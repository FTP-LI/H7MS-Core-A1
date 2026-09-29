"""Fetch explicitly listed public research documents; no remote code is executed."""
import concurrent.futures
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent

def fetch(item):
    out = (ROOT / item['path']).resolve()
    if not out.is_relative_to(ROOT):
        raise ValueError('Output outside research directory')
    try:
        r = requests.get(item['url'], timeout=40)
        r.raise_for_status()
        if out.suffix.lower() == '.pdf' and not r.content.startswith(b'%PDF'):
            raise ValueError('Response is not a PDF')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)
        return {**item, 'status': 'downloaded', 'final_url': r.url,
                'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'bytes': len(r.content), 'sha256': hashlib.sha256(r.content).hexdigest()}
    except Exception as exc:
        return {**item, 'status': 'failed', 'error': str(exc)}

if __name__ == '__main__':
    plan = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(fetch, plan))
    record = ROOT / 'review/download-log.json'
    prior = json.loads(record.read_text(encoding='utf-8')) if record.exists() else []
    record.write_text(json.dumps(prior + results, ensure_ascii=False, indent=2), encoding='utf-8')
    for result in results:
        print(json.dumps(result, ensure_ascii=False))
