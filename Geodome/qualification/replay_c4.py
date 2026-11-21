import sys,os,resource,subprocess,ctypes,hashlib,time,json,math,shutil,errno
from pathlib import Path
from array import array
from struct import pack

def require(ok,msg):
    if not ok: raise AssertionError(msg)

def main(repo,stage,src,local=False):
    sys.path[:0]=[str(repo),str(src),str(Path(__file__).resolve().parent)]
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    resource.setrlimit(resource.RLIMIT_CPU,(180,180));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,)*2)
    from smoke import restrict_writes
    restrict_writes(stage)
    from GEO144K import g1c_compact as geo,g2b_bridge as bridge
    from geodome_index import GeoIndex
    from geodome_state import NodeState
    import torch
    from geodome_compute import NativeHCA,ComputeWindow
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    t=time.monotonic(); coords,faces=geo.build(120); n=len(coords)//3; edges=bridge.collect_edges(faces,n);del coords,faces
    bfs,_=bridge.graph_bfs_order(edges,n);codes=array('I',[0])*n
    for i,v in enumerate(bfs):codes[v]=bridge.rank_to_code(i,n)
    del bfs;idx=GeoIndex(codes,edges);del codes,edges
    require(idx.mapping_sha256()=='abe96202b554608bd8f5e702b70459daaaf4ab33eb7dfd058723fd4d1724f51b','MAPPING')
    require(idx.edge_sha256()=='712a8fc3d94685aeb614456ba8c88f6df7e6c6ea8a4c19e86d4d3865ad014231','EDGES')
    fd=None
    if local:
        class Reference:
            def transport(self,endpoints,source,passes):
                a=source;b=(0.,)*4
                for _ in range(passes):a,b=tuple((x+y)/2 for x,y in zip(a,b)),tuple((x+y)/2 for x,y in zip(a,b))
                return a+(0.,)*4,b+(0.,)*4,2*passes
        hca=Reference()
    else:
        cc=shutil.which('cc');require(cc is not None,'CC_MISSING');so=stage/'hca88.so'
        subprocess.run([cc,'-std=c11','-O2','-ffp-contract=off','-fPIC','-shared',str(repo/'HCA88.c'),'-lm','-o',str(so)],check=True,timeout=45)
        try:fd=os.memfd_create('geo-hca88',getattr(os,'MFD_EXEC',0x10))
        except OSError as e:
            if e.errno!=errno.EINVAL:raise
            fd=os.memfd_create('geo-hca88',0)
        with os.fdopen(os.dup(fd),'wb') as out:out.write(so.read_bytes())
        hca=NativeHCA(ctypes.CDLL('/proc/self/fd/'+str(fd)))
    native_overlap=None if local else hca.overlap_probe()
    # Include defects, seam vertices, deep face interiors; use genuine edges only.
    paths=[]
    for u in [0,1,11,12,100,3570,3571,10000,30000,60000,100000,144001]:
        v=idx.neighbors(u)[0];w=next(x for x in idx.neighbors(v) if x!=u)
        paths.append((u,v,w))
    state=NodeState(idx,width=16,precision='f64',capacity=64)
    engine=ComputeWindow(idx,state,hca,paths)
    weights=lambda:hashlib.sha256(b''.join(p.detach().numpy().tobytes() for p in engine.model.parameters())).hexdigest()
    initial=weights();require(sum(p.numel() for p in engine.model.parameters())==120,'PARAMETERS')
    phi=lambda z:.5*z+.5*z*z+.5*z*z*z
    expected=lambda xs:6*phi(.1*sum(xs))
    maxerr=0.;checks=0;links=0;digest=hashlib.sha256()
    for path in paths:
        hs=tuple(state.acquire_vertex(v) for v in path);arcs=tuple(idx.arc_id(a,b) for a,b in zip(path,path[1:]))
        for signed in (-1,0,1):
            rows=[(signed*.2,)*5+(0.,)*11,(.1,)*5+(0.,)*11,(.05,)*5+(0.,)*11]
            for passes in (1,2,3):
                state.commit(tuple(zip(hs,rows)));r=engine.step(arcs,hs,passes);links+=r['links'];want=expected(rows[0][:5]);mid=want*.5;out=expected((mid,)*4+(.05,))
                vals=[(x,want) for x in r['source']]+[(x,mid) for x in r['first'][:4]+r['last'][:4]]+[(x,0.) for x in r['first'][4:]+r['last'][4:]]+[(x,out) for x in r['result']]
                err=max(abs(x-y) for x,y in vals);maxerr=max(maxerr,err);require(err<1e-12,'ORACLE_PARITY');checks+=len(vals)
                require(state.read(hs[1])==rows[1],'RELAY_NODE_MUTATED');require(state.read(hs[2])[5:9]==r['result'] and state.read(hs[2])[9:13]==r['last'][:4],'COMMIT');digest.update(pack('<4d',*r['result']))
        for h in hs:state.release(h)
    path=paths[0]; hs=tuple(state.acquire_vertex(v) for v in path);arcs=tuple(idx.arc_id(a,b) for a,b in zip(path,path[1:]));nc=0
    def reject(fn):
        nonlocal nc
        snap=state._values.tobytes()
        try:fn()
        except (ValueError,KeyError,RuntimeError):pass
        else:raise AssertionError('EXPECTED_REJECTION')
        require(snap==state._values.tobytes(),'FAILED_ATOMIC_REJECTION');nc+=1
    reject(lambda:engine.step(arcs[::-1],hs));reject(lambda:engine.step((True,arcs[1]),hs));reject(lambda:engine.step(arcs,hs[::-1]));reject(lambda:engine.step(arcs,hs,0));reject(lambda:engine.step(arcs,hs,4));reject(lambda:engine.step(arcs,hs[:2]));
    state.write(hs[0],(1.,)*16);reject(lambda:engine.step(arcs,hs));state.write(hs[0],(0.,)*16)
    class Failing:
        def transport(self,*args):raise RuntimeError('INJECTED_NATIVE_FAILURE')
    engine.transport=Failing();reject(lambda:engine.step(arcs,hs));engine.transport=hca
    state.release(hs[1]);reject(lambda:engine.step(arcs,hs));state.reset();reject(lambda:engine.step(arcs,hs));require(weights()==initial,'WEIGHT_MUTATION')
    if fd is not None:os.close(fd)
    r=dict(phase='GEO_CLOSE_C4_R0',status='LOCAL_REFERENCE_ONLY' if local else 'PASS_EXPLICIT_PHYSICAL_WINDOW_CGC_HCA88',paths=len(paths),window_cases=len(paths)*9,scalar_oracle_checks=checks,max_abs_error=maxerr,native_links=None if local else links,analytical_reference_links=links if local else None,native_overlap_atomic=native_overlap,negative_controls=nc,shared_cgc_parameters=120,hca_parameters=88,synthetic_weights=True,identity_frames_only=True,transport_scope='EXPLICIT_TWO_ARC_WINDOWS_ONLY',index_payload_bytes=idx.payload_bytes(),state_payload=state.payload(),result_sha256=digest.hexdigest(),peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,elapsed_seconds=time.monotonic()-t,KV_cache='NOT_ALLOCATED',training='NONE',runtime_persistent_writes='NONE',concurrency='SINGLE_THREAD_ONLY')
    print('=== SEND BACK ===');print('C4_RESULT='+json.dumps(r,sort_keys=True));print('NEXT_GATE=GEO_CLOSE_C5_SPARSE_ACTIVATION')
if __name__=='__main__':main(*(Path(x).resolve() for x in sys.argv[1:4]),local='--local-reference' in sys.argv[4:])
