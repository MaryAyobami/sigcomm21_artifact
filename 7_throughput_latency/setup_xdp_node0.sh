#!/bin/bash
# Run on node-0 (DUT) to compile xdp_fwd BPF programs from Linux 5.4 source
# and populate /usr/local/throughput-experiments/ for the benchmark.
#
# Usage: ./setup_xdp_node0.sh <trex-nic-mac>
#   trex-nic-mac: MAC of the T-Rex node's experimental NIC.
#                 Required for a static ARP entry so bpf_fib_lookup can resolve
#                 the next hop. T-Rex uses DPDK and never responds to ARP, so
#                 without this the XDP program falls back to the kernel slow path.
#
#   To find the MAC before T-Rex starts (it hides the NIC from the kernel):
#     ssh <trex-node> 'dmesg | grep "82:00.0" | grep -oE "([0-9a-f]{2}:){5}[0-9a-f]{2}"'
#   or read it from the peer port (port 1 MAC is usually port 0 MAC + 1):
#     ssh <trex-node> 'ip link show enp130s0f1 | grep ether'
#
# Prerequisites (install before running this script):
#   sudo apt-get install -y clang llvm libbpf-dev libelf-dev
#
set -euo pipefail

TREX_MAC="${1:?Usage: $0 <trex-nic-mac>}"
KSRC=/tmp/linux-bpf-src
SHIM=/tmp/bpf-shim
TE=/usr/local/throughput-experiments

echo "== Setting up $TE for c8220 benchmark =="

# ── Download source files from Linux 5.4 tree ──────────────────────────────
KBASE="https://raw.githubusercontent.com/torvalds/linux/v5.4/samples/bpf"
mkdir -p "$KSRC/samples/bpf"
for f in xdp_fwd_kern.c xdp_fwd_user.c bpf_helpers.h bpf_util.h \
          trace_helpers.h trace_helpers.c; do
    [ -f "$KSRC/samples/bpf/$f" ] || \
        wget -q "${KBASE}/${f}" -O "$KSRC/samples/bpf/$f"
done
echo "== Source files present =="

# ── bpf_helpers.h shim ─────────────────────────────────────────────────────
# Replace the kernel's bpf_helpers.h with a shim that uses system libbpf.
# Key fixes:
#   - cpu_to_be32 → bpf_htonl  (NOT bpf_cpu_to_be32: that symbol doesn't exist
#     in system libbpf headers; using it produces an unresolvable BTF kfunc
#     extern that causes bpf_prog_load_xattr to fail at load time)
#   - Adds kernel type aliases (u8/u16/u32/u64, __be*/__le*, etc.)
#   - Adds sparse annotations (__force, __user, etc.)
cat > "$KSRC/samples/bpf/bpf_helpers.h" <<'SHIM'
#pragma once
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>
/* Kernel integer type aliases */
typedef __u8  u8;  typedef __u16 u16; typedef __u32 u32; typedef __u64 u64;
typedef __s8  s8;  typedef __s16 s16; typedef __s32 s32; typedef __s64 s64;
typedef __u16 __be16; typedef __u32 __be32; typedef __u64 __be64;
typedef __u16 __le16; typedef __u32 __le32; typedef __u64 __le64;
typedef __u16 __sum16; typedef __u32 __wsum;
/* Sparse annotations */
#define __force
#define __user
#define __kernel
#define __iomem
/* Address families */
#ifndef AF_INET
#define AF_INET  2
#define AF_INET6 10
#endif
/* Network byte order helpers */
#ifndef htons
#define htons bpf_htons
#define ntohs bpf_ntohs
#define htonl bpf_htonl
#define ntohl bpf_ntohl
#endif
/* bpf_htonl == cpu_to_be32 on little-endian (both inline via __builtin_bswap32).
 * Do NOT use bpf_cpu_to_be32 here — it is not defined in system libbpf headers
 * and would silently become a BTF kfunc extern, breaking program load. */
#define cpu_to_be32 bpf_htonl
SHIM

# ── uapi/linux/bpf.h redirect shim ────────────────────────────────────────
# xdp_fwd_kern.c uses '#include <uapi/linux/bpf.h>' (kernel internal path),
# but system headers live at '#include <linux/bpf.h>'.
mkdir -p "$SHIM/uapi/linux"
printf '#include <linux/bpf.h>\n' > "$SHIM/uapi/linux/bpf.h"

