"""Index retained board sources and derived previews. Does not modify originals."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = {v['path']: v for v in json.loads((ROOT / 'review/download-log.json').read_text(encoding='utf-8')) if v['status'] == 'downloaded'}
BOARDS = [
    ('dji-type-a', 'DJI RoboMaster A型', '01_DJI_A型评估.md', '官方手册＋第三方仓库保存的原厂格式原理图；原理图不是本次从DJI服务器取得。'),
    ('dji-type-c', 'DJI RoboMaster C型', '02_DJI_C型评估.md', '官方手册＋官方CDN原理图/位号图ZIP，包含主板及IMU FPC小板。'),
    ('damiao-dm-mc02', '达妙DM-MC02', '03_达妙DM-MC02评估.md', '厂商项目页链接的Gitee仓库资料；V1.0-240124图纸与2025年V1.1手册版本不同。'),
    ('user-d-main-2558', 'D_MAIN_2558', '04_D_MAIN_2558评估.md', '用户提供的7份DXF；未提供PCB、BOM、固件及明确硬件版本。'),
]

def write_text(path, text):
    path.write_bytes(text.encode('utf-8'))

def dump(path, obj):
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def main():
    for folder, title, assessment, note in BOARDS:
        base = ROOT / folder
        entries = []
        zip_members = []
        if folder == 'dji-type-c':
            with zipfile.ZipFile(base / 'schematic-and-layout-official.zip') as bundle:
                zip_members = [n for n in bundle.namelist() if n.lower().endswith('.pdf')]
        for path in sorted(base.rglob('*')):
            if not path.is_file() or path.name in ('README.md', 'source-index.json'):
                continue
            relative = path.relative_to(base).as_posix()
            log = LOG.get(path.relative_to(ROOT).as_posix())
            item = {'path': relative, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            if log:
                item.update(kind='downloaded-original', url=log['url'], retrieved_at=log['retrieved_at'])
                item['provenance'] = 'third-party-mirror-of-manufacturer-drawing' if 'via-mirror' in path.name else 'publisher-or-official-host'
            elif path.suffix.lower() == '.dxf':
                original = Path('C:/Users/27348/Desktop/D_MAIN_2558') / path.name
                assert original.read_bytes() == path.read_bytes(), path
                item.update(kind='user-provided-original', original_path=original.as_posix(), byte_identical_verified=True)
            elif path.name.startswith('official-bundle-document-') and path.suffix == '.pdf':
                index = int(path.stem.rsplit('-', 1)[1]) - 1
                member = zip_members[index]
                with zipfile.ZipFile(base / 'schematic-and-layout-official.zip') as bundle:
                    assert bundle.read(member) == path.read_bytes()
                item.update(kind='extracted-original', container='schematic-and-layout-official.zip', container_member=member, byte_identical_verified=True)
            else:
                item.update(kind='derived-preview-or-text', authoritative=False)
            if folder == 'damiao-dm-mc02' and path.suffix == '.pdf':
                expected = {'schematic-v1.0-240124.pdf': '6756a5a33df12d11f1f695bdbaa46b2b5e24a809', 'user-manual-v1.1.pdf': '0d077247714b316d806692df125a6db409d463d1'}[path.name]
                data = path.read_bytes()
                actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                assert actual == expected
                item.update(repository_commit='0ad8a919495c6da38f36b9352ca1118e490ef4c2', git_blob_sha1=actual, git_blob_verified=True)
            if 'via-mirror' in path.name and path.suffix == '.pdf':
                data = path.read_bytes()
                actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                assert actual == '13caccbdb16f9219a1e56287dc964a49f1e39a21'
                item.update(repository_commit='10be088ec22b27686bdee01c1b3cf64342d3da56', git_blob_sha1=actual, git_blob_verified=True)
            entries.append(item)
        dump(base / 'source-index.json', {'schema_version': 1, 'board': title, 'collected_on': '2026-09-15', 'scope': note, 'assessment': '../../../../docs/reviews/2026-09-15/' + assessment, 'files': entries})
        md = f'# {title}资料索引\n\n采集日期：2026-09-15。{note}\n\n[独立评估](../../../../docs/reviews/2026-09-15/{assessment}) · [文件来源与SHA-256](source-index.json)\n\n## 原始资料\n\n| 文件 | 来源/性质 |\n| --- | --- |\n'
        for entry in entries:
            if entry['kind'] == 'derived-preview-or-text':
                continue
            origin = f"[原始下载地址]({entry['url']})" if 'url' in entry else ('用户提供；副本与外部原文件逐字节一致' if entry['kind'] == 'user-provided-original' else f"官方ZIP成员：`{entry['container_member']}`")
            if 'via-mirror' in entry['path']:
                origin += '；第三方镜像，非本次官方直取'
            md += f"| [{entry['path']}]({entry['path']}) | {origin} |\n"
        md += '\n## 预览与阅读规则\n\n预览和提取文本是本地生成的辅助材料。PDF原理图全部页面已渲染；用户手册仅渲染封面，但保存全文提取文本。DXF解析文字坐标并生成整页预览，部分原始符号文字重叠；精确连线以原文件和后续原生EDA/BOM复核为准。\n\n'
        for preview in sorted((base / 'previews').rglob('page-01.png')):
            rel = preview.relative_to(base).as_posix()
            text_rel = (preview.parent / 'extracted.txt').relative_to(base).as_posix()
            md += f'- {preview.parent.name}：[首张预览]({rel})、[全文提取]({text_rel})；其他页面在同目录按页码命名。\n'
        for preview in sorted((base / 'previews').glob('*.png')):
            md += f'- {preview.stem}：[预览]({preview.relative_to(base).as_posix()})、[文字坐标](previews/{preview.stem}.text.json)。\n'
        md += '\n原始PDF/DXF/ZIP保持下载或接收时字节，文件未因本次评估而修改。HTML只作来源快照，可能依赖网络脚本；不作为离线图纸或自动执行入口。第三方材料仍归原权利人，本次归档用于项目研究，不推定获得改版生产、商标或固件再分发许可。\n'
        write_text(base / 'README.md', md)
    print('Indexed four boards; source bytes, extracted ZIP members and repository blobs verified.')

if __name__ == '__main__':
    main()
