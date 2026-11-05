"""cocotb testbench for ACT4 certification ELFs that run behind the caches (the external model of the modular platform).

The platform simulation (core, instruction and data cache, FLASH and RAM chips) starts with the ELF already in
the chips, as if the host had loaded it, and the boot ROM jumps to the first instruction. The test signals its
end through the HTIF `tohost` word, which is a word of the RAM chip: the testbench reads it from the chip
model through the word debug port (the same view the host has), a PASS being 1 and any other odd value a FAIL.

Must stay in sync with ../rv32im-min/link.ld: the RAM starts at 0x00100000 and ends at 0x001FFFE0, where tohost sits.
"""

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

RAM_BASE = 0x00100000
TOHOST_ADDR = 0x001FFFE0
TOHOST_PASS = 1
POLL_CYCLES = 200
TIMEOUT_CYCLES = 8_000_000


async def read_word(dut, address: int) -> int:
    """The 32-bit word at an address of the RAM chip model."""
    dut.i_dbg_word_addr.value = (address - RAM_BASE) // 4
    for _ in range(3):
        await RisingEdge(dut.i_clk_mem)
    await Timer(1, unit="ns")
    return int(dut.o_dbg_word_data.value)


@cocotb.test()
async def test_program(dut) -> None:
    test_name = os.environ.get("TEST_NAME", "?")
    dut._log.info(f"running {test_name}")

    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    cocotb.start_soon(Clock(dut.i_clk_mem, 7, unit="ns").start())
    dut.i_rst.value = 1
    await ClockCycles(dut.i_clk, 5)
    dut.i_rst.value = 0

    cycles = 0
    while cycles < TIMEOUT_CYCLES:
        await ClockCycles(dut.i_clk, POLL_CYCLES)
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
