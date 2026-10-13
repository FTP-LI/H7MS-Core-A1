"""Verify saved originals/derived references and archived-only hash records."""
from pathlib import Path
import argparse, hashlib, json, zipfile

HERE=Path(__file__).resolve().parent
PROJECT=next(p for p in HERE.parents if (p/'project.json').exists())

def main(refresh=False):
    errors=[];checked=[];updated=[];archived=[]
    archive_path=PROJECT/'archives/2026-10-11_before-docs-v0.8.0/H7MS-Core-A1_before-docs-v0.8.0.zip'
    with zipfile.ZipFile(archive_path) as z:
        indices=sorted((PROJECT/'docs').rglob('source-index.json'))
        for index in indices:
            obj=json.loads(index.read_text(encoding='utf-8-sig'))
            def visit(x):
                if isinstance(x,dict):
                    if 'sha256' in x:
                        key=next((k for k in ('project_relative_path','path','file','local_path') if isinstance(x.get(k),str)),None)
                        if x.get('archived_only') and x.get('archive_member'):
                            member=x['archive_member']
                            data=z.read(member)
                            if hashlib.sha256(data).hexdigest()!=x['sha256']:errors.append(member+' archived hash mismatch')
                            else:archived.append(member)
                        elif key:
                            file=(PROJECT if key=='project_relative_path' else index.parent)/x[key]
                            if not file.is_file():errors.append(str(file)+' missing')
                            else:
                                actual=hashlib.sha256(file.read_bytes()).hexdigest()
                                if actual!=x['sha256']:
                                    if refresh and file.suffix in ('.md','.py'):
                                        x.setdefault('pre_migration_sha256',x['sha256'])
                                        x['sha256']=actual;x['bytes']=file.stat().st_size
                                        x['hash_updated_on']='2026-10-12'
                                        updated.append(file.relative_to(PROJECT).as_posix())
                                    else:errors.append(str(file)+' hash mismatch')
                                checked.append(file.relative_to(PROJECT).as_posix())
                    for v in list(x.values()):
                        if isinstance(v,(dict,list)):visit(v)
                elif isinstance(x,list):
                    for v in x:visit(v)
            visit(obj)
            if refresh:index.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report=dict(date='2026-10-12',status='pass' if not errors else 'fail',source_indexes=len(indices),saved_hash_records=len(checked),archived_hash_records=len(archived),updated_derived_files=updated,errors=errors,files=checked,archive_members=archived)
    (HERE/'source-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('files','archive_members')},ensure_ascii=False))
    return not errors

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--refresh-derived',action='store_true');args=parser.parse_args()
    raise SystemExit(0 if main(args.refresh_derived) else 1)
