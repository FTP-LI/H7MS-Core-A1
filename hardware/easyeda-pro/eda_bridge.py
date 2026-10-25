"""Small, explicit EasyEDA bridge client; no automatic mutation retries."""
import json
import urllib.request
import urllib.error
from pathlib import Path

URL = 'http://127.0.0.1:49620'
PROJECT = 'e83cf0959fa243f7847e15552d7a94a7'
TARGET_WINDOW = '8d47cbef-abe7-429c-81c6-1871c5faab91'


def request(path, payload=None, timeout=45):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL + path, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(error.read().decode('utf-8', errors='replace')) from error


def execute(code, guard=True):
    health = request('/health')
    if health.get('service') != 'easyeda-bridge':
        raise RuntimeError('Unexpected bridge service')
    windows = request('/eda-windows')['windows']
    # The user specified this H735 project. Bind to its observed window, never
    # follow focus into a different project opened by the user during authoring.
    selected = next((w['windowId'] for w in windows if w['windowId']==TARGET_WINDOW), None)
    if selected is None:
        raise RuntimeError('H735 window changed; re-identify the requested project before editing')
    if guard:
        code = ('const current = await eda.dmt_Project.getCurrentProjectInfo(); '
                f'if (current?.uuid !== {json.dumps(PROJECT)}) throw new Error("Unexpected active project"); ' + code)
    result = request('/execute', {'code': code, 'windowId': selected})
    if not result.get('success'):
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result.get('result')


def export_project(path):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    result = execute('const f = await eda.sys_FileManager.getProjectFile(undefined, undefined, "epro"); '
                     'if (!f) throw new Error("Export failed"); '
                     'return {name:f.name, bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(result['bytes']))
    return {'path': str(path), 'bytes': path.stat().st_size, 'exportName': result['name']}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--code-file', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    if args.backup:
        result = export_project(args.backup)
    else:
        result = execute(args.code_file.read_text(encoding='utf-8'))
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding='utf-8')
        print(args.output)
    else:
        print(serialized)

