"""Read source schematics; make PNG previews and searchable, non-authoritative text."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(os.environ['TEMP']) / 'h7ms-board-review-20260915/python'))
import ezdxf
import pymupdf
from ezdxf.addons.drawing import RenderContext, Frontend, layout, config
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
from ezdxf.disassemble import recursive_decompose

ROOT = Path(__file__).resolve().parent.parent
summary = []
for src in sorted((ROOT / 'user-d-main-2558').glob('*.dxf')):
    doc = ezdxf.readfile(src)
    out = src.parent / 'previews'
    out.mkdir(exist_ok=True)
    texts = []
    for entity in recursive_decompose(doc.modelspace()):
        if entity.dxftype() in ('TEXT', 'MTEXT', 'ATTRIB'):
            value = entity.plain_text() if hasattr(entity, 'plain_text') else entity.dxf.text
            pos = entity.dxf.insert
            texts.append({'x': round(pos.x, 3), 'y': round(pos.y, 3), 'text': value})
    texts.sort(key=lambda t: (-round(t['y'], 1), t['x']))
    (out / (src.stem + '.text.json')).write_text(json.dumps(texts, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / (src.stem + '.txt')).write_text('\n'.join(t['text'] for t in texts), encoding='utf-8')
    backend = PyMuPdfBackend()
    cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE)
    Frontend(RenderContext(doc), backend, config=cfg).draw_layout(doc.modelspace(), finalize=True)
    png = backend.get_pixmap_bytes(layout.Page(420, 297, margins=layout.Margins.all(5)), dpi=190)
    (out / (src.stem + '.png')).write_bytes(png)
    summary.append({'file': str(src.relative_to(ROOT)), 'text_entities': len(texts), 'dxf_version': doc.dxfversion})
for src in sorted(ROOT.glob('*/*.pdf')):
    out = src.parent / 'previews' / src.stem
    out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(src)
    text = []
    render_all = ('schematic' in src.name or 'bundle-document' in src.name)
    for i, page in enumerate(doc):
        text.append(f'\n\n=== PDF PAGE {i+1} ===\n' + page.get_text(sort=True))
        if render_all or i == 0:
            page.get_pixmap(dpi=130).save(out / f'page-{i+1:02}.png')
    (out / 'extracted.txt').write_text(''.join(text), encoding='utf-8')
    summary.append({'file': str(src.relative_to(ROOT)), 'pages': len(doc), 'metadata': doc.metadata})
(ROOT / 'review/render-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
