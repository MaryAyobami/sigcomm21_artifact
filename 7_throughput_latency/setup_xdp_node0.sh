#!/bin/bash
# Run on node-0 (DUT) to compile xdp_fwd BPF programs and set up
# /usr/local/throughput-experiments/ for the benchmark.
#
# Usage: ./setup_xdp_node0.sh <trex-nic-mac>
#
# Find the T-Rex MAC before T-Rex starts (DPDK hides the NIC after binding):
#   ssh <trex-node> 'dmesg | grep <pci-addr> | grep -oE "([0-9a-f]{2}:){5}[0-9a-f]{2}"'
# or from the sibling port (usually MAC+1):
#   ssh <trex-node> 'ip link show enp130s0f1 | grep ether'
#
# Prerequisites: sudo apt-get install -y clang llvm libbpf-dev libelf-dev
set -euo pipefail

TREX_MAC="${1:?Usage: $0 <trex-nic-mac>}"
KSRC=/tmp/linux-bpf-src
SHIM=/tmp/bpf-shim
TE=/usr/local/throughput-experiments

KBASE="https://raw.githubusercontent.com/torvalds/linux/v5.4/samples/bpf"
mkdir -p "$KSRC/samples/bpf"
for f in xdp_fwd_kern.c xdp_fwd_user.c bpf_helpers.h bpf_util.h \
          trace_helpers.h trace_helpers.c; do
    [ -f "$KSRC/samples/bpf/$f" ] || wget -q "${KBASE}/${f}" -O "$KSRC/samples/bpf/$f"
done

# bpf_helpers.h shim: bridges kernel source to system libbpf.
# cpu_to_be32 maps to bpf_htonl, NOT bpf_cpu_to_be32 — the latter doesn't
# exist in system libbpf 0.5.0 and becomes an unresolvable BTF kfunc extern
# that silently prevents the XDP program from loading.
cat > "$KSRC/samples/bpf/bpf_helpers.h" <<'SHIM'
#pragma once
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>
typedef __u8  u8;  typedef __u16 u16; typedef __u32 u32; typedef __u64 u64;
typedef __s8  s8;  typedef __s16 s16; typedef __s32 s32; typedef __s64 s64;
typedef __u16 __be16; typedef __u32 __be32; typedef __u64 __be64;
typedef __u16 __le16; typedef __u32 __le32; typedef __u64 __le64;
typedef __u16 __sum16; typedef __u32 __wsum;
#define __force
#define __user
#define __kernel
#define __iomem
#ifndef AF_INET
#define AF_INET  2
#define AF_INET6 10
#endif
#ifndef htons
#define htons bpf_htons
#define ntohs bpf_ntohs
#define htonl bpf_htonl
#define ntohl bpf_ntohl
#endif
#define cpu_to_be32 bpf_htonl
SHIM

# xdp_fwd_kern.c uses <uapi/linux/bpf.h> (kernel path); redirect to system path.
mkdir -p "$SHIM/uapi/linux"
printf '#include <linux/bpf.h>\n' > "$SHIM/uapi/linux/bpf.h"

# xdp_fwd_user.c uses "libbpf.h" (kernel-relative); redirect to system path.
printf '#include <bpf/libbpf.h>\n' > "$KSRC/samples/bpf/libbpf.h"

# Include order: /usr/include first, then the uapi shim, then the BPF sources.
# Do NOT add linux-headers/include — x86 asm headers cause clang to SIGABRT on BPF target.
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
"${CLANG_BPF[@]}" -O1 -o /tmp/xdp_fwd_o1.o && sudo cp /tmp/xdp_fwd_o1.o "$TE/O1/xdp_fwd_kern.o"
"${CLANG_BPF[@]}" -O2 -o /tmp/xdp_fwd_o2.o && sudo cp /tmp/xdp_fwd_o2.o "$TE/O2/xdp_fwd_kern.o"

if cc -O2 -I/usr/include -I"$KSRC/samples/bpf" \
       "$KSRC/samples/bpf/xdp_fwd_user.c" -o /tmp/xdp_fwd_bin \
       -lbpf -lelf -lz 2>/tmp/xdp_fwd_build.log; then
    sudo cp /tmp/xdp_fwd_bin "$TE/xdp_fwd"
else
    cat /tmp/xdp_fwd_build.log; exit 1
fi

# k0-k4 are O2 placeholders; run_mlffr.py hardcodes versionList including k4.
K2DIR="$TE/completed-programs/kernel_samples_xdp_fwd_kern_xdp_fwd_runtime_debug/top-progs"
sudo mkdir -p "$K2DIR"
for i in 0 1 2 3 4; do
    sudo cp "$TE/O2/xdp_fwd_kern.o" "$K2DIR/xdp_fwd_kern${i}.o"
done

# T-Rex (DPDK) never responds to ARP, so bpf_fib_lookup returns NO_NEIGH
# and all packets fall to the kernel slow path without this static entry.
# Re-add after each reboot.
sudo arp -s 10.10.1.2 "$TREX_MAC"
echo "static ARP: 10.10.1.2 -> $TREX_MAC (re-add after reboot)"

find "$TE" -type f | sort
