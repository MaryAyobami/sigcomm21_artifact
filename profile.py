# -*- coding: utf-8 -*-
"""
K2 Reproduction Profile
"""
import geni.portal as portal
import geni.rspec.pg as pg

pc = portal.Context()

NODE_TYPES = [
    ("xl170",     "xl170     [Utah]    Intel Broadwell E5-2640v4 2016  ConnectX-4 Lx mlx5 25GbE "),
    ("c8220",     "c8220     [Clemson] Intel Ivy Bridge E5-2660v2 2013 X520 ixgbe 10GbE "),
    ("c6525-25g", "c6525-25g [Utah]    AMD EPYC Rome 7302P 2019        ConnectX-5 mlx5 25GbE"),
    ("c6420",     "c6420     [Clemson] Intel Skylake-SP Gold 6142 2017 X710 i40e 10GbE"),
    ("c6620",     "c6620     [Utah]    Intel Emerald Rapids 5512U 2024  E810-XXV ice 25GbE "),
    ("c6320",     "c6320     [Clemson] Intel Haswell E5-2683v3 2014     X520 ixgbe 10GbE"),
    ("r6525",     "r6525     [Clemson] AMD EPYC Milan 7543 2021         ConnectX-5 mlx5 25GbE"),
    ("d6515",     "d6515     [Utah]    AMD EPYC Rome 7452 2019          ConnectX-5 mlx5 100GbE "),
    ("sm220u",    "sm220u    [Wisc]    Intel Ice Lake Silver 4314 2021  ConnectX-6 mlx5 100GbE"),
    ("d7615",     "d7615     [Clemson] AMD EPYC Genoa 9354P 2023        ConnectX-6 Lx mlx5 25GbE"),
]

pc.defineParameter(
    "nodeType",
    "Hardware type",
    portal.ParameterType.STRING,
    "xl170",
    NODE_TYPES,
    longDescription="Hardware type for both nodes. "
                    "Utah: xl170, c6525-25g, c6620, d6515. "
                    "Clemson: c8220, c6420, c6320, r6525, d7615. "
                    "Wisconsin: sm220u. "
                    "xl170/d6515 use pre-baked images; all others install T-Rex on first boot. "
                    "c6620 requires HWE kernel after boot: "
                    "sudo apt-get install -y linux-image-generic-hwe-20.04 && sudo reboot",
)

pc.defineParameter(
    "dualPort",
    "Two usable NIC ports",
    portal.ParameterType.BOOLEAN,
    False,
)

REPO_URL = "https://github.com/MaryAyobami/sigcomm21_artifact.git"
REPO_BRANCH = "hardware-generalization"

params = pc.bindParameters()
request = pc.makeRequestRSpec()

XL170_IMAGES = {
    "node0": "urn:publicid:IDN+utah.cloudlab.us+image+heartbeat-PG0:xl170-centos7-ubuntu20:2",
    "node1": "urn:publicid:IDN+utah.cloudlab.us+image+heartbeat-PG0:xl170-centos7-ubuntu20.node-1:5",
}

FALLBACK_IMAGE = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU20-64-STD"

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

link1 = request.Link("link1")
iface0_1 = node0.addInterface("if1")
iface0_1.addAddress(pg.IPv4Address("10.10.1.1", "255.255.255.0"))
iface1_1 = node1.addInterface("if1")
iface1_1.addAddress(pg.IPv4Address("10.10.1.2", "255.255.255.0"))
link1.addInterface(iface0_1)
link1.addInterface(iface1_1)

if params.dualPort:
    link2 = request.Link("link2")
    iface0_2 = node0.addInterface("if2")
    iface0_2.addAddress(pg.IPv4Address("10.10.2.1", "255.255.255.0"))
    iface1_2 = node1.addInterface("if2")
    iface1_2.addAddress(pg.IPv4Address("10.10.2.2", "255.255.255.0"))
    link2.addInterface(iface0_2)
    link2.addInterface(iface1_2)

pc.printRequestRSpec(request)
