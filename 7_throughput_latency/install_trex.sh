#!/bin/bash
# Install T-Rex v2.87 on node types without a pre-baked CloudLab image.
# Run on both node-0 and node-1.
#
# Usage: ./install_trex.sh <node-type>
set -euo pipefail

NODE_TYPE="${1:?Usage: $0 <node-type>}"
TREX_VERSION="2.87"
TREX_URL="https://trex-tgn.cisco.com/trex/release/v${TREX_VERSION}.tar.gz"

sudo apt-get update -y
sudo apt-get install -y build-essential python3 python3-pip wget tar pkg-config \
    linux-headers-"$(uname -r)" dkms
sudo pip3 install numpy pandas

case "$NODE_TYPE" in
    xl170|d6515|sm220u|d7615|c6525-25g|r6525)
        # Mellanox NIC — MLNX_OFED needed for DPDK PMD.
        # xl170/d6515 use pre-baked images and skip this script entirely.
        # For new Mellanox types: download and install MLNX_OFED matching your
        # NIC generation (ConnectX-4/5/6) before continuing.
        echo "Mellanox NIC detected. Install MLNX_OFED for $NODE_TYPE before running setup.sh."
        ;;
    *)
        # Intel NIC (ixgbe/i40e/ice) — in-kernel drivers, no OFED needed.
        ;;
esac

if [[ ! -d /usr/local/v2.87 ]]; then
    cd /tmp
    wget --no-check-certificate -O "v${TREX_VERSION}.tar.gz" "$TREX_URL"
    sudo mkdir -p /usr/local
    sudo tar -xzf "v${TREX_VERSION}.tar.gz" -C /usr/local
fi
