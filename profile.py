# -*- coding: utf-8 -*-
"""CloudLab profile for the K2 throughput/latency experiment, parameterized
by hardware type."""

import geni.portal as portal
import geni.rspec.pg as pg

pc = portal.Context()

NODE_TYPES = [
    ("xl170", "xl170 -- Intel Broadwell-EP, 2016 (Mellanox ConnectX-4)"),
    ("d6515", "d6515 -- AMD EPYC Rome, 2019 (Mellanox ConnectX-5)"),
    ("c8220", "c8220 -- Intel Ivy Bridge, 2013 (Intel X520/ixgbe)"),
    ("sm220u", "sm220u -- Intel Ice Lake, ~2021 (Mellanox ConnectX-5)"),
    ("d7615", "d7615 -- AMD EPYC Genoa, 2023 (Mellanox ConnectX-6 Lx)"),
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
                     "installs T-Rex fresh on a stock Ubuntu image.",
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
