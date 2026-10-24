#!/bin/sh
set -eu
variant=$1
binary=$2
[ "$variant" = baseline ] || [ "$variant" = outlet ] || [ "$variant" = lto ] || [ "$variant" = minimal ] || [ "$variant" = lean ] || [ "$variant" = compact ] || [ "$variant" = oz ] || [ "$variant" = ozcompile ]
mkdir -p /export/$variant /sdk/package-$variant/usr/bin
cp "$binary" /sdk/package-$variant/usr/bin/wemo-matter-outlet
mksquashfs /sdk/package-$variant /export/$variant/app.squashfs -noappend -all-root -comp xz -b 262144 -no-xattrs -processors 1 -mkfs-time 0 -all-time 0 > /export/$variant/compression.log
xz -c -9 "$binary" > /export/$variant/app.xz
sha256sum "$binary" /export/$variant/app.squashfs /export/$variant/app.xz
wc -c "$binary" /export/$variant/app.squashfs /export/$variant/app.xz
unsquashfs -cat /export/$variant/app.squashfs usr/bin/wemo-matter-outlet | cmp - "$binary"
