"""CloudLab profile for the K2 throughput/latency experiment, parameterized
by hardware type so the same profile can be instantiated against any of the
node types this repo has configs for (see ../7_throughput_latency/).

NOT YET VALIDATED end-to-end on CloudLab for the new node types — there is
no API access available from the environment this was written in to
instantiate or test a profile. The xl170 path below uses the *exact* disk
image URNs from a real working `xl170-centos7-ubuntu20` instance's request
rspec (confirmed by the user), so that path should be reliable. Everything
else (d6515 and the new c8220/sm220u/d7615 templates) falls back to a stock
Ubuntu image + install_trex.sh and has not been tested against real
hardware.

Topology: node-0 is the device-under-test (DUT, runs the XDP programs),
node-1 is the traffic generator (runs T-Rex). The real xl170 rspec we
checked this against has exactly ONE link between them (xl170 only exposes
one real NIC port for this experiment; trex_cfg_xl170.yaml's "dummy" second
interface is a placeholder, not a second physical link). Set the `dualPort`
parameter to add a second link, for node types confirmed (via the
first-boot checklist in 7_throughput_latency/README.md) to have two real
usable ports, the way d6515 does.

What this profile automates vs. what's still a manual step:
  - Automated: node allocation with the selected hardware type/image,
    network topology, and a boot-time script that installs T-Rex if it's
    not already on the image, and always overwrites run_mlffr*.py/
    mlffr*.py with our fixed versions (so even the pre-baked xl170/d6515
    images get the 3 bug fixes applied automatically).
  - Still manual (same constraint the original artifact had): once both
    nodes are "ready", SSH into node-1 and run
        cd /tmp/sigcomm21_artifact/7_throughput_latency
        ./setup.sh <nodeType> <your-username>@<node-0's-hostname>
    The node-0 hostname is only knowable after instantiation (CloudLab
    "List View"), so it can't be baked into the boot script.
"""

import geni.portal as portal
import geni.rspec.pg as pg

pc = portal.Context()

NODE_TYPES = [
    ("xl170", "xl170 -- Intel Broadwell-EP, 2016 (Mellanox ConnectX-4) [validated]"),
    ("d6515", "d6515 -- AMD EPYC Rome, 2019 (Mellanox ConnectX-5) [template, unverified image]"),
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
                     "(DUT) and node-1 (traffic generator). Only xl170 uses a "
                     "confirmed-working pre-baked image; everything else "
                     "installs T-Rex fresh on a stock Ubuntu image and is "
                     "unverified (see 7_throughput_latency/README.md).",
)

pc.defineParameter(
    "dualPort",
    "Node has two real usable NIC ports",
    portal.ParameterType.BOOLEAN,
    False,
    longDescription="Leave off (single link) unless you've confirmed via the "
                     "first-boot checklist that this allocation has two real "
                     "ports, like d6515 does. xl170 is confirmed single-port.",
)

REPO_URL = "https://github.com/MaryAyobami/sigcomm21_artifact.git"
REPO_BRANCH = "hardware-generalization"

params = pc.bindParameters()
request = pc.makeRequestRSpec()

# Confirmed from a real working xl170-centos7-ubuntu20 request rspec.
# node-0 (DUT) and node-1 (traffic generator) use two DIFFERENT pre-baked
# images, both built specifically for xl170 hardware (project heartbeat-PG0).
XL170_IMAGES = {
    "node0": "urn:publicid:IDN+utah.cloudlab.us+image+heartbeat-PG0:xl170-centos7-ubuntu20:2",
    "node1": "urn:publicid:IDN+utah.cloudlab.us+image+heartbeat-PG0:xl170-centos7-ubuntu20.node-1:5",
}

# Stock Ubuntu 20.04 image, used as a fallback for every node type that
# doesn't have a confirmed pre-baked image (d6515, c8220, sm220u, d7615).
# Unlike the xl170 images above, this is NOT confirmed to work for every
# hardware type/cluster combination -- verify it resolves before relying on it.
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
