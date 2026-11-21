"""Compare only invariant numerical and contract fields, not timings or RSS."""
import sys,json,hashlib
from pathlib import Path
STATUS={1:'PASS_FULL_SCALE_TOPOLOGY_LOGICAL_IDENTITY',2:'PASS_FULL_SCALE_ADDRESS_AND_ARC_RESOLUTION',3:'PASS_BOUNDED_VOLATILE_STATE_LIFECYCLE',4:'PASS_EXPLICIT_PHYSICAL_WINDOW_CGC_HCA88',5:'PASS_BOUNDED_SPARSE_SYNCHRONOUS_PROPAGATION',6:'PASS_BOUNDED_RESOURCE_CHARACTERIZATION',7:'PASS_EXACT_DISTRIBUTED_COMPOSITION'}
FILES={1:'C1_20261121T221935_162287028Z.txt',2:'C2_20261121T222301_861893087Z.txt',3:'C3_20261121T222709_046473500Z.txt',4:'C4_20261121T222957_542390033Z.txt',5:'C5_20261121T223407_709616992Z.txt',6:'C6_20261121T223623_783085645Z.txt',7:'C7_20261121T223925_430012923Z.txt'}
def result(path,n):
    prefix=f'C{n}_RESULT='; rows=[json.loads(x[len(prefix):]) for x in path.read_text().splitlines() if x.startswith(prefix)]
    if len(rows)!=1:raise ValueError(('RESULT_COUNT',str(path),len(rows)))
    r=rows[0]
    if r['phase']!=f'GEO_CLOSE_C{n}_R0' or r['status']!=STATUS[n]:raise ValueError(('STATUS',n,r['status']))
    return r
def select(d,keys):return {k:d[k] for k in keys.split()}
def projection(n,r):
    if n==1:return select(r,'topology address_bridge geometry_negative_controls')
    if n==2:return select(r,'vertices edges coordinate_roundtrips occupied_codes unoccupied_codes_rejected prefixes_tested prefix_memberships prefix_pages directed_arcs negative_controls index_payload_bytes mapping_sha256 edge_sha256')
    if n==3:return dict(**select(r,'vertices index_payload_bytes mapping_sha256 edge_sha256 negative_controls dense_sparse_parity'),records=[select(x,'mode precision width capacity verified_rows initial filled state_sha256 status') for x in r['records']])
    if n==4:return select(r,'paths window_cases scalar_oracle_checks max_abs_error native_links native_overlap_atomic negative_controls shared_cgc_parameters hca_parameters synthetic_weights identity_frames_only transport_scope index_payload_bytes state_payload result_sha256')
    if n in (5,6):
        rootkeys='paired_cases oracle_rows max_enrolled max_frontier index_payload_bytes arc_visits negative_controls dense_sparse_order_parity vertices' if n==5 else 'paired_cases scheduler_runs baseline_runs oracle_rows max_enrolled max_frontier'
        out=select(r,rootkeys)
        if n==6:out['builds']=[select(x,'frequency vertices edges index_payload_bytes mapping_sha256 edge_sha256') for x in r['builds']]
        out['records']=[]
        for x in r['records']:
            y=select(x,'center radius cut' if n==5 else 'center radius cut vertices nodes arcs width repeats index_payload_bytes')
            for m in ('dense','sparse'):
                y[m]=select(x[m],'state_sha256 trace_sha256 rounds visits max_frontier peak_touched nodes arcs reachable sources state_payload' if n==5 else 'state_sha256 trace_sha256 rounds visits max_frontier max_touched payload')
            if n==6:y['baseline']={k:select(v,'arc_visits'+(' rounds' if k=='flat_sync_sweep' else '')) for k,v in x['baseline'].items()}
            out['records'].append(y)
        return out
    return select(r,'vertices mapping_sha256 edge_sha256 fixtures paired_cases scheduler_runs oracle_rows causal_controls dense_sparse_order_parity deterministic_sha256 max_enrolled max_frontier max_touched max_rounds full_root_cases remote_depths task routing')
def main():
    n=int(sys.argv[1]);evidence,logs=map(Path,sys.argv[2:4]);old=result(evidence/FILES[n],n);new=result(logs/f'C{n}.txt',n)
    a,b=projection(n,old),projection(n,new)
    if a!=b:
        print('MISMATCH_FIELDS='+repr([k for k in a if a[k]!=b.get(k)]),flush=True);raise SystemExit(2)
    digest=hashlib.sha256(json.dumps(b,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    print('REPLAY_C'+str(n)+'='+json.dumps(dict(status='PASS',invariant_sha256=digest,peak_rss_bytes=new.get('peak_rss_bytes'),elapsed_seconds=new.get('total_seconds',new.get('elapsed_seconds'))),sort_keys=True),flush=True)
if __name__=='__main__':main()
