"""Minimal stdlib consumer. Execute through run.py --example, not directly."""
import sys
from pathlib import Path
if len(sys.argv)!=4: raise SystemExit('Use Geodome/run.py --example')
core,public,scratch=map(Path,sys.argv[1:]);sys.path.insert(0,str(public))
from smoke import restrict_writes
restrict_writes(scratch)
sys.path.insert(0,str(core))
import geodome as g
idx=g.build_index()
u=0;v=idx.neighbors(u)[0]
address=idx.address(u); assert idx.resolve(address)==u
s=g.new_state(idx,width=2,capacity=2)
a=s.acquire_address(address);b=s.acquire_vertex(v)
s.write(a,(7.,1.));arc=idx.arc_id(u,v)
sch=g.SparseScheduler(s,(a,b),(arc,),max_active=2,max_rounds=3,max_visits=1)
sch.start((u,))
while sch.status=='RUNNING':
    sch.step(lambda arc,u,v,row:row,lambda v,old,inbox:inbox[0][1])
assert sch.status=='QUIESCENT' and s.read(b)==(7.,1.)
print(f'VERTICES={idx.vertices} EDGES={idx.edges} INDEX_BYTES={idx.payload_bytes()}')
print(f'ADDRESS={address} RESOLVES_TO={u} ARC={arc} DESTINATION={v} ROW={s.read(b)}')
s.reset();assert s.resident==0
try:s.read(a)
except ValueError:print('STALE_HANDLE_REJECTION=PASS')
else:raise AssertionError('STALE_HANDLE_ACCEPTED')
print('GEODOME_EXAMPLE=PASS')
