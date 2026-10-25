import json
import native_design as n
from eda_bridge import execute
queries=['BM03B-GHS-TBT','BM04B-GHS-TBT','BM06B-GHS-TBT','USB4120','USB4145','XT30PB-M','XT30UPB-M','LMR38020','LMR38025']
data=execute('const qs='+json.dumps(queries)+';return await Promise.all(qs.map(async q=>({q,items:await eda.lib_Device.search(q,"0819f05c4eef4c71ace90d822a990e87",undefined,undefined,30,1)})));')
(n.HERE/'core-revision-library-search.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
for row in data:
    print(row['q'],[(i.get('supplierId'),i.get('manufacturerId'),i.get('footprintName'),i.get('uuid')) for i in row['items']],flush=True)
