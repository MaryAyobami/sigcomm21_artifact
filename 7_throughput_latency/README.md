# Throughput/Latency Experiment (Section 7) — versioned + multi-hardware

This directory versions the scripts behind the upstream README's
[section 7](https://github.com/smartnic/sigcomm21_artifact#7-latencythroughput-benefits-table-2-in-the-submitted-paper)
(latency/throughput benefits). Upstream, these scripts only exist baked into
the CloudLab disk image for the `xl170-centos7-ubuntu20` profile — they were
never tracked in git. This directory makes them forkable/editable, applies
three bug fixes found while reproducing the experiment, and adds templated
support for three additional CPU-generation hardware types so the paper's
claim ("K2-optimized code has similar-or-better throughput and lower tail
latency than the best `clang` baseline") can be tested for generalizability
across hardware, not just on the two node types the authors used.

## Fixes applied (changelog)

1. **Stale T-Rex process blocking the ZMQ port.** If a previous
   `run_mlffr.py`/`run_mlffr_user.py` run was interrupted, its `t-rex-64`
   process can be left running and holds the ZMQ port. The next run then
   fails immediately with `ERROR encountered while configuring TRex system`
   / `Error while starting Trex`. Fixed by running `sudo pkill t-rex; sleep 2`
   before every launch in both scripts (`v2.87-scripts/run_mlffr.py`,
   `v2.87-scripts/run_mlffr_user.py`).
2. **Missing `PYTHONPATH`.** `mlffr.py`'s top-level `from trex_stl_lib.api
   import *` only resolves if `PYTHONPATH` includes
   `/usr/local/v2.87/automation/trex_control_plane/interactive`. The upstream
   README documents this as a manual `~/.bash_profile` edit (section 2.1) —
   easy to miss, since nothing else in setup fails loudly without it until
   you actually run `mlffr.py`. `setup.sh` now adds this line automatically
   (idempotent — safe to re-run).
3. **`generate_user_graphs.py` `FileNotFoundError`.** For the packet-drop
   benchmark (`run_mlffr_user.py` / `xdp_map_access`), `load_xdp_user.py`
   runs over SSH *on node0* and writes its per-rate result files into
   node0's home directory — not node1's. `generate_user_graphs.py` runs on
   node1 and expects those files locally, so it crashed unless you manually
   `scp`'d them over first. `run_mlffr_user.py` now does this `scp`
   automatically right before tearing down T-Rex.

None of these required changes to `mlffr.py`, `mlffr_user.py`,
`load_xdp.py`, `load_xdp_user.py`, `unload_xdp.py`, or any of the
`visualize-data-scripts/` — those are carried forward unchanged.

## Layout

- `install_trex.sh` — fresh T-Rex v2.87 install for node types without a
  pre-baked CloudLab image. Run once per node (node-0 and node-1) after
  allocation, before `setup.sh`.
- `setup.sh` — per-experiment config: copies the right `trex_cfg_*.yaml` /
  `udp_for_benchmarks_*.py`, writes `node0.config`, installs the fixed
  `run_mlffr*.py`/`mlffr*.py`, sets `PYTHONPATH`. Run on node-1.
- `v2.87-scripts/` — the scripts that get copied into `/usr/local/v2.87/`.
- `trex-configuration/` — everything that gets copied into
  `/usr/local/trex-configuration/`: `scripts/`, `scripts-user/`,
  `visualize-data-scripts/`, and the per-node-type
  `trex_cfg_*.yaml`/`udp_for_benchmarks_*.py`.
- `../profile/profile.py` — CloudLab geni-lib profile with a hardware-type
  dropdown, replacing the fixed `xl170-centos7-ubuntu20` portal profile.

## Node types

| Type | Status | CPU | Year | NIC |
|---|---|---|---|---|
| `xl170` | validated (original artifact) | Intel Broadwell-EP | 2016 | Mellanox ConnectX-4 |
| `d6515` | validated (original artifact) | AMD EPYC Rome | 2019 | Mellanox ConnectX-5 |
| `c8220` | **template, unverified** | Intel Ivy Bridge | 2013 | Intel X520 (ixgbe) |
| `sm220u` | **template, unverified** | Intel Ice Lake | ~2021 | Mellanox ConnectX-5 |
| `d7615` | **template, unverified** | AMD EPYC Genoa | 2023 | Mellanox ConnectX-6 Lx |

`xl170`/`d6515` work as-is (same configs as upstream, plus the 3 fixes).
`c8220`/`sm220u`/`d7615` are templates — they will **not** work until you
complete the checklist below, because real PCI bus IDs and interface names
can't be known without the actual hardware.

## First-boot checklist for a new node type

After allocating `c8220`, `sm220u`, or `d7615` nodes:

1. On node-1: `lspci | grep -i ethernet` (or `mellanox` for the Mellanox
   types). Edit `trex-configuration/trex_cfg_<type>.yaml`, replacing the
   `PCI_BUS_ID_PORT0`/`PORT1` placeholders with the real bus IDs.
2. Decide single-port vs. dual-port for this allocation (check how many
   usable 10G+ interfaces you actually got):
   - Dual real ports → keep the template's `udp_for_benchmarks_<type>.py`
     and `trex_cfg_<type>.yaml` as-is (different-IP pattern, matches `d6515`).
   - Single real port → switch both files to the `xl170` pattern instead
     (single real interface + `"dummy"`, same-IP).
3. On node-1: `ip link` (or check node0's NIC similarly). Edit
   `trex-configuration/scripts/<type>.config`, replacing
   `REPLACE_WITH_REAL_IFACE_PORT0`/`PORT1` with the real interface names.
4. Confirm `lscpu` core count and adjust the `threads:`/`master_thread_id`/
   `latency_thread_id` fields in `trex_cfg_<type>.yaml` if the placeholder
   thread list doesn't match (it's deliberately conservative, not tuned).
5. On node0: write `/usr/local/trex-configuration/scripts/device.config`
   containing just the node type string (e.g. `c8220`) — same manual step
   the original artifact required for `xl170`/`d6515`.
6. **Verify native XDP, not generic/skb-mode.** After loading a program
   (`load_xdp.py`), check `ip -d link show <iface>` for `xdp` (native) vs.
   `xdpgeneric`. Older NIC firmware can silently fall back to generic mode,
   which would invalidate any hardware comparison — this is the most
   important thing to confirm before trusting results from a new node type.
7. For Mellanox types (`sm220u`, `d7615`): confirm the `install_trex.sh`
   Mellanox/MLNX_OFED step actually matches your NIC generation — it's left
   as a TODO in that script because the right OFED build varies by
   ConnectX generation and wasn't verified against real hardware.

## What's still manual (same as upstream)

- Reading node-0's/node-1's actual hostnames from the CloudLab "List View"
  after the profile finishes instantiating, and running
  `./setup.sh <type> <user>@<node0-hostname>` on node-1. This can't be
  automated in `profile.py` because the peer's hostname isn't known until
  after allocation.
- Everything from upstream README sections 7.3/7.4 (running
  `run_mlffr.py`/`run_mlffr_user.py`, then `rx_plot.py`/`latency.py`/
  `generate_graphs.py`/`generate_user_graphs.py`) is unchanged except that
  the 3 bugs above are now fixed automatically.

## Honesty about what's tested vs. not

`xl170` and `d6515` paths (including the 3 fixes) were validated by actually
running the full warmup and full 3-run/7-version evaluation end-to-end on a
live `xl170` pair. `c8220`/`sm220u`/`d7615` templates and `profile.py` were
written from code inspection (`t-rex-64`, `dpdk_setup_ports.py`,
`update-scripts.sh`) and from CloudLab's published hardware specs, but
**have not been run on real hardware** — there was no way to test them
without allocating that hardware. Treat the first instantiation against each
new node type as the real test, and expect to iterate on the checklist above.
