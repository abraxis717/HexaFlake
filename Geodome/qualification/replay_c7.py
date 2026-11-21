"""C7: exact distributed sufficient-statistic reduction; trusted callbacks only.
No trained model, automatic routing, native transport, or semantic claim.
"""
import sys,time,resource,json,hashlib,random
from array import array
from collections import deque
from pathlib import Path
from struct import pack

WIDTH=32 # local 4 + six child contributions of 4 + aggregate 4
ZERO=(0.,)*4

def require(x,msg):
    if not x: raise AssertionError(msg)
def emit(k,v):print(k+'='+json.dumps(v,sort_keys=True),flush=True)
def stats(x):return (1.,float(x),float(x*x),float(x>0))
def plus(a,b):return tuple(x+y for x,y in zip(a,b))
def build(geo,bridge,GeoIndex):
    xyz,faces=geo.build(120);n=len(xyz)//3;edges=bridge.collect_edges(faces,n);del xyz,faces
    bfs,_=bridge.graph_bfs_order(edges,n);codes=array('I',[0])*n
    for i,v in enumerate(bfs):codes[v]=bridge.rank_to_code(i,n)
    return GeoIndex(codes,edges)

def tree(idx,root,radius):
    parent={root:None};depth={root:0};q=deque([root])
    while q:
        u=q.popleft()
        if depth[u]==radius:continue
        for v in sorted(idx.neighbors(u)):
            if v not in parent:parent[v]=u;depth[v]=depth[u]+1;q.append(v)
    children={v:[] for v in parent}
    for v,p in parent.items():
        if p is not None:children[p].append(v)
    require(all(len(c)<=6 for c in children.values()),'CHILD_CAP')
    return parent,depth,children

def oracle(parent,inputs,cut):
    # Direct source-by-source accumulation along parent paths, independent of
    # scheduler, message buffers, arrival ordering, and update callback.
    expected={v:ZERO for v in parent}
    for u,value in inputs.items():
        contribution=stats(value);v=u
        while v is not None:
            expected[v]=plus(expected[v],contribution)
            if v==cut:break
            v=parent[v]
    return expected

def run(idx,root,parent,depth,children,inputs,cut,mode,reverse=False):
    from geodome_state import NodeState
    from geodome_scheduler import SparseScheduler
    vertices=sorted(parent,reverse=reverse)
    decoy=next(v for v in range(idx.vertices) if v not in parent)
    state=NodeState(idx,width=WIDTH,precision='f64',mode=mode,capacity=idx.vertices if mode=='dense' else len(vertices)+1)
    hs={v:state.acquire_vertex(v) for v in vertices}
    hdecoy=state.acquire_vertex(decoy);sentinel=(17.,)*WIDTH;state.write(hdecoy,sentinel)
    # Only the local owner has access to its own input; no answer injection.
    for v,x in inputs.items():state.write(hs[v],stats(x)+(0.,)*24+stats(x))
    arcs=[];slots={}
    for p,cs in children.items():
        for j,u in enumerate(sorted(cs)):
            if u==cut:continue
            a=idx.arc_id(u,p);arcs.append(a);slots[a]=4+4*j
    if reverse:arcs.reverse()
    def transport(a,u,v,row):return (0.,)*28+row[28:32]
    def update(v,old,inbox):
        row=list(old)
        for a,msg in inbox:
            k=slots[a];row[k:k+4]=msg[28:32]
        # Replace each child's last snapshot, rather than double-counting
        # retransmissions as the subtree accumulates additional contributions.
        row[28:32]=[sum(row[j+k] for j in range(0,28,4)) for k in range(4)]
        return tuple(row)
    sch=SparseScheduler(state,list(hs.values()),arcs,max_active=1024,max_rounds=256,max_visits=24576*256)
    sch.start(tuple(sorted(inputs,reverse=reverse)))
    expected=oracle(parent,inputs,cut);trace=[];first=None;t=time.perf_counter()
    while sch.status=='RUNNING':
        rr=sch.step(transport,update);trace.append((rr.status,rr.sources,rr.arcs,rr.destinations,rr.changed,rr.touched))
        if first is None and state.read(hs[root])[28]!=0:first=sch.rounds
    elapsed=time.perf_counter()-t
    require(sch.status=='QUIESCENT','BUDGET_STOP')
    require(state.read(hdecoy)==sentinel,'UNENROLLED_STATE_MUTATED')
    dig=hashlib.sha256();rows=0
    for v in sorted(parent):
        row=state.read(hs[v]);require(row[28:32]==expected[v],('ORACLE',v,row[28:32],expected[v]))
        require(row[:4]==(stats(inputs[v]) if v in inputs else ZERO),'LOCAL_INPUT_MUTATED')
        for j,u in enumerate(sorted(children[v])):
            require(row[4+4*j:8+4*j]==(ZERO if u==cut else expected[u]),'CHILD_SNAPSHOT_DRIFT')
        for j in range(len(children[v]),6):require(row[4+4*j:8+4*j]==ZERO,'UNUSED_SLOT_MUTATED')
        dig.update(pack('<I'+'d'*WIDTH,v,*row));rows+=1
    total=state.read(hs[root])[28:32];count,s,ss,pos=total
    return dict(mode=mode,root_stats=total,mean=s/count if count else None,variance=(ss/count-(s/count)**2) if count else None,positive_majority=(pos*2>count) if count else None,rows=rows,rounds=sch.rounds,visits=sch.visits,max_frontier=max(r[1] for r in trace),max_touched=max(r[5] for r in trace),first_root_round=first,state_sha256=dig.hexdigest(),trace_sha256=hashlib.sha256(repr(trace).encode()).hexdigest(),elapsed_seconds=elapsed,payload=state.payload(),decoy_unchanged=True)

