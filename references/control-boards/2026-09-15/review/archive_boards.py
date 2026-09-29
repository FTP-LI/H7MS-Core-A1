"""Create four portable, individually verifiable reference/review archives once."""
import hashlib
import json
import os
import re
import zipfile
from pathlib import Path
from index_sources import BOARDS, ROOT, dump, write_text

PROJECT = ROOT.parents[2]
OUTPUT = PROJECT / 'archives/2026-09-15_board-research'
NAMES = {'dji-type-a': 'DJI-A', 'dji-type-c': 'DJI-C', 'damiao-dm-mc02': 'Damiao-DM-MC02', 'user-d-main-2558': 'D_MAIN_2558'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Never silently replace a frozen archive.
    for folder, _, _, _ in BOARDS:
        target = OUTPUT / (NAMES[folder] + '_2026-09-15_reference-review.zip')
        if target.exists():
            raise FileExistsError(f'Existing snapshot retained: {target}')
    records = []
    for folder, title, review_name, note in BOARDS:
        stem = NAMES[folder] + '_2026-09-15_reference-review'
        archive_root = stem + '/'
        review = PROJECT / 'docs/reviews/2026-09-15' / review_name
        original_prefix = '../../../references/control-boards/2026-09-15/' + folder + '/'
        adapted_review = review.read_text(encoding='utf-8').replace(original_prefix, 'sources/').encode('utf-8')
        files = [('assessment.md', adapted_review, review, True)]
        intro = f'# {title}独立资料与评估归档\n\n日期：2026-09-15。{note}\n\n从[评估正文](assessment.md)或[原始资料索引](sources/README.md)开始阅读。预览在sources/previews；PDF、DXF和官方ZIP保留原始字节。\n\n本包只包含本板资料与对应评估，不包含其他板资料或H7MS正式工程。评估及索引的本地链接已调整为本包可用路径；技术内容未改动。MANIFEST.json列出所有内容的大小和SHA-256；清单本身不加入自身哈希列表。ZIP外同名清单与包内清单相同，ZIP自身哈希在.sha256文件。\n\n校验后解压至新的目录，避免覆盖工程。当前文件是研究日期快照，不代表现售板卡的所有修订或实测通过。\n'
        files.append(('README.md', intro.encode('utf-8'), None, False))
        for source in sorted((ROOT / folder).rglob('*')):
            if not source.is_file():
                continue
            data = source.read_bytes()
            relocated = False
            if source.name == 'README.md':
                data = data.decode('utf-8').replace('../../../../docs/reviews/2026-09-15/' + review_name, '../assessment.md').encode('utf-8')
                relocated = True
            elif source.name == 'source-index.json':
                index = json.loads(data)
                index['assessment'] = '../assessment.md'
                data = (json.dumps(index, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
                relocated = True
            files.append(('sources/' + source.relative_to(ROOT / folder).as_posix(), data, source, relocated))
        manifest = {'schema_version': 1, 'archive_id': stem, 'archive_root': archive_root, 'date': '2026-09-15', 'board': title, 'scope': note, 'files': []}
        for name, data, source, relocated in sorted(files):
            item = {'path': name, 'bytes': len(data), 'sha256': digest(data)}
            if source:
                item.update(repository_path=source.relative_to(PROJECT).as_posix(), repository_sha256=digest(source.read_bytes()), links_relocated=relocated)
            manifest['files'].append(item)
        manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        archive = OUTPUT / (stem + '.zip')
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for name, data, _, _ in sorted(files):
                bundle.writestr(archive_root + name, data)
            bundle.writestr(archive_root + 'MANIFEST.json', manifest_bytes)
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None
            for item in manifest['files']:
                data = bundle.read(archive_root + item['path'])
                assert len(data) == item['bytes'] and digest(data) == item['sha256']
        (OUTPUT / (stem + '.manifest.json')).write_bytes(manifest_bytes)
        write_text(OUTPUT / (stem + '.sha256'), digest(archive.read_bytes()) + '  ' + archive.name + '\n')
        records.append({'board': title, 'file': archive.name, 'bytes': archive.stat().st_size, 'sha256': digest(archive.read_bytes()), 'content_files': len(files), 'manifest': stem + '.manifest.json', 'checksum': stem + '.sha256'})

    source_synthesis = PROJECT / 'docs/11_参考控制板共性需求与选型结论.md'
    synthesis = source_synthesis.read_text(encoding='utf-8')
    # Preserve a synthesis snapshot while rebasing relative links to this directory.
    def relocate(match):
        label, target = match.group(1), match.group(2)
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
            return match.group(0)
        path, sep, anchor = target.partition('#')
        resolved = (source_synthesis.parent / path).resolve()
        relative = Path(os.path.relpath(resolved, OUTPUT)).as_posix()
        return f'[{label}]({relative}{sep}{anchor})'
    synthesis = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', relocate, synthesis)
    write_text(OUTPUT / 'synthesis.md', synthesis)
    synthesis_data = (OUTPUT / 'synthesis.md').read_bytes()
    index = {'schema_version': 1, 'date': '2026-09-15', 'archives': records, 'synthesis': {'file': 'synthesis.md', 'bytes': len(synthesis_data), 'sha256': digest(synthesis_data), 'repository_path': source_synthesis.relative_to(PROJECT).as_posix(), 'repository_sha256': digest(source_synthesis.read_bytes()), 'links_relocated': True}}
    dump(OUTPUT / 'archive-index.json', index)
    intro = '# 四款参考控制板独立归档\n\n日期：2026-09-15。每块板独立ZIP，内含原始资料、预览、评估及校验清单；全部ZIP通过CRC及逐文件SHA-256验证。\n\n[共性需求与结论快照](synthesis.md) · [机器可读归档索引](archive-index.json) · [仓库资料与评估入口](../../references/control-boards/2026-09-15/README.md)\n\n| 对象 | 归档 | 内容文件数 | 校验 |\n| --- | --- | --- | --- |\n'
    for record in records:
        intro += f"| {record['board']} | [{record['file']}]({record['file']})（{record['bytes']/1024/1024:.2f} MiB） | {record['content_files']} | [SHA-256]({record['checksum']}) / [清单]({record['manifest']}) |\n"
    intro += '\n内容文件数不包含包内MANIFEST.json。ZIP解压后从README.md进入；单板原始资料与评估链接在包内可用。原始PDF/DXF/官方ZIP未改动，评估和索引仅重定位链接。来源仍在sources/source-index.json，A型原理图的第三方镜像身份明确保留。\n\n先校验ZIP自身SHA-256，再核对清单内每个文件大小与哈希。包内/包外manifest相同；清单不把自身作为内容项。哈希用于一致性检查，不等于厂商数字签名或硬件验收。\n\n综述快照单独保存，哈希记录在archive-index.json；其跨板链接指向仓库位置，完整离线资料按本页四个ZIP查阅。本次快照不覆盖原有2026-09-11 Docs v0.7.1文档包，亦非H7MS生产发布包。后续修改使用新日期/修订，不静默覆盖本批ZIP。\n'
    write_text(OUTPUT / 'README.md', intro)
    print(json.dumps(records, ensure_ascii=True, indent=2))

if __name__ == '__main__':
    main()
