"""Validate research artifacts without changing sources or hardware definitions."""
import hashlib
import json
import posixpath
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
from index_sources import BOARDS, ROOT, dump

PROJECT = ROOT.parents[2]
REPO = PROJECT.parent
ARCHIVES = PROJECT / 'archives/2026-09-15_board-research'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def local_links(text):
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
        target = target.strip('<>')
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
            continue
        yield unquote(target.split('#', 1)[0])

def historical_text(relative):
    return subprocess.check_output(['git', 'show', 'HEAD:H7MS-Core-A1/' + relative], cwd=REPO).decode('utf-8').replace('\r\n', '\n')

def main():
    errors = []
    checks = {}
    markdown_count = link_count = 0
    for source in PROJECT.rglob('*.md'):
        text = source.read_text(encoding='utf-8')
        markdown_count += 1
        if '\ufffd' in text:
            errors.append(f'Replacement character in {source}')
        if len(re.findall(r'^```', text, re.M)) % 2:
            errors.append(f'Unclosed code fence in {source}')
        for target in local_links(text):
            link_count += 1
            if not (source.parent / target).exists():
                errors.append(f'Broken link: {source.relative_to(PROJECT)} -> {target}')
    checks['markdown_files'] = markdown_count
    checks['repository_local_links'] = link_count

    indexed_files = 0
    originals_verified = 0
    for folder, _, _, _ in BOARDS:
        base = ROOT / folder
        index = json.loads((base / 'source-index.json').read_text(encoding='utf-8'))
        for item in index['files']:
            data = (base / item['path']).read_bytes()
            assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
            indexed_files += 1
            if item['kind'] == 'user-provided-original':
                assert Path(item['original_path']).read_bytes() == data
                originals_verified += 1
            if 'git_blob_sha1' in item:
                assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == item['git_blob_sha1']
            if item['path'].endswith('.png'):
                assert data.startswith(b'\x89PNG\r\n\x1a\n')
    checks['indexed_source_and_preview_files'] = indexed_files
    checks['user_original_dxf_files_verified'] = originals_verified

    index = json.loads((ARCHIVES / 'archive-index.json').read_text(encoding='utf-8'))
    archive_links = archive_files = 0
    for record in index['archives']:
        archive = ARCHIVES / record['file']
        data = archive.read_bytes()
        assert len(data) == record['bytes'] and sha(data) == record['sha256']
        assert (ARCHIVES / record['checksum']).read_text(encoding='utf-8').split()[0] == record['sha256']
        sidecar = (ARCHIVES / record['manifest']).read_bytes()
        manifest = json.loads(sidecar)
        prefix = manifest['archive_root']
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None
            assert bundle.read(prefix + 'MANIFEST.json') == sidecar
            assert len(bundle.namelist()) == len(manifest['files']) + 1
            for item in manifest['files']:
                name = prefix + item['path']
                content = bundle.read(name)
                assert len(content) == item['bytes'] and sha(content) == item['sha256'], name
                archive_files += 1
                if item.get('repository_path'):
                    original = PROJECT / item['repository_path']
                    assert sha(original.read_bytes()) == item['repository_sha256'], original
                    if not item['links_relocated']:
                        assert content == original.read_bytes()
                if name.endswith('.md'):
                    for target in local_links(content.decode('utf-8')):
                        archive_links += 1
                        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
                        if resolved not in bundle.namelist():
                            errors.append(f'Broken offline archive link: {record["file"]}:{name} -> {target}')
    synthesis = index['synthesis']
    assert sha((ARCHIVES / synthesis['file']).read_bytes()) == synthesis['sha256']
    assert sha((PROJECT / synthesis['repository_path']).read_bytes()) == synthesis['repository_sha256']
    checks.update(archives_verified=len(index['archives']), archive_content_files=archive_files, offline_archive_links=archive_links, synthesis_snapshot_verified=True)

    pin_file = 'docs/H7MS-Core-A1_引脚配置.md'
    assert (PROJECT / pin_file).read_text(encoding='utf-8') == historical_text(pin_file)
    interface = 'docs/06_上下板接口规范.md'
    current = (PROJECT / interface).read_text(encoding='utf-8')
    previous = historical_text(interface)
    assert [s for s in current.splitlines() if s.startswith('|')] == [s for s in previous.splitlines() if s.startswith('|')]
    section = lambda text: text.split('## 4. 上电与安全时序', 1)[1].split('\n## ', 1)[0]
    assert section(current) == section(previous)
    checks.update(pin_plan_equal_git_head=True, interface_tables_equal_git_head=True, power_safety_sequence_equal_git_head=True)

    old_stem = 'H7MS-Core-A1_2026-09-11_docs-v0.7.1'
    for suffix in ['.zip', '.manifest.json', '.sha256']:
        relative = 'archives/' + old_stem + suffix
        old_data = subprocess.check_output(['git', 'show', 'HEAD:H7MS-Core-A1/' + relative], cwd=REPO)
        current_data = (PROJECT / relative).read_bytes()
        if suffix == '.zip':
            assert current_data == old_data
        else:
            # Git checkout can materialize text sidecars with CRLF on Windows.
            assert current_data.replace(b'\r\n', b'\n') == old_data.replace(b'\r\n', b'\n')
    old_manifest = json.loads((PROJECT / 'archives' / (old_stem + '.manifest.json')).read_text(encoding='utf-8'))
    with zipfile.ZipFile(PROJECT / 'archives' / (old_stem + '.zip')) as bundle:
        assert bundle.testzip() is None
        for item in old_manifest['files']:
            content = bundle.read('H7MS-Core-A1/' + item['path'])
            assert len(content) == item['bytes'] and sha(content) == item['sha256'].lower()
    checks['historical_zip_byte_equal_head_and_sidecars_text_equal_head'] = True

    result = subprocess.run(['git', '-c', 'core.autocrlf=false', 'diff', '--check', '--', 'H7MS-Core-A1'], cwd=REPO, capture_output=True)
    if result.returncode:
        errors.append(result.stdout.decode('utf-8', errors='replace') + result.stderr.decode('utf-8', errors='replace'))
    checks['git_diff_check_passed'] = result.returncode == 0
    meta = json.loads((PROJECT / 'project.json').read_text(encoding='utf-8'))
    assert meta['docs_version'] == 'v0.7.4' and meta['mcu'] == 'STM32H743VIH6'
    report = {'validated_at': datetime.now(timezone.utc).isoformat(), 'scope': 'Document/source/archive integrity only; no hardware or firmware tests.', 'checks': checks, 'errors': errors, 'passed': not errors}
    dump(ROOT / 'review/validation-result.json', report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if errors:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