# ── libbpf.h redirect shim ─────────────────────────────────────────────────
# xdp_fwd_user.c uses '#include "libbpf.h"' (kernel-relative),
# but the system provides libbpf via '#include <bpf/libbpf.h>'.
printf '#include <bpf/libbpf.h>\n' > "$KSRC/samples/bpf/libbpf.h"

# ── Compile BPF kernel programs ────────────────────────────────────────────
# Include path order matters:
#   1. /usr/include      — system UAPI headers (safe, no arch-specific asm)
#   2. $SHIM             — provides uapi/linux/bpf.h redirect
#   3. $KSRC/samples/bpf — our bpf_helpers.h shim and BPF utility headers
# Do NOT use linux-headers/include: it pulls in x86 asm headers incompatible
# with the BPF target and causes clang to abort with SIGABRT.
CLANG_BPF=(
    clang -g -target bpf
    -I/usr/include
    -I"$SHIM"
    -I"$KSRC/samples/bpf"
    -D__KERNEL__
    -Wno-unused-value -Wno-pointer-sign -Wno-compare-distinct-pointer-types
    -fno-stack-protector
    -c "$KSRC/samples/bpf/xdp_fwd_kern.c"
)

sudo mkdir -p "$TE/O1" "$TE/O2"

echo "== Compiling O1 =="
"${CLANG_BPF[@]}" -O1 -o /tmp/xdp_fwd_o1.o
sudo cp /tmp/xdp_fwd_o1.o "$TE/O1/xdp_fwd_kern.o"
echo "   $(ls -lh $TE/O1/xdp_fwd_kern.o)"

echo "== Compiling O2 =="
"${CLANG_BPF[@]}" -O2 -o /tmp/xdp_fwd_o2.o
sudo cp /tmp/xdp_fwd_o2.o "$TE/O2/xdp_fwd_kern.o"
echo "   $(ls -lh $TE/O2/xdp_fwd_kern.o)"

# ── Build xdp_fwd userspace loader ─────────────────────────────────────────
echo "== Building xdp_fwd binary =="
if cc -O2 \
       -I/usr/include \
       -I"$KSRC/samples/bpf" \
       "$KSRC/samples/bpf/xdp_fwd_user.c" \
       -o /tmp/xdp_fwd_bin \
       -lbpf -lelf -lz 2>/tmp/xdp_fwd_build.log; then
    sudo cp /tmp/xdp_fwd_bin "$TE/xdp_fwd"
    echo "   $(ls -lh $TE/xdp_fwd)"
else
    echo "   BUILD FAILED:"; cat /tmp/xdp_fwd_build.log; exit 1
fi

# ── K2 placeholder variants ─────────────────────────────────────────────────
# Real K2 variants require the K2 superoptimizer (hours to build/run).
# These O2 copies let the benchmark framework complete without errors.
# run_mlffr.py's hardcoded versionList = ["o1","o2","k0","k1","k2","k3","k4"]
# so we need k0-k4 (5 files).
K2DIR="$TE/completed-programs/kernel_samples_xdp_fwd_kern_xdp_fwd_runtime_debug/top-progs"
sudo mkdir -p "$K2DIR"
for i in 0 1 2 3 4; do
    sudo cp "$TE/O2/xdp_fwd_kern.o" "$K2DIR/xdp_fwd_kern${i}.o"
done
echo "== K2 placeholders installed (copies of O2, k0-k4) =="

# ── Static ARP entry for T-Rex ─────────────────────────────────────────────
# T-Rex (DPDK) takes over the NIC and never responds to ARP, so the kernel's
# neighbor table never gets an entry for 10.10.1.2. Without it, bpf_fib_lookup
# returns BPF_FIB_LKUP_RET_NO_NEIGH and all packets hit the kernel slow path
# (5000+ µs latency instead of ~30 µs).
sudo arp -s 10.10.1.2 "$TREX_MAC"
echo "== Static ARP: 10.10.1.2 → $TREX_MAC =="
echo "   NOTE: This entry does not persist across reboots."
echo "   To make it permanent, add to /etc/rc.local or a @reboot cron:"
echo "   arp -s 10.10.1.2 $TREX_MAC"

echo "== Final layout =="
find "$TE" -type f | sort
echo "== Done =="
