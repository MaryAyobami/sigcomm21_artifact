#!/bin/bash
# Run on node-1 after install_trex.sh has run on both nodes.
# Copies per-node-type configs, installs fixed mlffr scripts, sets PYTHONPATH.
#
# Usage: ./setup.sh <node-type> <dut-user@dut-host>
set -euo pipefail

NODE_TYPE="${1:?Usage: $0 <node-type> <dut-user@dut-host>}"
DUT="${2:?Usage: $0 <node-type> <dut-user@dut-host>}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TC="$REPO_DIR/trex-configuration"
V287_LIVE=/usr/local/v2.87
TC_LIVE=/usr/local/trex-configuration

if [[ ! -f "$TC/trex_cfg_${NODE_TYPE}.yaml" ]]; then
    echo "Missing $TC/trex_cfg_${NODE_TYPE}.yaml — fill in PCI bus IDs for this node type first." >&2
    exit 1
fi

sudo cp "$TC/trex_cfg_${NODE_TYPE}.yaml" /etc/trex_cfg.yaml
sudo cp "$TC/udp_for_benchmarks_${NODE_TYPE}.py" "$V287_LIVE/stl/udp_for_benchmarks.py"
echo "$DUT" | sudo tee "$V287_LIVE/node0.config" > /dev/null

sudo cp "$REPO_DIR/v2.87-scripts/mlffr.py"          "$V287_LIVE/"
sudo cp "$REPO_DIR/v2.87-scripts/run_mlffr.py"      "$V287_LIVE/"
sudo cp "$REPO_DIR/v2.87-scripts/mlffr_user.py"     "$V287_LIVE/"
sudo cp "$REPO_DIR/v2.87-scripts/run_mlffr_user.py" "$V287_LIVE/"

sudo mkdir -p "$TC_LIVE/scripts" "$TC_LIVE/scripts-user" "$TC_LIVE/visualize-data-scripts"
sudo cp -r "$TC/scripts/."                "$TC_LIVE/scripts/"
sudo cp -r "$TC/scripts-user/."          "$TC_LIVE/scripts-user/"
sudo cp -r "$TC/visualize-data-scripts/." "$TC_LIVE/visualize-data-scripts/"
echo "$NODE_TYPE" | sudo tee "$TC_LIVE/scripts/device.config" > /dev/null

ssh "$DUT" "sudo mkdir -p $TC_LIVE/scripts $TC_LIVE/scripts-user"
tar -czf - -C "$TC" scripts scripts-user \
    | ssh "$DUT" "cd /tmp && tar -xzf - \
        && sudo cp -r /tmp/scripts/.      $TC_LIVE/scripts/ \
        && sudo cp -r /tmp/scripts-user/. $TC_LIVE/scripts-user/ \
        && rm -rf /tmp/scripts /tmp/scripts-user"
ssh "$DUT" "echo '$NODE_TYPE' | sudo tee $TC_LIVE/scripts/device.config > /dev/null"

PYTHONPATH_LINE='export PYTHONPATH=/usr/local/v2.87/automation/trex_control_plane/interactive'
grep -qxF "$PYTHONPATH_LINE" ~/.bash_profile 2>/dev/null \
    || echo "$PYTHONPATH_LINE" >> ~/.bash_profile

echo "done — run 'source ~/.bash_profile' before using mlffr.py"
