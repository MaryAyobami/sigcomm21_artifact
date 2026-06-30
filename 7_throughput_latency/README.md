# Section 7: Throughput/Latency

Scripts for the latency/throughput benchmark (paper section 7). Upstream these
live only in a baked CloudLab image; this directory tracks them in git, applies
bug fixes, and adds support for additional hardware types.

## Files

- `install_trex.sh` — install T-Rex v2.87 on a stock Ubuntu image. Run on both nodes before `setup.sh`.
- `setup.sh` — copy per-node-type configs, install fixed scripts, set PYTHONPATH. Run on node-1.
- `setup_xdp_node0.sh` — compile xdp_fwd from source and set up `/usr/local/throughput-experiments/`. Run on node-0.
- `trex-configuration/` — per-node-type T-Rex configs (`trex_cfg_*.yaml`, `udp_for_benchmarks_*.py`) and scripts.
- `v2.87-scripts/` — fixed versions of `run_mlffr.py`, `mlffr.py`, and user-mode variants.
- `../profile.py` — CloudLab geni-lib profile with hardware-type selector.

## Bug fixes

1. Stale `t-rex-64` process holds ZMQ port after an interrupted run. Fixed: `run_mlffr.py` kills any existing process before starting.
2. Missing `PYTHONPATH` for `trex_stl_lib`. Fixed: `setup.sh` adds it to `~/.bash_profile`.
3. `generate_user_graphs.py` crashes because result files land on node-0, not node-1. Fixed: `run_mlffr_user.py` scp's them over before graphing.
4. `bpf_cpu_to_be32` is undefined in system libbpf 0.5.0, causing the XDP program to silently fail to load. Fixed: `setup_xdp_node0.sh` maps `cpu_to_be32` to `bpf_htonl` in the helpers shim.
5. T-Rex (DPDK) never responds to ARP, so `bpf_fib_lookup` falls to the kernel slow path. Fixed: `setup_xdp_node0.sh` adds a static ARP entry for the T-Rex IP.
6. `run_mlffr.py` expects `xdp_fwd_kern4.o` but only k0–k3 were created. Fixed: `setup_xdp_node0.sh` creates k0–k4.

## Node types

| Type | Site | CPU | Year | NIC | Status |
|---|---|---|---|---|---|
| xl170 | Utah | Intel Broadwell E5-2640v4 | 2016 | ConnectX-4 Lx mlx5 25GbE | validated (original) |
| d6515 | Utah | AMD EPYC Rome 7452 | 2019 | ConnectX-5 mlx5 100GbE | validated (original) |
| c8220 | Clemson | Intel Ivy Bridge E5-2660v2 | 2013 | X520 ixgbe 10GbE | validated 2026-06-29, fixes 4-6 required |
| c6525-25g | Utah | AMD EPYC Rome 7302P | 2019 | ConnectX-5 mlx5 25GbE | template |
| c6420 | Clemson | Intel Skylake-SP Gold 6142 | 2017 | X710 i40e 10GbE | template |
| c6620 | Utah | Intel Emerald Rapids 5512U | 2024 | E810-XXV ice 25GbE | template (needs HWE kernel) |
| c6320 | Clemson | Intel Haswell E5-2683v3 | 2014 | X520 ixgbe 10GbE | template |
| r6525 | Clemson | AMD EPYC Milan 7543 | 2021 | ConnectX-5 mlx5 25GbE | template |
| sm220u | Wisconsin | Intel Ice Lake Silver 4314 | 2021 | ConnectX-6 mlx5 100GbE | template |
| d7615 | Clemson | AMD EPYC Genoa 9354P | 2023 | ConnectX-6 Lx mlx5 25GbE | template |

## Adding a new node type

1. `lspci | grep -i ethernet` on node-1. Fill in the PCI bus IDs in `trex-configuration/trex_cfg_<type>.yaml`.
2. `ip link` on both nodes. Fill in interface names in `trex-configuration/scripts/<type>.config`.
3. Check whether you have one or two usable 10G+ ports. Single port: use the xl170 pattern (one real iface + `"dummy"`). Dual port: use the d6515 pattern.
4. `lscpu` — adjust `threads`, `master_thread_id`, `latency_thread_id` in the yaml to match actual core layout.
5. After loading XDP: `ip -d link show <iface>` should show `xdp` not `xdpgeneric`. Generic mode invalidates any performance comparison.
6. Mellanox NICs: install MLNX_OFED matching the NIC generation before running T-Rex.
