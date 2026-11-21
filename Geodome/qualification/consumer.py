import sys,resource,json,hashlib
from pathlib import Path

def require(ok,label):
    if not ok: raise AssertionError(label)

def reject(fn,kind):
    try: fn()
    except kind: return
    raise AssertionError('EXPECTED_REJECTION')

def run(core):
    sys.path.insert(0,str(core))
    import geodome as g
    require(g.API_VERSION=='1.0.0','VERSION')
    idx=g.build_index(); u=0; v=idx.neighbors(u)[0]; w=next(x for x in idx.neighbors(v) if x!=u and x not in idx.neighbors(u))
    arcs=(idx.arc_id(u,v),idx.arc_id(v,w))
    require(tuple(idx.arc_endpoints(a) for a in arcs)==((u,v),(v,w)),'ARCS')
    require(idx.prefix_count((0,))==144002 and len(idx.prefix_page((0,)))==1024,'PREFIX')
    for x in (u,v,w,144001):
        require(idx.resolve(idx.address(x))==x and idx.resolve_coordinate(idx.coordinate(x))==x,'IDENTITY')
    reject(lambda:idx.arc_id(u,w),KeyError)
    results=[]; controls=1
    for mode in ('sparse','dense'):
        s=g.new_state(idx,width=2,mode=mode,capacity=3 if mode=='sparse' else None)
        hs=tuple(s.acquire_address(idx.address(x)) for x in (u,v,w)); s.write(hs[0],(7.,1.))
        def transport(a,u,v,row): return row
        def update(v,old,inbox): return inbox[0][1]
        sch=g.SparseScheduler(s,hs,arcs,max_active=3,max_rounds=4,max_visits=2); sch.start((u,))
        sch.step(transport,update); require(s.read(hs[2])==(0.,0.),'SYNCHRONOUS')
        sch.step(transport,update); require(s.read(hs[2])==(7.,1.),'PROPAGATION')
        sch.step(transport,update); require(sch.status=='QUIESCENT' and sch.visits==2,'HALT')
        results.append([s.read(h) for h in hs]); s.reset(); reject(lambda:s.read(hs[0]),ValueError); controls+=1
        require(s.resident==0,'RESET')
        new=s.acquire_vertex(u); require(s.read(new)==(0.,0.),'ZERO')
        reject(lambda:g.SparseScheduler(s,(new,),arcs),ValueError); controls+=1
    require(results[0]==results[1],'RESIDENCY_PARITY')
    for m in ('geodome','geodome_index','geodome_state','geodome_scheduler','Hexaflag','GEO144K.g1c_compact','GEO144K.g2b_bridge'):
        require(Path(sys.modules[m].__file__).resolve().is_relative_to(core),'IMPORT_ESCAPE:'+m)
    forbidden=('torch','CGC120','geodome_compute','numpy')
    require(not any(m==x or m.startswith(x+'.') for m in sys.modules for x in forbidden),'CORE_DEPENDENCY')
    return dict(api_version=g.API_VERSION,vertices=idx.vertices,edges=idx.edges,mapping_sha256=idx.mapping_sha256(),edge_sha256=idx.edge_sha256(),index_payload_bytes=idx.payload_bytes(),dense_sparse_parity=True,negative_controls=controls,core_neural_imports=False,consumer_sha256=hashlib.sha256(json.dumps(results).encode()).hexdigest(),peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)

if __name__=='__main__':
    core=Path(sys.argv[1]).resolve()
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,)*2); resource.setrlimit(resource.RLIMIT_CORE,(0,0)); resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    if len(sys.argv)==4:
        public=Path(sys.argv[2]).resolve(); sys.path.insert(0,str(public)); from smoke import restrict_writes; sys.path.pop(0); restrict_writes(Path(sys.argv[3]).resolve())
    elif len(sys.argv)!=2: raise SystemExit('ARGS')
    print('API_RESULT='+json.dumps(run(core),sort_keys=True),flush=True)
