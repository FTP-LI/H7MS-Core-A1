"""Check staged Git blobs and nested ZIP/EPRO files without printing credentials.

Run after git add. This is a targeted pattern check, not a complete secret scanner.
Exit 0: no matches/errors; 1: matches; 2: incomplete scan or invalid archive.
"""

import io
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile


RULES = {
    "alibaba_access_key_id": rb"\bLTAI[A-Za-z0-9]{12,32}\b",
    "oss_signed_url": rb"(?i)OSSAccessKeyId(?:\\u003d|%3d|=)[A-Za-z0-9]{8,}",
    "oss_v4_signature": rb"(?i)x-oss-signature(?:\\u003d|%3d|=)[a-f0-9]{32,}",
    "named_credential": (
        rb"(?i)\b(?:access[_-]?key[_-]?secret|client_secret|api_key|"
        rb"access_token|refresh_token|password)[\x22\x27]?\s*[:=]\s*"
        rb"[\x22\x27][A-Za-z0-9_+/=.-]{16,}[\x22\x27]"
    ),
    "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "github_token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b",
    "aws_access_key_id": rb"\bAKIA[A-Z0-9]{16}\b",
    "openai_token": rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b",
}
PATTERNS = {name: re.compile(pattern) for name, pattern in RULES.items()}


class Scan:
    def __init__(self):
        self.counts = dict(staged_files=0, archive_containers=0,
                           archive_entries=0, bytes_examined=0)
        self.findings = []
        self.errors = []

    def inspect(self, data, path, depth=0):
        self.counts["bytes_examined"] += len(data)
        if self.counts["bytes_examined"] > 1024 ** 3:
            raise ValueError("scan exceeds 1 GiB; results are incomplete")
        for name, pattern in PATTERNS.items():
            count = sum(1 for _ in pattern.finditer(data))
            if count:
                self.findings.append(dict(path=path, rule=name, count=count))
        # Inspect all bytes, including binary assets, and decompress archives.
        # Do not classify arbitrary 30-character image data as an AccessKey secret.
        archive_suffix = Path(path).suffix.lower() in {".zip", ".epro", ".epro2"}
        if not (data.startswith(b"PK\x03\x04") or archive_suffix):
            return
        if depth >= 6:
            raise ValueError("archive nesting exceeds 6 levels")
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                self.counts["archive_containers"] += 1
                for entry in archive.infolist():
                    if entry.is_dir():
                        continue
                    if entry.file_size > 128 * 1024 ** 2:
                        raise ValueError("archive member exceeds 128 MiB")
                    self.counts["archive_entries"] += 1
                    self.inspect(archive.read(entry), path + "!/" + entry.filename,
                                 depth + 1)
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError, ValueError) as exc:
            self.errors.append(dict(path=path, error=type(exc).__name__))


def main():
    root = Path(__file__).resolve().parents[1]
    entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root)
    scan = Scan()
    with subprocess.Popen(["git", "cat-file", "--batch"], cwd=root,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as cat:
        try:
            for entry in entries.split(b"\0"):
                if not entry:
                    continue
                metadata, path_bytes = entry.split(b"\t", 1)
                mode, oid, stage = metadata.split()
                if stage != b"0" or mode == b"160000":
                    raise ValueError("unmerged index or submodule requires separate review")
                cat.stdin.write(oid + b"\n")
                cat.stdin.flush()
                _, kind, size = cat.stdout.readline().split()
                if kind != b"blob":
                    raise ValueError("expected staged blob")
                data = cat.stdout.read(int(size))
                if len(data) != int(size) or cat.stdout.read(1) != b"\n":
                    raise ValueError("incomplete staged blob")
                scan.counts["staged_files"] += 1
                scan.inspect(data, path_bytes.decode("utf-8"))
        except (ValueError, OSError) as exc:
            scan.errors.append(dict(path="<index>", error=type(exc).__name__))
        finally:
            cat.stdin.close()
            if cat.wait() != 0:
                scan.errors.append(dict(path="<index>", error="git cat-file failed"))
    print(json.dumps(dict(scope="staged Git blobs and nested ZIP/EPRO members",
                          rules=list(RULES), counts=scan.counts,
                          findings=scan.findings, errors=scan.errors),
                     ensure_ascii=False, indent=2))
    return 2 if scan.errors else (1 if scan.findings else 0)


if __name__ == "__main__":
    sys.exit(main())
