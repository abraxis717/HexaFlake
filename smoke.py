#!/usr/bin/env python3
"""Run bounded HexaFlake smoke tests without persistent runtime writes."""
import argparse
import ctypes
import errno
import os
from pathlib import Path
import resource
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def restrict_writes(stage):
    # Linux x86-64 Landlock syscall numbers; ABI 3 includes truncate protection.
    if sys.platform != 'linux' or os.uname().machine != 'x86_64':
        raise RuntimeError('Linux x86-64 with Landlock ABI >= 3 is required')
    libc = ctypes.CDLL(None, use_errno=True)
    def call(n, *args):
        result = libc.syscall(ctypes.c_long(n), *args)
        if result == -1:
            e = ctypes.get_errno()
            raise OSError(e, os.strerror(e))
        return result
    class Rules(ctypes.Structure):
        _fields_ = [('access', ctypes.c_uint64)]
    class PathRule(ctypes.Structure):
        _fields_ = [('access', ctypes.c_uint64), ('fd', ctypes.c_int32)]
    abi = call(444, ctypes.c_void_p(), ctypes.c_size_t(0), ctypes.c_uint(1))
    if abi < 3:
        raise RuntimeError('Landlock ABI >= 3 required; no unsandboxed fallback')
    rights = sum(1 << b for b in (1,4,5,6,7,8,9,10,11,12,13,14))
    rules = Rules(rights)
    fd = call(444, ctypes.byref(rules), ctypes.c_size_t(ctypes.sizeof(rules)), ctypes.c_uint(0))
    try:
        for path, access in [(stage, rights), ('/dev/null', (1<<1)|(1<<14))]:
            if path == '/dev/null':
                st = os.lstat(path)
                if not stat.S_ISCHR(st.st_mode) or (os.major(st.st_rdev), os.minor(st.st_rdev)) != (1,3):
                    raise RuntimeError('unexpected null device')
            pfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = PathRule(access, pfd)
                call(445, ctypes.c_int(fd), ctypes.c_int(1), ctypes.byref(rule), ctypes.c_uint(0))
            finally:
                os.close(pfd)
        if libc.prctl(38,1,0,0,0) != 0:
            e = ctypes.get_errno()
            raise OSError(e, os.strerror(e))
        call(446, ctypes.c_int(fd), ctypes.c_uint(0))
    finally:
        os.close(fd)
    # Deliberately attempt a write-open, without truncating or writing any data.
    try:
        probe = os.open(ROOT/'README.md', os.O_WRONLY)
    except PermissionError:
        pass
    else:
        os.close(probe)
        raise RuntimeError('write boundary failed')
    print(f'VOLATILE_WRITE_BOUNDARY=PASS LANDLOCK_ABI={abi}', flush=True)


def main(full):
    if sys.platform != 'linux' or os.uname().machine != 'x86_64':
        raise RuntimeError('Linux x86-64 required')
    # Standard Linux RAM-backed filesystem, not a project-specific path.
    ram = Path('/dev/shm')
    mounts = Path('/proc/self/mountinfo').read_text().splitlines()
    if not any(l.split()[4] == str(ram) and l.split(' - ',1)[1].split()[0] == 'tmpfs' for l in mounts):
        raise RuntimeError('RAM-backed shared memory mount required')
    memory = {l.split(':')[0]:int(l.split()[1]) for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemAvailable:', 'SwapTotal:'))}
    if memory['SwapTotal'] != 0:
        raise RuntimeError('swap must be disabled in the execution environment; use a dedicated VM if needed')
    if memory['MemAvailable'] < (5 if full else 1)*1024**2 or shutil.disk_usage(ram).free < 64*1024**2:
        raise RuntimeError('insufficient RAM or shared-memory space')
    cc = shutil.which('cc')
    if not cc:
        raise RuntimeError('C11 compiler not found (install GCC or Clang)')
    with tempfile.TemporaryDirectory(prefix='hexaflake-smoke-', dir=ram) as d:
        # The unrestricted parent only creates and removes private RAM scratch.
        # The child installs the write boundary before launching the compiler.
        pid = os.fork()
        if pid == 0:
            try:
                execute(Path(d), cc, full)
            except Exception as e:
                print(f'HEXAFLAKE_SMOKE=HOLD {e}', file=sys.stderr, flush=True)
                os._exit(1)
            os._exit(0)
        _, status = os.waitpid(pid, 0)
        if status != 0:
            raise RuntimeError('sandboxed smoke failed')
    print('HEXAFLAKE_SMOKE=PASS MODE='+('FULL' if full else 'NATIVE'),flush=True)


def execute(stage, cc, full):
    d = str(stage)
    resource.setrlimit(resource.RLIMIT_AS, ((4 if full else 1)*1024**3,)*2)
    resource.setrlimit(resource.RLIMIT_CPU, (90,90))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CORE, (0,0))
    env = dict(os.environ, HOME=d, TMPDIR=d, TMP=d, TEMP=d, XDG_CACHE_HOME=d,
               TORCH_HOME=d, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
               CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    if full:
        env.pop('PYTHONPATH', None)
    restrict_writes(stage)
    binary = stage/'native-smoke'
    subprocess.run([cc,'-std=c11','-O2','-ffp-contract=off','-I.', 'HCA88.c', 'tests/test_hca88.c','-lm','-o',str(binary)],cwd=ROOT,env=env,check=True,timeout=25)
    # Execute from an anonymous RAM file, including on noexec tmpfs mounts.
    try:
        fd = os.memfd_create('hexaflake-smoke', getattr(os,'MFD_EXEC',0x0010))
    except OSError as e:
        if e.errno != errno.EINVAL:
            raise
        fd = os.memfd_create('hexaflake-smoke',0)
    try:
        with os.fdopen(os.dup(fd),'wb') as f:
            f.write(binary.read_bytes())
        executable = '/proc/self/fd/'+str(fd)
        subprocess.run([executable],env=env,pass_fds=(fd,),check=True,timeout=5)
        bad = subprocess.run([executable,'nan','0','0','0'],env=env,pass_fds=(fd,),capture_output=True,text=True,timeout=5)
        if bad.returncode != 1 or 'FAIL line' not in bad.stderr or bad.stdout:
            raise RuntimeError('invalid input was not rejected as expected')
        print('INVALID_NONFINITE_INPUT_REJECTED=PASS',flush=True)
        if full:
            env.update(HEXAFLAKE_NATIVE_SMOKE=executable, HEXAFLAKE_NATIVE_FD=str(fd))
            subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],cwd=ROOT,env=env,pass_fds=(fd,),check=True,timeout=60)
    finally:
        os.close(fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true', help='also run Python/PyTorch component and coupling tests')
    args = parser.parse_args()
    try:
        main(args.full)
    except Exception as e:
        print(f'HEXAFLAKE_SMOKE=HOLD {e}',file=sys.stderr,flush=True)
        sys.exit(1)
