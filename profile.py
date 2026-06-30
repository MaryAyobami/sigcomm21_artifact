# -*- coding: utf-8 -*-
"""CloudLab profile for the K2 throughput/latency experiment, parameterized
by hardware type."""

import geni.portal as portal
import geni.rspec.pg as pg

pc = portal.Context()

NODE_TYPES = [
    # ── Already benchmarked ──────────────────────────────────────────────────
    ("xl170",     "xl170     [Utah]    Intel Broadwell E5-2640v4, 2016  -- ConnectX-4 Lx mlx5  25GbE"),
    ("c8220",     "c8220     [Clemson] Intel Ivy Bridge E5-2660v2, 2013 -- X520 ixgbe          10GbE"),
    # ── Priority additions (hardware-generalization study) ───────────────────
    ("c6525-25g", "c6525-25g [Utah]    AMD EPYC Rome 7302P, 2019        -- ConnectX-5 mlx5    25GbE  ★ AMD/Zen2"),
    ("c6420",     "c6420     [Clemson] Intel Skylake-SP Gold 6142, 2017 -- X710 i40e          10GbE  ★ i40e NIC"),
    ("c6620",     "c6620     [Utah]    Intel Emerald Rapids 5512U, 2024 -- E810-XXV ice       25GbE  ★ newest; needs HWE kernel"),
    ("c6320",     "c6320     [Clemson] Intel Haswell E5-2683v3, 2014    -- X520 ixgbe         10GbE  ★ clean Intel ladder"),
    ("r6525",     "r6525     [Clemson] AMD EPYC Milan 7543, 2021        -- ConnectX-5 mlx5   25GbE  ★ AMD/Zen3"),
    # ── Other node types (pre-existing, not yet benchmarked) ─────────────────
    ("d6515",     "d6515     [Utah]    AMD EPYC Rome 7452, 2019         -- ConnectX-5 mlx5   100GbE"),
    ("sm220u",    "sm220u    [Wisc]    Intel Ice Lake Silver 4314, 2021 -- ConnectX-6 mlx5   100GbE"),
    ("d7615",     "d7615     [Clemson] AMD EPYC Genoa 9354P, 2023       -- ConnectX-6 Lx mlx5 25GbE"),
]

pc.defineParameter(
    "nodeType",
    "Hardware type",
    portal.ParameterType.STRING,
    "xl170",
    NODE_TYPES,
    longDescription="Which CloudLab hardware type to allocate for BOTH node-0 "
                     "(DUT) and node-1 (traffic generator). "
                     "Site guidance: xl170/c6525-25g/c6620/d6515 are Utah; "
                     "c8220/c6420/c6320/r6525/d7615 are Clemson; sm220u is Wisconsin. "
                     "Only xl170 uses a confirmed pre-baked image; all others use "
                     "stock Ubuntu 20.04 and install T-Rex on first boot. "
                     "c6620 EXCEPTION: the E810 ice NIC driver requires the HWE "
                     "kernel (5.15); after boot run: "
                     "sudo apt-get install -y linux-image-generic-hwe-20.04 && sudo reboot",
)

pc.defineParameter(
    "dualPort",
    "Node has two real usable NIC ports",
    portal.ParameterType.BOOLEAN,
    False,
    longDescription="",
)

REPO_URL = "https://github.com/MaryAyobami/sigcomm21_artifact.git"
REPO_BRANCH = "hardware-generalization"

params = pc.bindParameters()
request = pc.makeRequestRSpec()

XL170_IMAGES = {
    "node0": "urn:publicid:IDN+utah.cloudlab.us+image+heartbeat-PG0:xl170-centos7-ubuntu20:2",
    "node1": "urn:publicid:IDN+utah.cloudlab.us+image+heartbeat-PG0:xl170-centos7-ubuntu20.node-1:5",
}

# Stock Ubuntu 20.04 image, used as a fallback for every node type that
# doesn't have a confirmed pre-baked image (d6515, c8220, sm220u, d7615).
FALLBACK_IMAGE = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU20-64-STD"

# Idempotent boot script: installs T-Rex only if missing (so it's a no-op on
# the pre-baked xl170 image, and a real install on stock images), then always
# overwrites run_mlffr*.py/mlffr*.py with the fixed versions from this repo --
# this retrofits the 3 bug fixes even onto the old pre-baked images.
BOOT_CMD = (
    "git clone --branch {branch} {url} /tmp/sigcomm21_artifact "
    "&& REPO=/tmp/sigcomm21_artifact/7_throughput_latency "
    "&& if [ ! -d /usr/local/v2.87 ]; then bash $REPO/install_trex.sh {node_type} "
    ">> /tmp/install_trex.log 2>&1; fi "
    "&& sudo mkdir -p /usr/local/v2.87 /usr/local/trex-configuration "
    "&& sudo cp $REPO/v2.87-scripts/*.py /usr/local/v2.87/ 2>/dev/null; true"
).format(branch=REPO_BRANCH, url=REPO_URL, node_type=params.nodeType)

node0 = request.RawPC("node0")
node1 = request.RawPC("node1")

if params.nodeType == "xl170":
    node0.hardware_type = "xl170"
    node0.disk_image = XL170_IMAGES["node0"]
    node1.hardware_type = "xl170"
    node1.disk_image = XL170_IMAGES["node1"]
else:
    node0.hardware_type = params.nodeType
    node0.disk_image = FALLBACK_IMAGE
    node1.hardware_type = params.nodeType
    node1.disk_image = FALLBACK_IMAGE

node0.addService(pg.Execute(shell="bash", command=BOOT_CMD))
node1.addService(pg.Execute(shell="bash", command=BOOT_CMD))

# Link 1: always present, carries the 10.10.1.x subnet.
link1 = request.Link("link1")
iface0_1 = node0.addInterface("if1")
iface0_1.addAddress(pg.IPv4Address("10.10.1.1", "255.255.255.0"))
iface1_1 = node1.addInterface("if1")
iface1_1.addAddress(pg.IPv4Address("10.10.1.2", "255.255.255.0"))
link1.addInterface(iface0_1)
link1.addInterface(iface1_1)

# Link 2: only added if dualPort is set. d6515-style nodes need this; xl170
# does not (confirmed against the real rspec -- it has a single link).
if params.dualPort:
    link2 = request.Link("link2")
    iface0_2 = node0.addInterface("if2")
    iface0_2.addAddress(pg.IPv4Address("10.10.2.1", "255.255.255.0"))
    iface1_2 = node1.addInterface("if2")
    iface1_2.addAddress(pg.IPv4Address("10.10.2.2", "255.255.255.0"))
    link2.addInterface(iface0_2)
    link2.addInterface(iface1_2)

pc.printRequestRSpec(request)
