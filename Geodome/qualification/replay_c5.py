import sys,resource,time,json,hashlib,random
from array import array
from collections import deque
from pathlib import Path
from struct import pack
from dataclasses import asdict

def require(ok,msg):
    if not ok: raise AssertionError(msg)
def peak(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024

def region(idx,root,radius):
    seen={root:0}; q=deque([root])
    while q:
        u=q.popleft()
        if seen[u]==radius: continue
        for v in idx.neighbors(u):
            if v not in seen: seen[v]=seen[u]+1;q.append(v)
    return tuple(sorted(seen))

def graph(idx,vs,seed,cut=False):
    rng=random.Random(seed); avail=set(vs)
    return tuple(idx.arc_id(u,v) for u in vs for v in idx.neighbors(u) if v in avail and (not cut or rng.random()>.28))

def oracle(idx,vs,arcs,roots):
    es={v:[] for v in vs}
    for a in arcs:
        u,v=idx.arc_endpoints(a);es[u].append(v)
    d={v:10000 for v in vs};q=deque(roots)
    for u in roots:d[u]=0
    while q:
        u=q.popleft()
        for v in es[u]:
            if d[v]>d[u]+1:d[v]=d[u]+1;q.append(v)
    return d

def transport(a,u,v,row): return (row[0]+1.,0.)
def update(v,old,inbox): return (min(old[0],*(m[0] for a,m in inbox)),old[1])

def fixture(idx,vs,arcs,roots,mode,reverse=False):
    from geodome_state import NodeState
    from geodome_scheduler import SparseScheduler
    state=NodeState(idx,width=2,precision='f64',mode=mode,capacity=idx.vertices if mode=='dense' else len(vs)+1)
    # A resident but unauthorized sentinel proves the scheduler is not a global sweep.
    outsider=next(v for v in range(idx.vertices) if v not in set(vs))
    sentinel=state.acquire_vertex(outsider);state.write(sentinel,(777.,888.))
    hs=[]
    for v in reversed(vs) if reverse else vs:
        h=state.acquire_address(idx.address(v)); state.write(h,(0. if v in roots else 10000.,float(v)));hs.append(h)
    sch=SparseScheduler(state,hs,tuple(reversed(arcs)) if reverse else arcs,max_active=1024,max_rounds=128,max_visits=200000)
    sch.start(tuple(reversed(roots)) if reverse else roots); trace=[];t=time.monotonic()
    while sch.status=='RUNNING': trace.append(asdict(sch.step(transport,update)))
    elapsed=time.monotonic()-t
    require(sch.status=='QUIESCENT','UNEXPECTED_STOP'); expected=oracle(idx,vs,arcs,roots)
    dig=hashlib.sha256()
    for v in vs:
        row=state.read(state.handle(v));require(row==(float(expected[v]),float(v)),'ORACLE_MISMATCH');dig.update(pack('<Idd',v,*row))
    require(state.read(sentinel)==(777.,888.) and state.resident==len(vs)+1,'UNAUTHORIZED_MUTATION')
    record=dict(mode=mode,nodes=len(vs),arcs=len(arcs),sources=len(roots),reachable=sum(d<10000 for d in expected.values()),rounds=sch.rounds,visits=sch.visits,peak_touched=max(r['touched'] for r in trace),max_frontier=max(r['sources'] for r in trace),elapsed_seconds=elapsed,state_sha256=dig.hexdigest(),trace_sha256=hashlib.sha256(json.dumps(trace,sort_keys=True).encode()).hexdigest(),state_payload=state.payload())
    return record

def controls(idx):
    from geodome_state import NodeState
    from geodome_scheduler import SparseScheduler
    u=0; v,w=idx.neighbors(u)[:2];s=NodeState(idx,width=2,capacity=4);hs=tuple(s.acquire_vertex(x) for x in (u,v,w));s.write(hs[0],(0.,0.));s.write(hs[1],(100.,1.));s.write(hs[2],(100.,2.));arcs=(idx.arc_id(u,v),idx.arc_id(u,w))
    snap=lambda: (s._values.tobytes(),s.resident,s.epoch); count=0
    def bad(fn,exc):
        nonlocal count
        before=snap()
        try:fn()
        except exc:pass
        else: raise AssertionError('REJECTION_MISSING')
        require(snap()==before,'REJECTION_MUTATED_STATE');count+=1
    def create(**kw):return SparseScheduler(s,hs,arcs,**kw)
    bad(lambda:SparseScheduler(s,hs,(arcs[0],arcs[0])),ValueError)
    bad(lambda:SparseScheduler(s,hs[:2],arcs),ValueError)
    bad(lambda:SparseScheduler(s,hs,(2*idx.edges,)),ValueError)
    bad(lambda:SparseScheduler(s,hs+(hs[0],),arcs),ValueError)
    bad(lambda:create(max_rounds=0),ValueError)
    sch=create();bad(lambda:sch.start((True,)),ValueError);bad(lambda:sch.start((u,u)),ValueError);bad(lambda:sch.start((idx.vertices-1,)),ValueError);bad(lambda:sch.step(transport,update),ValueError)
    sch.start((u,));before=(sch.rounds,sch.visits,sch.frontier,sch.status)
    bad(lambda:sch.start((u,)),ValueError)
    bad(lambda:sch.step(lambda a,u,v,row:(float('nan'),0.),update),ValueError)
    def invalid(vtx,old,inbox):return (float('inf'),0.) if vtx==max(v,w) else update(vtx,old,inbox)
    bad(lambda:sch.step(transport,invalid),ValueError)
    require((sch.rounds,sch.visits,sch.frontier,sch.status)==before,'FAILED_ROUND_COUNTERS')
    for kwargs,status in (({'max_active':2},'ACTIVE_BUDGET'),({'max_visits':1},'ARC_BUDGET')):
        x=create(**kwargs);x.start((u,));b=snap();r=x.step(transport,update);require(r.status==status and snap()==b and x.rounds==0 and x.visits==0,'BUDGET_NOT_ATOMIC');count+=1
    x=create(max_rounds=1);x.start((u,));x.step(transport,update);b=snap();require(x.step(transport,update).status=='ROUND_BUDGET' and snap()==b,'ROUND_BUDGET');count+=1
    x=create();x.start((u,));s.release(hs[1]);new=s.acquire_vertex(v);bad(lambda:x.step(transport,update),ValueError);require(s.read(new)==(0.,0.),'STALE_HANDLE')
    x=SparseScheduler(s,(hs[0],new,hs[2]),arcs);x.start((u,));s.reset();bad(lambda:x.step(transport,update),ValueError)
    # Genuine physical adjacency is not implied authority. A two-arc
    # physical path with one withheld arc cannot reach the third vertex.
    v=idx.neighbors(0)[0];w=next(z for z in idx.neighbors(v) if z!=0 and z not in idx.neighbors(0))
    s=NodeState(idx,width=2,capacity=3); hs=tuple(s.acquire_vertex(z) for z in (0,v,w))
    for h in hs:s.write(h,(0. if h.vertex==0 else 10000.,float(h.vertex)))
    arcs=(idx.arc_id(0,v),idx.arc_id(v,w))
    x=SparseScheduler(s,hs,arcs[:1]);x.start((0,))
    while x.status=='RUNNING':x.step(transport,update)
    require(s.read(hs[1])[0]==1 and s.read(hs[2])[0]==10000,'WITHHELD_PHYSICAL_ARC');count+=1
    # Synchronous snapshots: B sends its old row while A updates B.
    s.write(hs[1],(10000.,float(v)))
    x=SparseScheduler(s,hs,arcs);x.start((0,v));x.step(transport,update)
    require(s.read(hs[1])[0]==1 and s.read(hs[2])[0]==10000,'ASYNCHRONOUS_LEAKAGE');count+=1
    x.step(transport,update);require(s.read(hs[2])[0]==2,'SECOND_ROUND_MISSING');count+=1
    x=SparseScheduler(s,hs,());x.start((0,));b=snap();require(x.step(transport,update).status=='QUIESCENT' and snap()==b,'EMPTY_GRAPH');count+=1
    return count

def main(repo,stage,src,local=False):
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(240,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    sys.path[:0]=[str(repo),str(src),str(Path(__file__).resolve().parent)]
    if not local:
        from smoke import restrict_writes
        restrict_writes(stage)
    from GEO144K import g1c_compact as geo,g2b_bridge as bridge
    from geodome_index import GeoIndex
    t=time.monotonic();xyz,faces=geo.build(120);n=len(xyz)//3;edges=bridge.collect_edges(faces,n);del xyz,faces
    bfs,_=bridge.graph_bfs_order(edges,n);codes=array('I',[0])*n
    for rank,v in enumerate(bfs):codes[v]=bridge.rank_to_code(rank,n)
    del bfs;idx=GeoIndex(codes,edges);del codes,edges
    require(idx.mapping_sha256()=='abe96202b554608bd8f5e702b70459daaaf4ab33eb7dfd058723fd4d1724f51b','MAPPING_DRIFT')
    require(idx.edge_sha256()=='712a8fc3d94685aeb614456ba8c88f6df7e6c6ea8a4c19e86d4d3865ad014231','EDGE_DRIFT')
    nc=controls(idx); print('NEGATIVE_CONTROLS='+str(nc),flush=True);records=[]
    for i,(center,radius) in enumerate(((0,3),(11,6),(42042,9),(100000,12),(143999,15),(65000,35))):
        vs=region(idx,center,radius)
        for cut in (False,True):
            arcs=graph(idx,vs,1500+i,cut); roots=(center,) if not cut else (center,next(v for v in vs if v!=center))
            a=fixture(idx,vs,arcs,roots,'sparse');b=fixture(idx,vs,arcs,roots,'dense',True)
            require(a['state_sha256']==b['state_sha256'] and a['trace_sha256']==b['trace_sha256'],'ORDER_OR_RESIDENCY_DRIFT')
            rec=dict(center=center,radius=radius,cut=cut,sparse=a,dense=b);records.append(rec);print('C5_CASE='+json.dumps(rec,sort_keys=True),flush=True)
    result=dict(phase='GEO_CLOSE_C5_R0',status='PASS_BOUNDED_SPARSE_SYNCHRONOUS_PROPAGATION',local_reconstruction=local,vertices=n,index_payload_bytes=idx.payload_bytes(),negative_controls=nc,paired_cases=len(records),oracle_rows=sum(2*r['sparse']['nodes'] for r in records),arc_visits=sum(2*r['sparse']['visits'] for r in records),max_enrolled=max(r['sparse']['nodes'] for r in records),max_frontier=max(r['sparse']['max_frontier'] for r in records),dense_sparse_order_parity=True,records=records,total_seconds=time.monotonic()-t,peak_rss_bytes=peak(),transport='REFERENCE_PURE_CALLBACK',CGC='NOT_RUN',HCA88='NOT_RUN',KV_cache='NOT_ALLOCATED',concurrency='SINGLE_THREAD_ONLY',runtime_persistent_writes='LOCAL_REPLAY_NO_SANDBOX' if local else 'NONE',learned_controller='NOT_RUN')
    print('=== SEND BACK ===');print('C5_RESULT='+json.dumps(result,sort_keys=True));print('NEXT_GATE=GEO_CLOSE_C6_RESOURCE_SCALING')
if __name__=='__main__':main(*(Path(x).resolve() for x in sys.argv[1:4]),local=len(sys.argv)>4 and sys.argv[4]=='--local')
