/* Linker script of the ACT4 target of rv32im_pipeline_core with the code and the data in the SDRAM.
 *
 * The core fetches instructions from the SDRAM through its instruction cache and reads and writes
 * data in the same SDRAM, so the whole test is one flat region. The simulation loads the ELF into the
 * SDRAM chip model at time zero (as the host loads the chip through the debug port), and the boot ROM
 * only jumps to the first instruction. Every section is loaded at the address it runs from.
 *
 * The map is the one in sail.json (memory.regions) and in the testbench:
 *
 *   0x40000000  code of the test and of the model macros
 *               then .rodata, .data, .bss and the stack, one after the other
 *   0x400FFFE0  end of the region proper; the last 32 bytes hold, outside the region of the
 *               linker (so the sections of the test never reach them):
 *                 0x400FFFE0  tohost     (8 bytes, HTIF)
 *                 0x400FFFE8  fromhost   (8 bytes, HTIF)
 *                 0x400FFFF0  console    (4 bytes, one character per store)
 */

MEMORY
{
  mem (rwx) : ORIGIN = 0x40000000, LENGTH = 1M - 32
}

TEST_BASE = ORIGIN(mem);
STACK_SIZE = 0x1000;
NUM_HARTS = 1;

OUTPUT_ARCH("riscv")
ENTRY(rvtest_entry_point)

PROVIDE(__stack_size = STACK_SIZE);
PROVIDE(__num_harts = NUM_HARTS);

SECTIONS
{
  .text.init   TEST_BASE : { *(.text.init) } > mem
  .text.rvtest . : { *(.text.rvtest) *(.text.rvtest.*) } > mem

  .rodata . : { *(.rodata) *(.rodata.*) *(.srodata) *(.srodata.*) } > mem
  .data . : {
    . = ALIGN(4);
    /* gp reaches +/-0x800 around this point */
    PROVIDE(__global_pointer$ = . + 0x800);
    *(.data) *(.data.*) *(.sdata) *(.sdata.*)
  } > mem

  . = ALIGN(16);
  .bss (NOLOAD) : {
    __bss_start = .;
    *(.sbss) *(.sbss.*) *(.bss) *(.bss.*) *(COMMON)
    . = ALIGN(16);
    __bss_end = .;
  } > mem

  . = ALIGN(16);
  __stack_bottom = .;
  . += __stack_size * __num_harts;
  __stack_top = .;

  /* The code of the model macros comes after the data and the stack, so that its size does not
   * move the symbols of the test data (the signature must sit at the same address in the ELF of
   * the model and in the ELF of the core). */
  .text.rvmodel . : { *(.text.rvmodel) *(.text.rvmodel.*) *(.text) *(.text.*) } > mem

  ASSERT(. <= ORIGIN(mem) + LENGTH(mem), "the test does not fit in the SDRAM region of the target")

  /* The HTIF words, from RVMODEL_DATA_SECTION, at the end of the region. */
  .tohost ORIGIN(mem) + LENGTH(mem) (NOLOAD) : { *(.tohost) }
}

PROVIDE(rv32_act_console = ORIGIN(mem) + LENGTH(mem) + 16);