def main(repo,stage,src,local=False):
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(240,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    sys.path[:0]=[str(repo),str(src)]
    if not local:
        from smoke import restrict_writes
        restrict_writes(stage)
    from GEO144K import g1c_compact as geo,g2b_bridge as bridge
    from geodome_index import GeoIndex
    start=time.monotonic();idx=build(geo,bridge,GeoIndex)
    require(idx.mapping_sha256()=='abe96202b554608bd8f5e702b70459daaaf4ab33eb7dfd058723fd4d1724f51b','MAP_PIN')
    require(idx.edge_sha256()=='712a8fc3d94685aeb614456ba8c88f6df7e6c6ea8a4c19e86d4d3865ad014231','EDGE_PIN')
    records=[];controls=0
    for root,radius in ((0,4),(42042,9),(65000,15)):
        parent,depth,children=tree(idx,root,radius)
        require(len(parent)<=4095,'ENROLLMENT')
        for seed in (701,702,703):
            rng=random.Random(seed+root);population=sorted(v for v in parent if v!=root)
            far=max(population,key=lambda v:(depth[v],v));chosen={far,*rng.sample(population,min(31,len(population)))}
            inputs={v:rng.choice(tuple(range(-9,0))+tuple(range(1,10))) for v in sorted(chosen)}
            # Cut the root-child arc which carries the deepest selected source.
            cut=far
            while parent[cut]!=root:cut=parent[cut]
            full=oracle(parent,inputs,None)[root]
            require(full[0]==len(inputs) and full[1]==sum(inputs.values()) and full[2]==sum(x*x for x in inputs.values()) and full[3]==sum(x>0 for x in inputs.values()),'DIRECT_CENTRAL_ORACLE')
            negate=dict(inputs);negate[far]=-negate[far]
            erase=dict(inputs);del erase[far]
            conditions=(('intact',inputs,None),('cut',inputs,cut),('negate',negate,None),('erase',erase,None),('remote_only',{far:inputs[far]},None),('remote_cut',{far:inputs[far]},cut))
            by={}
            for name,values,blocked in conditions:
                a=run(idx,root,parent,depth,children,values,blocked,'sparse');b=run(idx,root,parent,depth,children,values,blocked,'dense',True)
                require(a['state_sha256']==b['state_sha256'] and a['trace_sha256']==b['trace_sha256'],'DENSE_SPARSE_ORDER_DRIFT')
                require(a['root_stats']==b['root_stats'],'READOUT_DRIFT')
                by[name]=a
                records.append(dict(root=root,radius=radius,seed=seed,condition=name,enrolled=len(parent),source_count=len(values),cut_vertex=blocked,remote_depth=depth[far],sparse=a,dense=b))
            orig=by['intact']['root_stats'];cut_stats=by['cut']['root_stats'];neg=by['negate']['root_stats'];erased=by['erase']['root_stats'];x=inputs[far]
            require(cut_stats[0]<orig[0],'CUT_NO_EFFECT');controls+=1
            require(neg==plus(orig,(0.,-2.*x,0.,float(x<0)-float(x>0))),'NEGATION_EFFECT');controls+=1
            require(erased==tuple(a-b for a,b in zip(orig,stats(x))),'ERASURE_EFFECT');controls+=1
            require(by['remote_only']['first_root_round']==depth[far] and by['remote_only']['root_stats']==stats(x),'CAUSAL_HOP_DEPTH');controls+=1
            require(by['remote_cut']['first_root_round'] is None and by['remote_cut']['root_stats']==ZERO,'REMOTE_CUT_LEAK');controls+=1
            emit('C7_CASE',dict(root=root,radius=radius,seed=seed,enrolled=len(parent),sources=len(inputs),remote_depth=depth[far],root_stats=orig,cut_root_stats=cut_stats,negated_root_stats=neg,erased_root_stats=erased))
    require(len(records)==54 and controls==45,'INCOMPLETE_MATRIX')
    # Reproducible numerical/trace receipt, independent of memory, timing and mode.
    deterministic=[dict(root=r['root'],radius=r['radius'],seed=r['seed'],condition=r['condition'],cut_vertex=r['cut_vertex'],remote_depth=r['remote_depth'],enrolled=r['enrolled'],source_count=r['source_count'],**{k:r['sparse'][k] for k in ('root_stats','rows','rounds','visits','max_frontier','max_touched','first_root_round','state_sha256','trace_sha256')}) for r in records]
    digest=hashlib.sha256(json.dumps(deterministic,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for r in records:emit('C7_DETAIL',r)
    print('=== SEND BACK ===',flush=True)
    emit('C7_RESULT',dict(phase='GEO_CLOSE_C7_R0',status='PASS_EXACT_DISTRIBUTED_COMPOSITION',local_reconstruction=local,vertices=idx.vertices,mapping_sha256=idx.mapping_sha256(),edge_sha256=idx.edge_sha256(),fixtures=9,paired_cases=len(records),scheduler_runs=len(records)*2,oracle_rows=sum(r['enrolled']*2 for r in records),causal_controls=controls,dense_sparse_order_parity=True,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,total_seconds=time.monotonic()-start,deterministic_sha256=digest,max_enrolled=max(r['enrolled'] for r in records),max_frontier=max(r['sparse']['max_frontier'] for r in records),max_touched=max(r['sparse']['max_touched'] for r in records),max_rounds=max(r['sparse']['rounds'] for r in records),full_root_cases=9,remote_depths=sorted({r['remote_depth'] for r in records}),CGC='NOT_RUN',HCA88='NOT_RUN',KV_cache='NOT_ALLOCATED',learned_competence='NOT_RUN',task='EXACT_INTEGER_SUFFICIENT_STATISTICS_TREE_REDUCTION',routing='HOST_SUPPLIED_PHYSICAL_TREE',runtime_persistent_writes='LOCAL_NO_SANDBOX' if local else 'NONE'))
    print('NEXT_GATE=GEO_CLOSE_C8_REPRODUCTION',flush=True)
if __name__=='__main__':main(*(Path(x).resolve() for x in sys.argv[1:4]),local=len(sys.argv)>4 and sys.argv[4]=='--local')
