#!/bin/sh
# Collection only: never launch or signal Spectre. Paths are exact bound args.
set -eu
root=$1
control=$2
case "$root" in
  /tmp/virtuoso_bridge_chenzc_intern25/90590/virtuoso_bridge_spectre/cf76d807) ;;
  *) exit 91 ;;
esac
test "$control" = "$root/recovery_v1"
mkdir "$control/lock" || exit 92
trap 'rc=$?; if test "$rc" -ne 0; then printf "%s\n" "$rc" > "$control/failed"; fi' 0
printf '%s\n' "$$" > "$control/lock/pid"
if ps -u chenzc_intern25 -ww -o comm,args | awk -v deck="$root/b_dynamic_512.scs" '
  $1=="spectre" && index($0,deck) {found=1} END {exit !found}'; then exit 93; fi
grep -q '^spectre completes with 0 errors' "$root/spectre.out"
raw="$root/b_dynamic_512.raw/tran_b_sine.tran.tran"
packed="$control/full.tran.tran.gz"
test ! -e "$packed" && test ! -e "$packed.part"
before=$(stat -c '%s:%Y' "$raw")
sleep 2
test "$before" = "$(stat -c '%s:%Y' "$raw")"
gzip -1 -c -- "$raw" > "$packed.part"
test "$before" = "$(stat -c '%s:%Y' "$raw")"
mv -- "$packed.part" "$packed"
sha256sum "$raw" "$packed" > "$control/hashes.pending"
stat -c '%s' "$raw" > "$control/raw_bytes"
stat -c '%s' "$packed" > "$control/gzip_bytes"
mv -- "$control/hashes.pending" "$control/hashes"
printf '0\n' > "$control/done.pending"
mv -- "$control/done.pending" "$control/done"
