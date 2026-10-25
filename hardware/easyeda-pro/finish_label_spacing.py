import json
import native_design as n
from functional_layout import ATTR_JS
from eda_bridge import execute
s=n.load_state()['CORE']
for page,attr,x,y in [('C04','e2c95e622652d56b',528,968),('C06','32e68aa0159b618f',350,940)]:
    execute('await eda.dmt_EditorControl.openDocument('+json.dumps(s['pages'][page])+');return true;')
    execute('if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(s['pages'][page])+')throw new Error("Wrong SCH");'+ATTR_JS+'await style(await eda.sch_PrimitiveAttribute.get('+json.dumps(attr)+'),'+str(x)+','+str(y)+',6,3,0,true);await eda.sch_Document.save();return true;')
print('two remaining annotation collisions corrected')
