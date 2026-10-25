"""Capture the explicitly pinned H735 project for independent review."""
import argparse,json
from pathlib import Path
import native_design as n
from eda_bridge import execute,export_project

def capture(archive):
    folder=n.HERE/'review-native';folder.mkdir(exist_ok=True)
    state=n.load_state()['CORE']
    for key,pid in state['pages'].items():
        result=execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,400));return await eda.sys_FileManager.getDocumentSource();')
        (folder/(key+'.esch')).write_text(result,encoding='utf-8')
    r=execute('const f=await eda.sch_ManufactureData.getNetlistFile(undefined,"JLCEDA");return await f.text();')
    (n.HERE/'native-CORE-netlist.json').write_text(r,encoding='utf-8')
    drc=execute('return await eda.sch_Drc.check(true,false,true);')
    report=dict(passed=not drc,api='sch_Drc.check(true,false,true)',groups=drc,ui_used=False,detail_supported='severity/count only',client_version='3.2.149.88089769')
    (n.HERE/'native-drc-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DRC',drc,flush=True)
    print(export_project(archive),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive');capture(p.parse_args().archive)
