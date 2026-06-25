"""CloudLab profile for the K2 throughput/latency experiment, parameterized
by hardware type so the same profile can be instantiated against any of the
node types this repo has configs for (see ../7_throughput_latency/).

NOT YET VALIDATED end-to-end on CloudLab — there is no API access available
to instantiate or test a profile from this environment. This was written
from the standard geni-lib/ProtoGENI patterns used by other CloudLab
profiles, but treat the first real instantiation as the actual test.

Topology mirrors the original artifact: node-0 is the device-under-test
(DUT, runs the XDP programs), node-1 is the traffic generator (runs T-Rex).
They're connected by two point-to-point links carrying the 10.10.1.x and
10.10.2.x subnets the trex_cfg_*.yaml / udp_for_benchmarks_*.py files
already assume.

What this profile automates vs. what's still a manual step:
  - Automated: node allocation with the selected hardware type, OS image,
    network topology, and running install_trex.sh on both nodes at boot.
  - Still manual (same as the original artifact's README): once both nodes
    are "ready", SSH into node-1 and run
        ./setup.sh <nodeType> <your-username>@<node-0's-hostname>
    The node-0 hostname is only knowable after instantiation (CloudLab
    "List View"), so it can't be baked into the startup script.
"""

import geni.portal as portal
import geni.rspec.pg as pg

pc = portal.Context()

NODE_TYPES = [
    ("xl170", "xl170 -- Intel Broadwell-EP, 2016 (Mellanox ConnectX-4)"),
    ("d6515", "d6515 -- AMD EPYC Rome, 2019 (Mellanox ConnectX-5)"),
    ("c8220", "c8220 -- Intel Ivy Bridge, 2013 (Intel X520/ixgbe) [template, unverified]"),
    ("sm220u", "sm220u -- Intel Ice Lake, ~2021 (Mellanox ConnectX-5) [template, unverified]"),
    ("d7615", "d7615 -- AMD EPYC Genoa, 2023 (Mellanox ConnectX-6 Lx) [template, unverified]"),
]

pc.defineParameter(
    "nodeType",
    "Hardware type",
    portal.ParameterType.STRING,
    "xl170",
    NODE_TYPES,
    longDescription="Which CloudLab hardware type to allocate for BOTH node-0 "
                     "(DUT) and node-1 (traffic generator). xl170/d6515 have "
                     "pre-validated configs; the others are unverified "
                     "templates (see 7_throughput_latency/README.md).",
)

# Generic install_trex.sh repo path on this profile's own source repo. Update
# REPO_URL/REPO_BRANCH if you fork this again.
REPO_URL = "https://github.com/MaryAyobami/sigcomm21_artifact.git"
REPO_BRANCH = "hardware-generalization"

params = pc.bindParameters()
request = pc.makeRequestRSpec()

# Stock Ubuntu 20.04 image. This URN is the common emulab-ops image mirrored
# across CloudLab clusters; verify it resolves on whichever cluster actually
# hosts the chosen hardware type before relying on it.
UBUNTU_IMAGE = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU20-64-STD"

BOOT_CMD = (
    "git clone --branch {branch} {url} /tmp/sigcomm21_artifact "
    "&& bash /tmp/sigcomm21_artifact/7_throughput_latency/install_trex.sh {node_type} "
    "> /tmp/install_trex.log 2>&1"
).format(branch=REPO_BRANCH, url=REPO_URL, node_type=params.nodeType)

node0 = request.RawPC("node0")
node0.hardware_type = params.nodeType
node0.disk_image = UBUNTU_IMAGE
node0.addService(pg.Execute(shell="bash", command=BOOT_CMD))

node1 = request.RawPC("node1")
node1.hardware_type = params.nodeType
node1.disk_image = UBUNTU_IMAGE
node1.addService(pg.Execute(shell="bash", command=BOOT_CMD))

# Two point-to-point links between node0 and node1, matching the
# 10.10.1.x / 10.10.2.x subnets the existing trex_cfg_*.yaml and
# udp_for_benchmarks_*.py files assume. If the allocated hardware turns out
# to only expose one usable port (see the per-node-type yaml TODOs), drop
# link2 and switch the configs to the xl170 single-port pattern instead.

link1 = request.Link("link1")
iface0_1 = node0.addInterface("if1")
iface0_1.addAddress(pg.IPv4Address("10.10.1.1", "255.255.255.0"))
iface1_1 = node1.addInterface("if1")
iface1_1.addAddress(pg.IPv4Address("10.10.1.2", "255.255.255.0"))
link1.addInterface(iface0_1)
link1.addInterface(iface1_1)

link2 = request.Link("link2")
iface0_2 = node0.addInterface("if2")
iface0_2.addAddress(pg.IPv4Address("10.10.2.1", "255.255.255.0"))
iface1_2 = node1.addInterface("if2")
iface1_2.addAddress(pg.IPv4Address("10.10.2.2", "255.255.255.0"))
link2.addInterface(iface0_2)
link2.addInterface(iface1_2)

pc.printRequestRSpec(request)
