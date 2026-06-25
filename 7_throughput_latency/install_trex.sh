#!/bin/bash
# Fresh T-Rex v2.87 install, for node types that don't have a pre-baked
# CloudLab disk image (anything other than xl170/d6515). Run on both
# node-0 and node-1.
#
# Usage: ./install_trex.sh <node-type>
#   node-type: one of xl170, d6515, c8220, sm220u, d7615
#
# NOT YET VALIDATED end-to-end on c8220/sm220u/d7615 hardware — there is
# no way to test this without allocating that hardware. xl170/d6515 already
# have working pre-baked images and don't need this script at all; it's
# provided for new node types and should be treated as a starting point,
# not a guaranteed-working install.

set -euo pipefail

NODE_TYPE="${1:?Usage: $0 <node-type>}"
TREX_VERSION="2.87"
TREX_URL="https://trex-tgn.cisco.com/trex/release/v${TREX_VERSION}.tar.gz"

mellanox_types=(xl170 d6515 sm220u d7615)
is_mellanox=false
for t in "${mellanox_types[@]}"; do
    [[ "$NODE_TYPE" == "$t" ]] && is_mellanox=true
done

echo "== Installing OS build dependencies =="
sudo apt-get update -y
sudo apt-get install -y build-essential python3 python3-pip wget tar pkg-config \
    linux-headers-"$(uname -r)" dkms

if $is_mellanox; then
    echo "== Node type '$NODE_TYPE' uses a Mellanox NIC: installing MLNX_OFED =="
    echo "   (NOT validated on this node type — confirm the OFED version matches"
    echo "    the NIC generation; xl170/d6515 used MLNX_OFED_LINUX-5.0-2.1.8.0.)"
    # Placeholder — fetch and run the appropriate MLNX_OFED installer for the
    # detected distro/kernel. Left as a manual step for new node types since
    # the right OFED build varies by NIC generation (ConnectX-4 vs -5 vs -6)
    # and we have not been able to confirm the exact version on real hardware.
    echo "   TODO: download/install MLNX_OFED for this NIC generation before continuing."
else
    echo "== Node type '$NODE_TYPE' uses an Intel NIC (ixgbe/i40e): no OFED needed =="
    echo "   ixgbe/i40e are in-kernel drivers with native DPDK PMD support."
fi

if [[ ! -d /usr/local/v2.87 ]]; then
    echo "== Downloading T-Rex v${TREX_VERSION} =="
    cd /tmp
    wget --no-check-certificate -O "v${TREX_VERSION}.tar.gz" "$TREX_URL"
    sudo mkdir -p /usr/local
    sudo tar -xzf "v${TREX_VERSION}.tar.gz" -C /usr/local
else
    echo "== /usr/local/v2.87 already present, skipping download =="
fi

echo "== Done. Next: run setup.sh $NODE_TYPE <dut-user@dut-host> on node-1, =="
echo "==   and confirm native (not generic/skb) XDP mode is available for this NIC. =="
