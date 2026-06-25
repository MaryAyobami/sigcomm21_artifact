#!/bin/bash
# Run on node-1 (the traffic generator) after install_trex.sh has installed
# T-Rex on both node-0 and node-1.
#
# Generalizes the original manual steps from the artifact's README section
# 7.2 (the ~/.bash_profile PYTHONPATH edit, plus what update-scripts.sh did
# by hand): copy the right per-node-type config files into place, write
# node0.config, and copy the (fixed) mlffr/run_mlffr scripts into v2.87/.
#
# Usage: ./setup.sh <node-type> <dut-user@dut-host>
#   node-type: one of xl170, d6515, c8220, sm220u, d7615
#   dut-user@dut-host: SSH-reachable address of node-0

set -euo pipefail

NODE_TYPE="${1:?Usage: $0 <node-type> <dut-user@dut-host>}"
DUT="${2:?Usage: $0 <node-type> <dut-user@dut-host>}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TC="$REPO_DIR/trex-configuration"
V287_LIVE=/usr/local/v2.87

valid_types=(xl170 d6515 c8220 sm220u d7615)
if [[ ! " ${valid_types[*]} " =~ " ${NODE_TYPE} " ]]; then
    echo "Unknown node type '$NODE_TYPE'. Valid: ${valid_types[*]}" >&2
    exit 1
fi

if [[ ! -f "$TC/trex_cfg_${NODE_TYPE}.yaml" ]]; then
    echo "Missing $TC/trex_cfg_${NODE_TYPE}.yaml" >&2
    exit 1
fi

echo "== Installing trex_cfg for $NODE_TYPE =="
sudo cp "$TC/trex_cfg_${NODE_TYPE}.yaml" /etc/trex_cfg.yaml

echo "== Installing udp_for_benchmarks for $NODE_TYPE =="
sudo cp "$TC/udp_for_benchmarks_${NODE_TYPE}.py" "$V287_LIVE/stl/udp_for_benchmarks.py"

echo "== Writing node0.config =="
echo "$DUT" | sudo tee "$V287_LIVE/node0.config" > /dev/null

echo "== Installing run_mlffr/mlffr scripts (with fixes) into $V287_LIVE =="
sudo cp "$REPO_DIR/v2.87-scripts/mlffr.py" "$V287_LIVE/"
sudo cp "$REPO_DIR/v2.87-scripts/run_mlffr.py" "$V287_LIVE/"
sudo cp "$REPO_DIR/v2.87-scripts/mlffr_user.py" "$V287_LIVE/"
sudo cp "$REPO_DIR/v2.87-scripts/run_mlffr_user.py" "$V287_LIVE/"

# Fix #2: README section 2.1 requires this PYTHONPATH for mlffr.py's
# top-level `from trex_stl_lib.api import *` to resolve. It's easy to
# follow the rest of setup and miss this one manual step (we did, on the
# first reproduction attempt) — so make it automatic and idempotent here.
PYTHONPATH_LINE='export PYTHONPATH=/usr/local/v2.87/automation/trex_control_plane/interactive'
if ! grep -qxF "$PYTHONPATH_LINE" ~/.bash_profile 2>/dev/null; then
    echo "== Adding PYTHONPATH to ~/.bash_profile =="
    echo "$PYTHONPATH_LINE" >> ~/.bash_profile
else
    echo "== PYTHONPATH already set in ~/.bash_profile, skipping =="
fi

echo "== Done. Run 'source ~/.bash_profile' (or start a new shell) before using mlffr.py =="
