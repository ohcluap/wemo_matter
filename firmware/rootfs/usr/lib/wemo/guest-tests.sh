#!/bin/sh
set -eu
fail() { echo "WEMO_GUEST_FAIL=$1"; tail -n 30 /tmp/hostap.log /tmp/wpa.log /tmp/wpa-wext.log /tmp/device.log /tmp/last-tool.log 2>/dev/null || true; exit 1; }
trap 'echo WEMO_GUEST_UNEXPECTED_FAILURE' 0
pass() { echo "WEMO_GUEST_PASS=$1"; }
ns() { /usr/bin/netns-exec --exec "$station_pid" "$@"; }
tool() {
  label=$1; shift
  /usr/bin/wemo-chip-tool "$@" --storage-directory /tmp/controller > /tmp/last-tool.log 2>&1 || fail "$label"
  pass "$label"
}
start_app() {
  ns env WEMO_RELAY_VALUE_PATH=/tmp/wemo-relay/value /usr/bin/wemo-matter-outlet \
    --KVS /etc/wemo-matter/state/wemo.kvs --interface-id wlan1 --discriminator 3840 --passcode 20202021 > /tmp/device.log 2>&1 &
  app_pid=$!
  i=0
  while ! grep -q 'Server initialization complete' /tmp/device.log; do
    sleep 1; i=$((i+1)); [ "$i" -lt 60 ] || fail app-start
  done
}
[ "$(uname -r)" = 3.18.27 ] || fail kernel-version
pass linux-3.18.27
cat /proc/meminfo | head -n 4
mem_kb=$(awk '/MemTotal:/ {print $2}' /proc/meminfo)
[ "$mem_kb" -ge 40000 ] && [ "$mem_kb" -le 65536 ] || fail guest-memory-envelope
[ -d /sys/class/ieee80211/phy0 ] && [ -d /sys/class/ieee80211/phy1 ] || fail virtual-radios
pass hwsim-radios
ip link set lo up
netns-exec --hold /tmp/station.pid &
i=0
while [ ! -s /tmp/station.pid ]; do sleep 1; i=$((i+1)); [ "$i" -lt 10 ] || fail station-netns; done
station_pid=$(cat /tmp/station.pid)
iw phy phy1 set netns "$station_pid"
ns ip link set lo up
hostapd -B -f /tmp/hostap.log /etc/offline-ap.conf || fail access-point
ns wpa_supplicant -B -D nl80211 -i wlan1 -c /etc/offline-station.conf -f /tmp/wpa.log || fail station
i=0
while ! ns wpa_cli -p /tmp/wpa -i wlan1 status | grep -q 'wpa_state=COMPLETED'; do
  sleep 1; i=$((i+1)); [ "$i" -lt 40 ] || fail wpa2-association
done
pass wpa2-nl80211-association
ns wpa_cli -p /tmp/wpa -i wlan1 terminate >/tmp/wpa-terminate.log
sleep 2
ns wpa_supplicant -B -D wext -i wlan1 -c /etc/offline-station.conf -f /tmp/wpa-wext.log || fail wext-station
i=0
while ! ns wpa_cli -p /tmp/wpa -i wlan1 status | grep -q 'wpa_state=COMPLETED'; do
  sleep 1; i=$((i+1)); [ "$i" -lt 40 ] || fail wpa2-wext-association
done
pass wpa2-wext-association
ip -6 addr add fd7e:ca71:10::1/64 dev wlan0
ns ip -6 addr add fd7e:ca71:10::2/64 dev wlan1
sleep 3
ns ping6 -c 1 -W 5 fd7e:ca71:10::1 || fail wifi-ipv6-datapath
pass wifi-ipv6-between-network-namespaces
mkdir -p /tmp/controller /tmp/wemo-relay
echo 0 > /tmp/wemo-relay/value
start_app
tool commissioning pairing onnetwork-long 1 20202021 3840
grep -q 'Device commissioning completed with success' /tmp/last-tool.log || fail commissioning-result
tool outlet-device-type descriptor read device-type-list 1 1
grep -q 'DeviceType: 266' /tmp/last-tool.log || fail outlet-type
tool off-command onoff off 1 1
[ "$(cat /tmp/wemo-relay/value)" = 0 ] || fail off-file
tool on-command onoff on 1 1
[ "$(cat /tmp/wemo-relay/value)" = 1 ] || fail on-file
tool on-readback onoff read on-off 1 1
grep -q 'OnOff: TRUE' /tmp/last-tool.log || fail on-readback
tool toggle-command onoff toggle 1 1
[ "$(cat /tmp/wemo-relay/value)" = 0 ] || fail toggle-file
tool toggle-readback onoff read on-off 1 1
grep -q 'OnOff: FALSE' /tmp/last-tool.log || fail toggle-readback
rm /tmp/wemo-relay/value
/usr/bin/wemo-chip-tool onoff on 1 1 --storage-directory /tmp/controller > /tmp/last-tool.log 2>&1 && fail missing-relay-file-accepted
pass relay-write-failure-rejected
tool failure-readback onoff read on-off 1 1
grep -q 'OnOff: FALSE' /tmp/last-tool.log || fail failed-write-changed-attribute
echo 0 > /tmp/wemo-relay/value
kill "$app_pid"
wait "$app_pid" || true
start_app
tool retained-commissioning onoff on 1 1
[ "$(cat /tmp/wemo-relay/value)" = 1 ] || fail retained-control
pass full-mips-kernel-rootfs-wifi-matter-relay
cat /proc/meminfo | head -n 4
trap - 0
exit 0
