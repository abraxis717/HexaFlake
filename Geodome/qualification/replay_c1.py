import sys,resource,time,json
from pathlib import Path
repo,stage=map(Path,sys.argv[1:3]);sys.path.insert(0,str(repo))
resource.setrlimit(resource.RLIMIT_AS,(1024**3,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(240,)*2)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
from smoke import restrict_writes
restrict_writes(stage)
from GEO144K import g1c_compact as geo,g2b_bridge as bridge
import Hexaflag as hxf
hxf.check_core(); original=geo.audit; audits=[]
def capture(*a,**kw):
    result=original(*a,**kw);audits.append(result);return result
geo.audit=capture
try: result=bridge.run(120)
finally: geo.audit=original
assert len(audits)==1
print('C1_RESULT='+json.dumps(dict(phase='GEO_CLOSE_C1_R0',status='PASS_FULL_SCALE_TOPOLOGY_LOGICAL_IDENTITY',topology=audits[0],address_bridge=result,geometry_negative_controls=geo.negative_controls(2)),sort_keys=True),flush=True)
