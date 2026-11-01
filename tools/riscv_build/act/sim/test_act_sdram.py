"""cocotb testbench for ACT4 certification ELFs that run from the SDRAM (rv32im-sdram).

The platform simulation (core, instruction cache, SDRAM controller and chip model) starts with the
ELF already in the chip, as if the host had loaded it through the debug port, and the boot ROM
jumps to the first instruction. The test signals its end through the HTIF `tohost` word, which is
a word of the SDRAM chip: the testbench reads it from the chip model through the word debug port
(the same view the host has), a PASS being 1 and any other odd value a FAIL.

Must stay in sync with ../rv32im-sdram/link.ld: the region ends at 0x400FFFE0, where tohost sits.
"""

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

SDRAM_BASE = 0x40000000
TOHOST_ADDR = 0x400FFFE0
TOHOST_PASS = 1
POLL_CYCLES = 200
TIMEOUT_CYCLES = 8_000_000


async def read_word(dut, address: int) -> int:
    """The 32-bit word at an address of the SDRAM chip model."""
    dut.DBG_WORD_ADDR.value = (address - SDRAM_BASE) // 4
    for _ in range(3):
        await RisingEdge(dut.CLK_MEM)
    await Timer(1, unit="ns")
    return int(dut.DBG_WORD_DATA.value)


@cocotb.test()
async def test_program(dut) -> None:
    test_name = os.environ.get("TEST_NAME", "?")
    dut._log.info(f"running {test_name}")

    cocotb.start_soon(Clock(dut.CLK, 10, unit="ns").start())
    cocotb.start_soon(Clock(dut.CLK_MEM, 7, unit="ns").start())
    dut.reset.value = 1
    await ClockCycles(dut.CLK, 5)
    dut.reset.value = 0

    cycles = 0
    while cycles < TIMEOUT_CYCLES:
        await ClockCycles(dut.CLK, POLL_CYCLES)
        cycles += POLL_CYCLES
        tohost = await read_word(dut, TOHOST_ADDR)
        if tohost & 1:
            dut._log.info(f"CLOCK CYCLES TAKEN about {cycles}")
            if tohost == TOHOST_PASS:
                dut._log.info("PASS")
                return
            raise AssertionError(f"test signalled FAIL via tohost (value={tohost:#x})")

    raise AssertionError(
        f"timed out after {TIMEOUT_CYCLES} cycles without a tohost PASS/FAIL write"
    )
