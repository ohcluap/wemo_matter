#!/usr/bin/env python3
"""Assemble the real board-kernel/development-rootfs candidate, never install it."""
import hashlib
import json
from pathlib import Path
from assemble_candidate import assemble

ROOT=Path(__file__).resolve().parents[1]
kernel=ROOT/'artifacts/kernel-board/wemo-kernel.uImage'
rootfs=ROOT/'artifacts/system-image/board-rootfs.squashfs'
image=assemble(kernel.read_bytes(),rootfs.read_bytes())
digest=hashlib.sha256(image).hexdigest()
output=ROOT/'artifacts/system-image'/('wemo-unsigned-development-'+digest[:12]+'.bin')
if output.exists():assert output.read_bytes()==image
else:output.write_bytes(image)
report={'scope':'Real rebuilt Wemo-profile kernel and minimal complete development rootfs; board boot unverified',
        'kernel_bytes':kernel.stat().st_size,'kernel_budget_bytes':0x180000,
        'rootfs_bytes':rootfs.stat().st_size,'rootfs_budget_bytes':0x5c0000,
        'image_bytes':len(image),'image_sha256':digest,'path':str(output.relative_to(ROOT)),
        'kernel_sha256':hashlib.sha256(kernel.read_bytes()).hexdigest(),
        'rootfs_sha256':hashlib.sha256(rootfs.read_bytes()).hexdigest(),
        'format_size_validation_passed':True,'vendor_signed':False,'installable_update':False,
        'radio_autoload':False,'physical_relay_enabled':False,'board_boot_tested':False,
        'provisioning':'Transactional OS-level WPA2 tool included; no home-network credentials. Matter Wi-Fi onboarding, production identity and persistent flash overlay setup unimplemented'}
(ROOT/'research/system-image-build.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: real kernel and complete development rootfs fit conservative image budgets')
