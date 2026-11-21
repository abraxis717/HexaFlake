#!/usr/bin/env python3
"""Reconstruct hash-pinned Geodome sources in RAM; fail closed on prerequisites."""
import argparse, hashlib, json, os, resource, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAM = Path('/dev/shm')
GIB = 1024**3
EXPECTED = {'api_version':'1.0.0','vertices':144002,'edges':432000,
 'mapping_sha256':'abe96202b554608bd8f5e702b70459daaaf4ab33eb7dfd058723fd4d1724f51b',
 'edge_sha256':'712a8fc3d94685aeb614456ba8c88f6df7e6c6ea8a4c19e86d4d3865ad014231',
 'consumer_sha256':'405ad9f3fe94258cd227f9b1823e974b6b91bdf10567b54c4ec759ab7c4c4c89',
 'index_payload_bytes':11502238,'dense_sparse_parity':True,'negative_controls':5,'core_neural_imports':False}
CORE = ('geodome.py','geodome_index.py','geodome_state.py','geodome_scheduler.py')
GEOMETRY = ('Hexaflag.py','GEO144K/g1c_compact.py','GEO144K/g2b_bridge.py')
NEURAL = ('CGC120.py','src/ecsg_e0.py','HCA88.c','HCA88.h')

def require(ok,label):
    if not ok: raise RuntimeError(label)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    for line in (HERE/'PUBLIC.sha256').read_text().splitlines():
        digest, name = line.split('  ',1); p=ROOT/name
        require(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT), 'MISSING_OR_EXTERNAL:'+name)
        require(sha(p)==digest,'SOURCE_DRIFT:'+name)

def preflight(neural):
    require(sys.platform=='linux' and os.uname().machine=='x86_64','LINUX_X86_64_REQUIRED')
    require(any(l.split()[4]==str(RAM) and l.split(' - ',1)[1].split()[0]=='tmpfs' for l in Path('/proc/self/mountinfo').read_text().splitlines()),'TMPFS_REQUIRED')
    info={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemAvailable:','SwapTotal:'))}
    require(info['SwapTotal']==0,'SWAP_MUST_BE_DISABLED')
    require(info['MemAvailable']>= (5 if neural else 1)*GIB,'RAM_FLOOR')
    require(shutil.disk_usage(RAM).free>=64*1024**2,'TMPFS_FLOOR')
    if neural: require(shutil.which('cc') is not None,'C11_COMPILER_REQUIRED')

def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)

def child(script,args,scratch,neural=False):
    scratch.mkdir(); env=dict(os.environ)
    for k in ('PYTHONPATH','PYTHONHOME','LD_PRELOAD','LD_LIBRARY_PATH','BASH_ENV','ENV'):
        # Retain LD_LIBRARY_PATH only for an explicit trusted native environment? No:
        # the qualified replay needs no injected libraries.
        env.pop(k,None)
    env.update({k:str(scratch) for k in ('HOME','TMPDIR','TMP','TEMP','XDG_CACHE_HOME','TORCH_HOME')})
    env.update(PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    cmd=[sys.executable,'-I','-B']+([] if neural else ['-S'])+[str(script),*map(str,args)]
    # The parent owns a bounded RAM log; the restricted child only inherits this fd.
    log=scratch/'output.txt'
    def limits():
        resource.setrlimit(resource.RLIMIT_AS,((4 if neural else 1)*GIB,)*2)
        resource.setrlimit(resource.RLIMIT_CPU,(240,240))
        resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,)*2)
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    with log.open('wb') as f:
        result=subprocess.run(cmd,cwd=scratch,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=300,preexec_fn=limits)
    out=log.read_text(errors='replace')
    if result.returncode or 'VOLATILE_WRITE_BOUNDARY=PASS' not in out:
        print('\n'.join(out.splitlines()[-20:]),flush=True); raise RuntimeError('CHILD_HOLD:'+script.name)
    return out

def main(mode):
    neural=mode=='replay'; preflight(neural); verify()
    with tempfile.TemporaryDirectory(prefix='geodome-reference-',dir=RAM) as d:
        stage=Path(d); public=stage/'repo'; core=stage/'core'; src=stage/'src'; logs=stage/'logs'; logs.mkdir()
        for n in (*GEOMETRY,'smoke.py','README.md',*(NEURAL if neural else ())):
            copy(ROOT/n,public/n)
        for n in GEOMETRY: copy(ROOT/n,core/n)
        for n in CORE: copy(HERE/n,core/n); copy(HERE/n,src/n)
        if neural: copy(HERE/'adapters/geodome_compute.py',src/'geodome_compute.py')
        for f in (HERE/'qualification').glob('*.py'): copy(f,src/f.name)
        if mode=='example':
            out=child(HERE/'example.py',(core,public,stage/'example'),stage/'example'); print(out.strip())
        else:
            gates=range(1,8) if neural else (1,2,3,5,6,7) if mode=='stdlib-replay' else ()
            for n in gates:
                scratch=stage/f'c{n}'
                out=child(src/f'replay_c{n}.py',(public,scratch,src),scratch,neural=n==4)
                (logs/f'C{n}.txt').write_text(out)
                result=subprocess.run([sys.executable,'-I','-S','-B',str(src/'compare.py'),str(n),str(HERE/'evidence'),str(logs)],check=True,capture_output=True,text=True,timeout=10)
                print(result.stdout.strip(),flush=True)
            scratch=stage/'c9';out=child(src/'consumer.py',(core,public,scratch),scratch)
            rows=[json.loads(x.split('=',1)[1]) for x in out.splitlines() if x.startswith('API_RESULT=')]
            require(len(rows)==1 and all(rows[0].get(k)==v for k,v in EXPECTED.items()),'C9_INVARIANT_DRIFT')
            print(out.strip(),flush=True)
    verify()
    print('GEODOME_REFERENCE=PASS MODE='+mode+' C4='+('REPLAYED' if neural else 'NOT_RUN'),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for name in ('example','replay','stdlib-replay'): group.add_argument('--'+name,action='store_const',const=name,dest='mode')
    try: main(parser.parse_args().mode or 'consumer')
    except Exception as e: print('GEODOME_REFERENCE=HOLD '+str(e),file=sys.stderr,flush=True); sys.exit(1)
