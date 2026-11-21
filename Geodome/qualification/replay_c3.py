"""Full C3 qualification, under the published write boundary on workstation."""
import sys,resource,time,json,hashlib
from array import array
from pathlib import Path
from dataclasses import replace
from struct import pack

def require(x,label):
    if not x: raise AssertionError(label)
def rejects(fn,kind):
    try: fn()
    except kind: return
    raise AssertionError('EXPECTED_REJECTION')
def rss():
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('VmRSS:'): return int(line.split()[1])*1024
    raise RuntimeError('RSS_UNAVAILABLE')
def peak(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024

def row(v,w): return tuple(((v*31+j*7)%257-128)/16 for j in range(w))

def controls(idx):
    from geodome_state import NodeState,MAX_BATCH
    s=NodeState(idx,width=4,precision='f32',capacity=3); other=NodeState(idx,width=4,precision='f32',capacity=3)
    h=s.acquire_address(idx.address(0)); j=s.acquire_vertex(1); k=s.acquire_vertex(2); oh=other.acquire_vertex(0)
    s.commit(((h,[1,2,3,4]),(j,[4,3,2,1]),(k,[5,6,7,8])))
    snapshot=lambda: (s._values.tobytes(),s._generation.tobytes(),s._slot_owner.tobytes(),s._vertex_slot.tobytes(),s._free.tobytes(),s.resident,s.epoch)
    count=0
    def bad(fn,kind):
        nonlocal count
        before=snapshot(); rejects(fn,kind); require(snapshot()==before,'REJECTION_MUTATED_STATE'); count+=1
    bad(lambda:s.acquire_vertex(3),OverflowError)
    bad(lambda:s.acquire_vertex(0),ValueError)
    bad(lambda:s.acquire_vertex(True),ValueError)
    bad(lambda:s.acquire_vertex(idx.vertices),ValueError)
    bad(lambda:s.read(oh),ValueError)
    bad(lambda:s.write(oh,[0]*4),ValueError)
    bad(lambda:s.release(oh),ValueError)
    bad(lambda:s.read(replace(h,slot=-1)),ValueError)
    bad(lambda:s.read(replace(h,generation=h.generation+1)),ValueError)
    bad(lambda:s.read(replace(h,vertex=1)),ValueError)
    bad(lambda:s.commit(((h,[0]*4),(j,[float('nan')]*4))),ValueError)
    bad(lambda:s.commit(((h,[0]*4),(j,[float('inf')]*4))),ValueError)
    bad(lambda:s.commit(((h,[0]*4),(j,[1e100]*4))),ValueError)
    bad(lambda:s.commit(((h,[0]*4),(j,[1,2,3]))),ValueError)
    bad(lambda:s.commit(((h,[0]*4),(j,[True]*4))),ValueError)
    bad(lambda:s.commit(((h,[0]*4),(oh,[0]*4))),ValueError)
    bad(lambda:s.commit(((h,[0]*4),(h,[1]*4))),ValueError)
    bad(lambda:s.commit(()),ValueError)
    bad(lambda:s.commit(((h,[0]*4),)*(MAX_BATCH+1)),ValueError)
    bad(lambda:s.commit(((h,[0]*4),(j,))),ValueError)
    # Snapshot is independent of caller input and returned read is immutable.
    data=[11,12,13,14]; s.write(h,data); data[0]=999
    require(s.read(h)==(11.,12.,13.,14.) and other.read(oh)==(0.,)*4,'ALIASED_OR_CROSS_STORE')
    old=h;s.release(h); require(s.resident==2,'RELEASE_COUNT')
    bad(lambda:s.read(old),ValueError); bad(lambda:s.release(old),ValueError); bad(lambda:s.handle(0),KeyError)
    h=s.acquire_vertex(3); require(h.slot==old.slot and s.read(h)==(0.,)*4,'SLOT_REUSE_NOT_ZERO')
    bad(lambda:s.write(old,[1]*4),ValueError)
    s.release(h); h=s.acquire_vertex(0); require(s.read(h)==(0.,)*4,'SAME_VERTEX_REUSE_NOT_ZERO')
    bad(lambda:s.read(old),ValueError)
    s.write(h,[8]*4); before_epoch=s.epoch;s.reset()
    require(s.epoch==before_epoch+1 and s.resident==0 and not any(s._values),'RESET_ZERO_OR_EPOCH')
    h2=s.acquire_vertex(0); require(s.read(h2)==(0.,)*4,'RESET_REACQUIRE')
    for old in (h,j,k): bad(lambda old=old:s.read(old),ValueError)
    require(other.read(oh)==(0.,)*4,'OTHER_STORE_RESET')
    return count

def exercise(idx,mode,width,precision,capacity,count):
    from geodome_state import NodeState
    t=time.monotonic(); baseline=rss(); s=NodeState(idx,width,precision,mode,capacity)
    initial=s.payload(); allocated_rss=rss()
    require(s.resident==0,'INITIAL_COUNT')
    # Deterministic distinct vertices distributed across the entire domain.
    vertices=range(idx.vertices) if count==idx.vertices else tuple((i*7919)%idx.vertices for i in range(count))
    require(len(set(vertices))==count,'TEST_VERTEX_COLLISION')
    for v in vertices:
        h=s.acquire_vertex(v); require(s.read(h)==(0.,)*width,'INITIAL_ROW')
        s.write(h,row(v,width))
    require(s.resident==count,'RESIDENT_COUNT')
    filled=s.payload(); filled_rss=rss(); digest=hashlib.sha256()
    for v in vertices:
        h=s.handle(v); actual=s.read(h); require(actual==row(v,width),'STATE_ROUNDTRIP')
        digest.update(pack('<I',v)); digest.update(pack('<'+('f' if precision=='f32' else 'd')*width,*actual))
    if count==capacity and count<idx.vertices:
        outside=next(v for v in range(idx.vertices) if v not in set(vertices))
        rejects(lambda:s.acquire_vertex(outside),OverflowError)
    # All populated slots are released and verified zero; old handle cannot be reused.
    first_v=vertices[0]; stale=s.handle(first_v)
    for v in vertices: s.release(s.handle(v))
    require(s.resident==0 and not any(s._values),'EXHAUSTIVE_RELEASE_ZERO')
    require(all(v==-1 for v in s._slot_owner) and (mode=='dense' or (len(s._free)==capacity and len(set(s._free))==capacity and all(v==-1 for v in s._vertex_slot))),'RELEASE_METADATA')
    rejects(lambda:s.read(stale),ValueError)
    h=s.acquire_vertex(first_v); require(s.read(h)==(0.,)*width,'RECLAIM_ZERO'); rejects(lambda:s.read(stale),ValueError)
    s.write(h,row(first_v,width)); s.reset(); require(s.resident==0 and not any(s._values),'RESET_ALL_SLOTS'); rejects(lambda:s.read(h),ValueError)
    h=s.acquire_vertex(first_v); require(s.read(h)==(0.,)*width,'RESET_ROW'); s.release(h)
    result=dict(mode=mode,precision=precision,width=width,capacity=capacity,verified_rows=count,initial=initial,filled=filled,baseline_rss_bytes=baseline,allocated_rss_bytes=allocated_rss,filled_rss_bytes=filled_rss,process_highwater_bytes=peak(),state_sha256=digest.hexdigest(),elapsed_seconds=time.monotonic()-t,status='PASS')
    print('C3_ARM='+json.dumps(result,sort_keys=True),flush=True)
    return result

def main(repo,stage,source):
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,)*2)
    resource.setrlimit(resource.RLIMIT_CPU,(240,)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    sys.path[:0]=[str(repo),str(source),str(Path(__file__).resolve().parent)]
    from smoke import restrict_writes
    restrict_writes(stage)
    from GEO144K import g1c_compact as geo,g2b_bridge as bridge
    from geodome_index import GeoIndex
    t=time.monotonic(); coords,faces=geo.build(120); n=len(coords)//3; edges=bridge.collect_edges(faces,n); del coords,faces
    bfs,_=bridge.graph_bfs_order(edges,n); codes=array('I',[0])*n
    for i,v in enumerate(bfs): codes[v]=bridge.rank_to_code(i,n)
    del bfs; idx=GeoIndex(codes,edges); del codes,edges
    require(idx.mapping_sha256()=='abe96202b554608bd8f5e702b70459daaaf4ab33eb7dfd058723fd4d1724f51b','C2_MAPPING_DRIFT')
    require(idx.edge_sha256()=='712a8fc3d94685aeb614456ba8c88f6df7e6c6ea8a4c19e86d4d3865ad014231','C2_EDGE_DRIFT')
    nc=controls(idx); print('NEGATIVE_CONTROLS='+str(nc),flush=True)
    records=[exercise(idx,'sparse',16,'f64',4096,4096),exercise(idx,'dense',16,'f64',n,4096),exercise(idx,'dense',16,'f64',n,n),exercise(idx,'dense',64,'f32',n,n)]
    require(records[0]['state_sha256']==records[1]['state_sha256'],'DENSE_SPARSE_PARITY')
    r=dict(phase='GEO_CLOSE_C3_R0',status='PASS_BOUNDED_VOLATILE_STATE_LIFECYCLE',vertices=n,index_payload_bytes=idx.payload_bytes(),mapping_sha256=idx.mapping_sha256(),edge_sha256=idx.edge_sha256(),negative_controls=nc,dense_sparse_parity=True,records=records,total_seconds=time.monotonic()-t,peak_rss_bytes=peak(),runtime_persistent_writes='NONE',KV_cache='NOT_ALLOCATED',CGC='NOT_RUN',HCA88='NOT_RUN',transport_authority='NOT_GRANTED',concurrency='SINGLE_THREAD_ONLY',active_compute='NOT_RUN')
    print('=== SEND BACK ==='); print('C3_RESULT='+json.dumps(r,sort_keys=True)); print('NEXT_GATE=GEO_CLOSE_C4_AUTHENTIC_CGC_HCA88')
if __name__=='__main__': main(*(Path(x).resolve() for x in sys.argv[1:4]))
