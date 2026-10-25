from eda_bridge import execute
print(execute('return {d:await eda.dmt_SelectControl.getCurrentDocumentInfo(),t:await eda.sch_PrimitiveText.getAll(),w:(await eda.sch_PrimitiveWire.getAll()).length};'))
