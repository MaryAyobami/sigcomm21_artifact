# Throughput/Latency Experiment (Section 7) — versioned + multi-hardware

This directory versions the scripts behind the upstream README's
[section 7](https://github.com/smartnic/sigcomm21_artifact#7-latencythroughput-benefits-table-2-in-the-submitted-paper)
(latency/throughput benefits). Upstream, these scripts only exist baked into
the CloudLab disk image for the `xl170-centos7-ubuntu20` profile — they were
never tracked in git. This directory makes them forkable/editable, applies
bug fixes found while reproducing the experiment, and adds support for
additional CPU-generation hardware types so the paper's claim
("K2-optimized code has similar-or-better throughput and lower tail
latency than the best `clang` baseline") can be tested for generalizability
across hardware.

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

4. **`bpf_cpu_to_be32` undefined — BPF program silently fails to load on
   Ubuntu 20.04 / libbpf 0.5.0.** `xdp_fwd_kern.c` uses `cpu_to_be32()` via
   the kernel's `bpf_helpers.h`. Our shim originally mapped this to
   `bpf_cpu_to_be32`, which does not exist in system libbpf headers. Clang
   for the BPF target treats undefined calls as BTF kfunc externs; libbpf
   0.5.0 then fails with `failed to find BTF for extern 'bpf_cpu_to_be32'`
   and exits — but the userspace loader swallows this and prints only the
   misleading message "Does kernel support devmap lookup?". The fix is in
   `setup_xdp_node0.sh`: `#define cpu_to_be32 bpf_htonl` (which expands to
   `__builtin_bswap32` inline). Affects any node type that compiles from
   source rather than using a pre-baked object.
5. **Missing static ARP entry for T-Rex IP.** T-Rex (DPDK) takes over the
   NIC and never responds to ARP. Without a permanent ARP entry for the
   T-Rex IP (10.10.1.2), `bpf_fib_lookup()` returns
   `BPF_FIB_LKUP_RET_NO_NEIGH` and all packets fall through to `XDP_PASS`,
   hitting the kernel slow path (~5500 µs instead of ~30 µs). Fixed in
   `setup_xdp_node0.sh` with `sudo arp -s 10.10.1.2 <trex-mac>`. The T-Rex
   NIC MAC must be read from `dmesg | grep <pci-addr>` before T-Rex starts
   (DPDK hides the NIC from the kernel once it binds). Affects all node
   types; must be re-added after each node reboot.
6. **Missing `xdp_fwd_kern4.o` placeholder.** `run_mlffr.py` hardcodes
   `versionList = ["o1","o2","k0","k1","k2","k3","k4"]` so the k4 slot must
   exist even when real K2 variants are not built. `setup_xdp_node0.sh`
   now creates k0–k4 as O2 copies. If k4.o is absent, the `cp` in
   `load_xdp.py` silently fails, the stale object from the previous variant
   is used, and k4 results are garbage.

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
- `../profile.py` — CloudLab geni-lib profile with a hardware-type
  dropdown, replacing the fixed `xl170-centos7-ubuntu20` portal profile.

## Node types

| Type | Site | Status | CPU | Year | NIC | Driver |
|---|---|---|---|---|---|---|
| `xl170` | Utah | validated — original artifact | Intel Broadwell E5-2640v4 | 2016 | ConnectX-4 Lx | mlx5 25GbE |
| `d6515` | Utah | validated — original artifact | AMD EPYC Rome 7452 | 2019 | ConnectX-5 | mlx5 100GbE |
| `c8220` | Clemson | **validated — 2026-06-29** (fixes 4–6 required) | Intel Ivy Bridge E5-2660v2 | 2013 | X520 | ixgbe 10GbE |
| `c6525-25g` | Utah | **template** — priority target, AMD/Zen2 | AMD EPYC Rome 7302P | 2019 | ConnectX-5 | mlx5 25GbE |
| `c6420` | Clemson | **template** — priority target, i40e NIC | Intel Skylake-SP Gold 6142 | 2017 | X710 | i40e 10GbE |
| `c6620` | Utah | **template** — priority target, newest Intel; needs HWE kernel | Intel Emerald Rapids 5512U | 2024 | E810-XXV | ice 25GbE |
| `c6320` | Clemson | **template** — Intel ladder (same NIC as c8220) | Intel Haswell E5-2683v3 | 2014 | X520 | ixgbe 10GbE |
| `r6525` | Clemson | **template** — AMD/Zen3 | AMD EPYC Milan 7543 | 2021 | ConnectX-5 | mlx5 25GbE |
| `sm220u` | Wisconsin | **template, unverified** | Intel Ice Lake Silver 4314 | 2021 | ConnectX-6 | mlx5 100GbE |
| `d7615` | Clemson | **template, unverified** | AMD EPYC Genoa 9354P | 2023 | ConnectX-6 Lx | mlx5 25GbE |

`xl170`/`d6515` work as-is (same configs as upstream, plus fixes 1–3).
`c8220` is now validated; run `setup_xdp_node0.sh` on node-0 (it applies
fixes 4–6 automatically). All other types are templates — they will **not**
work until you complete the checklist below, because real PCI bus IDs and
interface names can't be known without the actual hardware.

## First-boot checklist for a new node type

After allocating any template node (`c6525-25g`, `c6420`, `c6620`, `c6320`,
`r6525`, `sm220u`, `d7615`):

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

`xl170` and `d6515` paths were validated by the original artifact authors.
`c8220` was validated on 2026-06-29 (clnode060/clnode065, Clemson) — fixes
4–6 above were discovered during that run and are now applied by
`setup_xdp_node0.sh`. Results: MLFFR ≈ 4.5–4.7 Mpps, latency ≈ 30–55 µs
at XDP fast path. All other templates (`c6525-25g`, `c6420`, `c6620`,
`c6320`, `r6525`, `sm220u`, `d7615`) were written from hardware specs and
code inspection but **have not been run on real hardware**. Treat the first
instantiation as the real test and expect to iterate on the checklist.
