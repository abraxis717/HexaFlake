"""C6 resource characterization. No model, learned routing or superiority claim."""
import sys,time,resource,json,hashlib,statistics,random,gc
from array import array
from collections import deque,defaultdict
from pathlib import Path
from struct import pack

def require(x,msg):
    if not x: raise AssertionError(msg)
def rss():
    return int(next(x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('VmRSS:')).split()[1])*1024
def peak(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
def emit(k,v): print(k+'='+json.dumps(v,sort_keys=True),flush=True)
def region(idx,root,radius):
    seen={root:0};q=deque([root])
    while q:
        u=q.popleft()
        if seen[u]==radius:continue
        for v in idx.neighbors(u):
            if v not in seen:seen[v]=seen[u]+1;q.append(v)
    return tuple(sorted(seen))
def build(f,geo,bridge,GeoIndex):
    t=time.perf_counter(); xyz,faces=geo.build(f); n=len(xyz)//3
    edges=bridge.collect_edges(faces,n);del xyz,faces
    bfs,_=bridge.graph_bfs_order(edges,n);codes=array('I',[0])*n
    for i,v in enumerate(bfs):codes[v]=bridge.rank_to_code(i,n)
    idx=GeoIndex(codes,edges);del codes,edges,bfs
    return idx,time.perf_counter()-t

def case(idx,center,radius,cut,width,repeats):
    from geodome_state import NodeState
    from geodome_scheduler import SparseScheduler
    vs=region(idx,center,radius); avail=set(vs);rng=random.Random(60600+radius)
    arcs=tuple(idx.arc_id(u,v) for u in vs for v in idx.neighbors(u) if v in avail and (not cut or rng.random()>.28))
    roots=(center,) if not cut else (center,next(v for v in vs if v!=center))
    out={v:[] for v in vs}
    for a in arcs:
        u,v=idx.arc_endpoints(a);out[u].append(v)
    def bfs():
        d={v:10000 for v in vs};q=deque(roots);visits=0
        for u in roots:d[u]=0
        while q:
            u=q.popleft()
            for v in out[u]:
                visits+=1
                if d[v]>d[u]+1:d[v]=d[u]+1;q.append(v)
        return d,visits
    # Synchronous full enrolled-region sweep, same shortest-distance recurrence,
    # no NodeState/arc wrappers. All enrolled arcs visited each round.
    def sweep():
        d={v:10000 for v in vs}
        for u in roots:d[u]=0
        for r in range(1,257):
            nxt=d.copy()
            for u in vs:
                x=d[u]+1
                for v in out[u]:
                    if x<nxt[v]:nxt[v]=x
            if nxt==d:return d,r,r*len(arcs)
            d=nxt
        raise AssertionError('SWEEP_ROUND_CAP')
    expected,bvis=bfs(); ds,sround,svis=sweep();require(ds==expected,'FLAT_PARITY')
    baseline={}
    for name,fn in [('flat_bfs',bfs),('flat_sync_sweep',sweep)]:
        samples=[]
        for _ in range(repeats):
            t=time.perf_counter_ns();got=fn();samples.append(time.perf_counter_ns()-t);require(got[0]==expected,'BASELINE_DRIFT')
        baseline[name]={'median_ns':statistics.median(samples),'samples_ns':samples,'arc_visits':bvis if name=='flat_bfs' else svis}
    baseline['flat_sync_sweep']['rounds']=sround
    pad=(0.,)*(width-2)
    def msg(a,u,v,row):return (row[0]+1.,0.)+pad
    def update(v,old,inbox):return (min(old[0],*(m[0] for a,m in inbox)),)+old[1:]
    result={}
    # Alternate order by repeat; same graph, widths, initial states and callbacks.
    runs={'dense':[],'sparse':[]}
    for rep in range(repeats):
        for mode in (('sparse','dense') if rep%2==0 else ('dense','sparse')):
            gc.collect();rb=rss();t=time.perf_counter_ns()
            state=NodeState(idx,width=width,precision='f64',mode=mode,capacity=idx.vertices if mode=='dense' else len(vs))
            hs=[]
            for v in vs:
                h=state.acquire_vertex(v);state.write(h,(0. if v in roots else 10000.,float(v))+pad);hs.append(h)
            sch=SparseScheduler(state,hs,arcs,max_active=1024,max_rounds=256,max_visits=24576*256);sch.start(roots)
            setup=time.perf_counter_ns()-t;rs=rss();t=time.perf_counter_ns();trace=[]
            while sch.status=='RUNNING':
                rr=sch.step(msg,update);trace.append((rr.status,rr.sources,rr.arcs,rr.destinations,rr.changed,rr.touched))
            elapsed=time.perf_counter_ns()-t;re=rss();require(sch.status=='QUIESCENT','BUDGET_STOP')
            dig=hashlib.sha256()
            for v,h in zip(vs,hs):
                row=state.read(h);require(row==(float(expected[v]),float(v))+pad,'STATE_ORACLE');dig.update(pack('<I'+'d'*width,v,*row))
            rec=dict(setup_ns=setup,execution_ns=elapsed,rss_before_bytes=rb,rss_setup_bytes=rs,rss_after_bytes=re,rounds=sch.rounds,visits=sch.visits,max_frontier=max(r[1] for r in trace),max_touched=max(r[5] for r in trace),state_sha256=dig.hexdigest(),trace_sha256=hashlib.sha256(repr(trace).encode()).hexdigest(),payload=state.payload())
            runs[mode].append(rec);del sch,state,hs,h,trace
    require(len({r['state_sha256'] for rr in runs.values() for r in rr})==1,'RESIDENCY_STATE_DRIFT')
    require(len({r['trace_sha256'] for rr in runs.values() for r in rr})==1,'RESIDENCY_TRACE_DRIFT')
    for mode,rr in runs.items():
        a=rr[0];result[mode]=dict(execution_median_ns=statistics.median(r['execution_ns'] for r in rr),setup_median_ns=statistics.median(r['setup_ns'] for r in rr),execution_samples_ns=[r['execution_ns'] for r in rr],setup_samples_ns=[r['setup_ns'] for r in rr],rss_before_bytes=[r['rss_before_bytes'] for r in rr],rss_setup_bytes=[r['rss_setup_bytes'] for r in rr],rss_after_bytes=[r['rss_after_bytes'] for r in rr],**{k:a[k] for k in ('rounds','visits','max_frontier','max_touched','state_sha256','trace_sha256','payload')})
    return dict(vertices=idx.vertices,nodes=len(vs),arcs=len(arcs),center=center,radius=radius,cut=cut,width=width,repeats=repeats,index_payload_bytes=idx.payload_bytes(),baseline=baseline,**result)

def main(repo,stage,src,local=False):
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(240,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    sys.path[:0]=[str(repo),str(src)]
    if not local:
        from smoke import restrict_writes
        restrict_writes(stage)
    from GEO144K import g1c_compact as geo,g2b_bridge as bridge
    from geodome_index import GeoIndex
    start=time.monotonic();builds=[];records=[]
    for f in (16,32,64,120):
        gc.collect();before=rss();idx,secs=build(f,geo,bridge,GeoIndex)
        rec=dict(frequency=f,vertices=idx.vertices,edges=idx.edges,construction_seconds=secs,index_payload_bytes=idx.payload_bytes(),rss_before_bytes=before,rss_after_bytes=rss(),mapping_sha256=idx.mapping_sha256(),edge_sha256=idx.edge_sha256());builds.append(rec);emit('C6_BUILD',rec)
        if f==120:
            require(rec['mapping_sha256']=='abe96202b554608bd8f5e702b70459daaaf4ab33eb7dfd058723fd4d1724f51b','MAPPING_DRIFT')
            require(rec['edge_sha256']=='712a8fc3d94685aeb614456ba8c88f6df7e6c6ea8a4c19e86d4d3865ad014231','EDGE_DRIFT')
        # same radius around identical pentavalent vertex, at all four frequencies
        configs=[(0,6,False,16)]
        if f==120:configs += [(65000,9,False,2),(65000,15,False,16),(65000,35,False,2),(65000,35,True,2),(65000,35,False,16),(65000,35,False,64)]
        for args in configs:
            r=case(idx,*args,repeats=3);records.append(r);emit('C6_CASE',r)
        del idx
    require(len(records)==10,'MATRIX_INCOMPLETE')
    require(len({r['nodes'] for r in records if r['center']==0})==1,'FIXED_PATCH_DRIFT')
    require(len({r['sparse']['visits'] for r in records if r['center']==0})==1,'FIXED_PATCH_WORK_DRIFT')
    emit('C6_RESULT',dict(phase='GEO_CLOSE_C6_R0',status='PASS_BOUNDED_RESOURCE_CHARACTERIZATION',local_reconstruction=local,builds=builds,records=records,paired_cases=len(records),scheduler_runs=len(records)*6,baseline_runs=len(records)*6,oracle_rows=sum(r['nodes']*6 for r in records),max_enrolled=max(r['nodes'] for r in records),max_frontier=max(r['sparse']['max_frontier'] for r in records),peak_rss_bytes=peak(),total_seconds=time.monotonic()-start,KV_cache='NOT_ALLOCATED',CGC='NOT_RUN',HCA88='NOT_RUN',speed_advantage='NOT_REQUIRED',learned_competence='NOT_RUN',memory_scope='PROCESS_RSS_AND_ARRAY_PAYLOAD_NOT_PER_ARM_PEAK',runtime_persistent_writes='LOCAL_NO_SANDBOX' if local else 'NONE'))
    print('NEXT_GATE=GEO_CLOSE_C7_DISTRIBUTED_COMPUTATION',flush=True)
if __name__=='__main__':main(*(Path(x).resolve() for x in sys.argv[1:4]),local=len(sys.argv)>4 and sys.argv[4]=='--local')
