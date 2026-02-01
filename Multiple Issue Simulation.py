import m5
from m5.objects import *

import argparse

# Cache definitions

class L1ICache(Cache):
    assoc = 2
    tag_latency = 1
    data_latency = 1
    response_latency = 1
    mshrs = 4
    tgts_per_mshr = 20
    size = "16kB"

    def connectCPU(self, cpu):
        self.cpu_side = cpu.icache_port

    def connectBus(self, bus):
        self.mem_side = bus.cpu_side_ports


class L1DCache(Cache):
    assoc = 2
    tag_latency = 1
    data_latency = 1
    response_latency = 1
    mshrs = 4
    tgts_per_mshr = 20
    size = "64kB"

    def connectCPU(self, cpu):
        self.cpu_side = cpu.dcache_port

    def connectBus(self, bus):
        self.mem_side = bus.cpu_side_ports


class L2Cache(Cache):
    assoc = 8
    tag_latency = 10
    data_latency = 10
    response_latency = 10
    mshrs = 16
    tgts_per_mshr = 20
    size = "256kB"

    def connectCPUSideBus(self, bus):
        self.cpu_side = bus.mem_side_ports

    def connectMemSideBus(self, bus):
        self.mem_side = bus.cpu_side_ports


# -----------------------------
# Argument parsing
# -----------------------------
parser = argparse.ArgumentParser(description="Pipeline experiment (SE mode)")
parser.add_argument(
    "--binary",
    type=str,
    default="/bin/echo",
    help="Binary to run (default: /bin/echo)",
)
parser.add_argument(
    "--options",
    type=str,
    default="Hello gem5 pipeline",
    help="Arguments for the binary",
)

options = parser.parse_args()

# -----------------------------
# System
# -----------------------------
system = System()

system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = "timing"
system.mem_ranges = [AddrRange("8192MiB")]

# -----------------------------
# CPU (superscalar, out-of-order)
# -----------------------------
system.cpu = [
    X86O3CPU(
        cpu_id=0,
        fetchWidth=4,
        decodeWidth=4,
        renameWidth=4,
        dispatchWidth=4,
        issueWidth=4,
        wbWidth=4,
        commitWidth=4,
    )
]

# -----------------------------
# Memory bus
# -----------------------------
system.membus = SystemXBar()
system.system_port = system.membus.cpu_side_ports

# -----------------------------
# Memory controller
# -----------------------------
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

# -----------------------------
# Workload (SE mode)
# -----------------------------
binary = options.binary
args = options.options.split()

system.workload = SEWorkload.init_compatible(binary)

process = Process()
process.executable = binary
process.cmd = [binary] + args

# -----------------------------
# CPU configuration
# -----------------------------
for cpu in system.cpu:
    cpu.workload = process
    cpu.createThreads()
    cpu.createInterruptController()

    cpu.interrupts[0].pio = system.membus.mem_side_ports
    cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
    cpu.interrupts[0].int_responder = system.membus.mem_side_ports

    # L2 bus
    cpu.l2bus = L2XBar()

    # L1 caches
    cpu.icache = L1ICache(size="16kB")
    cpu.dcache = L1DCache(size="64kB")

    cpu.icache.connectCPU(cpu)
    cpu.dcache.connectCPU(cpu)

    cpu.icache.connectBus(cpu.l2bus)
    cpu.dcache.connectBus(cpu.l2bus)

    # L2 cache
    cpu.l2cache = L2Cache(size="256kB")
    cpu.l2cache.connectCPUSideBus(cpu.l2bus)
    cpu.l2cache.connectMemSideBus(system.membus)

# -----------------------------
# Root
# -----------------------------
root = Root(full_system=False, system=system)

m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
