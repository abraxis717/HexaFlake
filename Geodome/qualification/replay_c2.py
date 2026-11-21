"""Exhaustive C2 qualification, run under the public write boundary."""
import sys, resource, time, json, hashlib
from array import array
from pathlib import Path
from collections import Counter
from struct import pack
REPO=Path(sys.argv[1]).resolve(); STAGE=Path(sys.argv[2]).resolve()
resource.setrlimit(resource.RLIMIT_AS,(1024**3,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(240,)*2)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
sys.path[:0]=[str(REPO),str(Path(__file__).resolve().parent)]
from smoke import restrict_writes
restrict_writes(STAGE)
from GEO144K import g1c_compact as geo, g2b_bridge as bridge
import Hexaflag as hxf
from geodome_index import GeoIndex, address_of, code_of, CAPACITY, DEPTH, SHIFT, MASK

def require(x,label):
    if not x: raise AssertionError(label)

def rejects(fn,kind):
    try: fn()
    except kind: return
    raise AssertionError('EXPECTED_REJECTION')

def qualify(codes,edges,frequency):
    start=time.monotonic(); idx=GeoIndex(codes,edges); n=idx.vertices
    if frequency==120: require(idx.mapping_sha256()=='abe96202b554608bd8f5e702b70459daaaf4ab33eb7dfd058723fd4d1724f51b','C1_MAPPING_DRIFT')
    if frequency==120: require(idx.edge_sha256()=='712a8fc3d94685aeb614456ba8c88f6df7e6c6ea8a4c19e86d4d3865ad014231','C1_EDGE_DRIFT')
    lat=hxf.HexaflagLattice(max_depth=DEPTH)
    reference=array('i',[-1])*CAPACITY
    parent_counts=[Counter() for _ in range(8)]
    coords=set()
    for v,c in enumerate(codes):
        a=bridge.address_of(c); xy=lat.decode(a)
        require(idx.address(v)==a and idx.resolve(a)==v and code_of(a,7)==c,'ADDRESS_ROUNDTRIP')
        require(xy not in coords and idx.coordinate(v)==xy and idx.resolve_coordinate(xy)==v,'COORD_ROUNDTRIP')
        coords.add(xy); reference[c]=v
        for d in range(8): parent_counts[d][c//7**(7-d)]+=1
    del coords
    print('EXHAUSTIVE_COORDINATES=PASS',flush=True)
    empty=0
    for c,v in enumerate(reference):
        if v>=0: require(idx.resolve_code(c)==v,'OCCUPIED_CODE')
        else: rejects(lambda c=c:idx.resolve_code(c),KeyError); empty+=1
    print('EXHAUSTIVE_CODE_SPACE=PASS',flush=True)
    # Independent prefix oracle: scan ascending occupied codes, group by digits.
    ordered=[(c,v) for c,v in enumerate(reference) if v>=0]
    pages=0; memberships=0; prefix_tests=0
    for depth,counts in enumerate(parent_counts):
        cursor=0; factor=7**(7-depth)
        for p in range(7**depth):
            a=address_of(p,depth); k=counts.get(p,0)
            require(idx.prefix_count(a)==k,'PREFIX_COUNT'); prefix_tests+=1
            if not k: require(idx.prefix_page(a)==(),'EMPTY_PREFIX_PAGE'); continue
            require(all(c//factor==p for c,v in ordered[cursor:cursor+k]),'ORACLE_PREFIX_GROUP')
            for off in range(0,k,1024):
                expected=tuple(v for c,v in ordered[cursor+off:cursor+min(k,off+1024)])
                require(idx.prefix_page(a,off)==expected,'PREFIX_MEMBERSHIP'); pages+=1; memberships+=len(expected)
            require(idx.prefix_page(a,k)==(),'END_PAGE'); cursor+=k
        require(cursor==n,'PREFIX_COVERAGE')
    print('EXHAUSTIVE_PREFIXES=PASS',flush=True)
    # Exact directed topological arcs, independent of mutable transport registry.
    incoming=array('I',[0])*n
    for i,e in enumerate(edges):
        u,v=e>>SHIFT,e&MASK
        for r,a,b in ((2*i,u,v),(2*i+1,v,u)):
            require(idx.arc_id(a,b)==r and idx.arc_endpoints(r)==(a,b) and b in idx.neighbors(a),'ARC_IDENTITY')
            require(idx.arc_endpoints(r^1)==(b,a),'REVERSE_ARC'); incoming[b]+=1
    for v in range(n): require(len(idx.neighbors(v))==incoming[v] and len(set(idx.neighbors(v)))==incoming[v],'NEIGHBOR_COVERAGE')
    print('EXHAUSTIVE_ARCS=PASS',flush=True)
    a=idx.address(0); u=next(v for v in range(1,n) if v not in idx.neighbors(0))
    bad=[(lambda:idx.resolve_code(-1),ValueError),(lambda:idx.resolve_code(True),ValueError),(lambda:idx.address(n),ValueError),(lambda:idx.resolve((6,*a[1:7])),ValueError),(lambda:idx.resolve((7,(True,0),*a[2:])),ValueError),(lambda:idx.resolve((7,(9,9),*a[2:])),ValueError),(lambda:idx.resolve_coordinate((10**9,10**9)),ValueError),(lambda:idx.prefix_page((0,),0,1025),ValueError),(lambda:idx.prefix_page((0,),n+1),ValueError),(lambda:idx.arc_id(0,u),KeyError),(lambda:idx.arc_id(0,0),KeyError),(lambda:idx.arc_endpoints(2*idx.edges),ValueError)]
    for fn,kind in bad: rejects(fn,kind)
    broken=array('I',codes); broken[1]=broken[0]; rejects(lambda:GeoIndex(broken,edges),ValueError)
    bad_edges=array('Q',edges); bad_edges[1]=bad_edges[0]; rejects(lambda:GeoIndex(codes,bad_edges),ValueError)
    return dict(vertices=n,edges=idx.edges,coordinate_roundtrips=n,occupied_codes=n,unoccupied_codes_rejected=empty,prefixes_tested=prefix_tests,prefix_memberships=memberships,prefix_pages=pages,directed_arcs=2*idx.edges,negative_controls=len(bad)+2,index_payload_bytes=idx.payload_bytes(),mapping_sha256=idx.mapping_sha256(),edge_sha256=idx.edge_sha256(),audit_seconds=time.monotonic()-start)

if __name__=='__main__':
    start=time.monotonic(); hxf.check_core()
    coords,faces=geo.build(120); edges=bridge.collect_edges(faces,len(coords)//3)
    n=len(coords)//3; del coords,faces
    bfs,_=bridge.graph_bfs_order(edges,n)
    codes=array('I',[0])*n
    for i,v in enumerate(bfs): codes[v]=bridge.rank_to_code(i,n)
    del bfs
    r=qualify(codes,edges,120)
    r.update(phase='GEO_CLOSE_C2_R0',status='PASS_FULL_SCALE_ADDRESS_AND_ARC_RESOLUTION',total_seconds=time.monotonic()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,transport_authority='NOT_GRANTED',HCA88='NOT_RUN',CGC='NOT_RUN',KV_cache='NOT_ALLOCATED',runtime_persistent_writes='NONE')
    print('=== SEND BACK ==='); print('C2_RESULT='+json.dumps(r,sort_keys=True)); print('NEXT_GATE=GEO_CLOSE_C3_VOLATILE_STATE')
