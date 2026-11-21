"""C4: bounded explicit two-arc windows; no learned routing, no global scheduler.
HCA88 relation rows are temporary, not node state. Identity frames are a fixture,
not qualified chart transport. Trust boundary is the sandbox, not Python objects.
"""
import ctypes as C
from math import atanh,isfinite
import torch
from CGC120 import CGC120

class NativeHCA:
    def __init__(self,lib):
        self.lib=lib
        lib.awr_abi_version.restype=C.c_int
        if lib.awr_abi_version()!=4: raise RuntimeError('HCA_ABI')
        i=C.c_int32; q=C.c_int64; d=C.c_double
        pi=C.POINTER(i); pq=C.POINTER(q); pd=C.POINTER(d)
        self.fn=lib.awr_execute
        self.fn.argtypes=[i,pi,pi,i,pi,pd,pd,pd,pd,pq,pi,pd,pd,pd,i,d,d,i,i,pi,pi,pi,pq,i]
        self.fn.restype=C.c_int
    def overlap_probe(self):
        # Two identical windows share both rows: exclusive mode must reject
        # the complete transaction without altering the caller's pool.
        i=C.c_int32; q=C.c_int64; d=C.c_double
        slots=(i*8)(0,1,-1,-1,0,1,-1,-1); rows=(i*2)(0,1)
        pool=(d*16)(*([.125]*16)); original=bytes(pool)
        ba=(d*16)(); bb=(d*16)(); cand=(d*64)()
        offsets=(q*3)(0,2,4); members=(i*4)(0,1,1,2)
        frames=(d*32)(*([1.,0.,0.,1.,1.,0.,0.,1.]*4))
        weights=(d*80)(); bias=(d*8)(); bias[1]=atanh(.5)
        counts=(i*2)(); off=(i*3)(); listing=(i*8)(); links=q()
        rc=self.fn(2,slots,slots,2,rows,pool,ba,bb,cand,offsets,members,frames,weights,bias,0,0.,0.,2,1,counts,off,listing,C.byref(links),0)
        if rc!=4 or bytes(pool)!=original: raise RuntimeError('NATIVE_OVERLAP_ATOMICITY')
        return True
    def transport(self,endpoints,source,passes=1):
        if type(passes) is not int or not 1<=passes<=3: raise ValueError('PASSES')
        if len(endpoints)!=2 or any(len(e)!=2 or any(type(v) is not int or not 0<=v<144002 for v in e) or e[0]==e[1] for e in endpoints): raise ValueError('ENDPOINTS')
        a,b=endpoints
        if a[1]!=b[0] or len(set(a+b))!=3: raise ValueError('PATH')
        if len(source)!=4 or not all(isfinite(v) and abs(v)<=.5 for v in source): raise ValueError('SOURCE_RANGE')
        i=C.c_int32; q=C.c_int64; d=C.c_double
        slots=(i*4)(0,1,-1,-1); rows=(i*2)(0,1)
        pool=(d*16)(*source,*([0.]*12)); ba=(d*16)(); bb=(d*16)(); cand=(d*32)()
        offsets=(q*3)(0,2,4); members=(i*4)(*sorted(a),*sorted(b))
        frames=(d*32)(*([1.,0.,0.,1.,1.,0.,0.,1.]*4))
        weights=(d*80)(); bias=(d*8)(); bias[1]=atanh(.5)
        counts=(i*2)(); off=(i*3)(); listing=(i*4)(); links=q()
        rc=self.fn(1,slots,slots,2,rows,pool,ba,bb,cand,offsets,members,frames,weights,bias,0,0.,0.,passes,1,counts,off,listing,C.byref(links),0)
        if rc or links.value!=2*passes or not all(isfinite(v) for v in pool): raise RuntimeError(('HCA_FAILURE',rc,links.value))
        return tuple(pool[:8]),tuple(pool[8:]),links.value

class ComputeWindow:
    """Explicit admission of a bounded set of real two-arc paths. No automatic routing."""
    def __init__(self,index,state,transport,paths):
        if state.index is not index or state.width!=16 or state.precision!='f64': raise ValueError('STATE_CONTRACT')
        if type(paths) not in (list,tuple) or not 1<=len(paths)<=1024: raise ValueError('PATH_CAP')
        authorized={}
        for path in paths:
            if type(path) is not tuple or len(path)!=3 or len(set(path))!=3: raise ValueError('PATH')
            u,v,w=path; arcs=(index.arc_id(u,v),index.arc_id(v,w))
            if arcs in authorized: raise ValueError('DUPLICATE_PATH')
            authorized[arcs]=path
        self.index=index; self.state=state; self.transport=transport; self._authorized=authorized
        # Fixed synthetic weights; shared by all nodes, no training or historical checkpoint.
        self.model=CGC120(torch.full((4,5,6),.1,dtype=torch.float64,device='cpu')).eval().requires_grad_(False)
    @torch.no_grad()
    def step(self,arcs,handles,passes=1):
        if type(arcs) is not tuple or len(arcs)!=2 or any(type(a) is not int for a in arcs) or arcs not in self._authorized: raise ValueError('UNAUTHORIZED_WINDOW')
        if type(passes) is not int or not 1<=passes<=3: raise ValueError('PASSES')
        path=self._authorized[arcs]
        if type(handles) is not tuple or len(handles)!=3: raise ValueError('HANDLE_COUNT')
        before=[self.state.read(h) for h in handles]
        if tuple(h.vertex for h in handles)!=path: raise ValueError('HANDLE_PATH_MISMATCH')
        endpoints=tuple(self.index.arc_endpoints(r) for r in arcs)
        if endpoints!=((path[0],path[1]),(path[1],path[2])): raise RuntimeError('ARC_DRIFT')
        if any(abs(x)>.25 for row in before for x in row[:5]): raise ValueError('INPUT_RANGE')
        source=tuple(self.model(torch.tensor([before[0][:5]],dtype=torch.float64))[0].tolist())
        first,last,links=self.transport.transport(endpoints,source,passes)
        if len(first)!=8 or len(last)!=8 or links!=2*passes or not all(isfinite(v) for v in first+last): raise RuntimeError('TRANSPORT_RESULT')
        result=tuple(self.model(torch.tensor([last[:4]+(before[2][4],)],dtype=torch.float64))[0].tolist())
        # Single atomic state-store commit after all native and CGC work succeeds.
        self.state.commit(((handles[0],before[0][:5]+source+before[0][9:]),(handles[2],before[2][:5]+result+last[:4]+before[2][13:])))
        return dict(source=source,first=first,last=last,result=result,links=links)
