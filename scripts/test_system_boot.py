#!/usr/bin/env python3
"""Boot the offline MIPS Linux guest and summarize only non-secret test markers."""
import hashlib
import json
from pathlib import Path
import re
import selectors
import subprocess
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
run_id=uuid.uuid4().hex[:8]
name='wemo-system-test-'+run_id
folder=ROOT/'artifacts/system-tests'/run_id
folder.mkdir(parents=True)
command=['docker','run','--rm','--name',name,'--network','none','--cap-drop','ALL',
         '--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp',
         '-v',f'{ROOT}/artifacts/kernel-malta:/kernel:ro',
         '-v',f'{ROOT}/artifacts/system-image:/images:ro',
         'wemo-matter-board-builder:bookworm','qemu-system-mipsel',
         '-M','malta','-cpu','24KEc','-m','64M','-nographic','-monitor','none',
         '-no-reboot','-kernel','/kernel/vmlinux','-initrd','/images/guest-initramfs.cpio.gz',
         '-append','console=ttyS0,115200 rdinit=/init wemo.offline_test=1 rng_core.default_quality=1024 panic=-1',
         '-vga','none','-netdev','user,id=net0,restrict=on','-device','pcnet,netdev=net0,romfile=','-object','rng-random,filename=/dev/urandom,id=rng0',
         '-device','virtio-rng-pci,rng=rng0']
report={'run_id':run_id,'machine':'QEMU Malta; not an emulated MT7688 board',
        'cpu':'24KEc','guest_memory_bytes':64*1024*1024,'docker_network':'none',
        'wifi':'mac80211_hwsim virtual radios in separate guest network namespaces',
        'relay':'temporary value file; physical GPIO disabled','physical_wemo_touched':False,
        'tests':[],'passed':False}
start=time.monotonic()
process=None
try:
    with (folder/'console.log').open('wb') as log:
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
        buffer=b''
        while process.poll() is None:
            if time.monotonic()-start>900:raise TimeoutError('Guest boot/test exceeded 15 minutes')
            for key,_ in selector.select(timeout=1):
                chunk=key.fileobj.read1(65536)
                if not chunk:continue
                log.write(chunk);log.flush();buffer+=chunk
                while b'\n' in buffer:
                    line,buffer=buffer.split(b'\n',1)
                    marker=re.search(rb'WEMO_GUEST_PASS=([a-zA-Z0-9_.-]+)',line)
                    if marker:
                        label=marker[1].decode(); report['tests'].append(label);print('PASS:',label,flush=True)
        remainder=process.stdout.read();log.write(remainder)
    text=(folder/'console.log').read_text(errors='replace')
    report['tests'] = re.findall(r'WEMO_GUEST_PASS=([a-zA-Z0-9_.-]+)', text)
    report['passed']=(process.returncode==0 and 'WEMO_GUEST_EXIT=0' in text and
                      'WEMO_GUEST_PASS=full-mips-kernel-rootfs-wifi-matter-relay' in text and
                      'WEMO_GUEST_FAIL=' not in text)
    report['wall_seconds']=round(time.monotonic()-start,2)
    report['guest_meminfo_observations']=re.findall(r'(?:MemTotal|MemFree|MemAvailable|Buffers):\s+\d+ kB',text)
    for path in ('artifacts/kernel-malta/vmlinux','artifacts/system-image/guest-initramfs.cpio.gz'):
        report.setdefault('artifacts',{})[path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    if not report['passed']:raise RuntimeError(f'Guest test failed; inspect {folder}/console.log')
finally:
    subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if process is not None and process.poll() is None:process.wait(timeout=10)
    (folder/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['passed']:(ROOT/'research/system-boot-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Local console:',folder/'console.log',flush=True)
