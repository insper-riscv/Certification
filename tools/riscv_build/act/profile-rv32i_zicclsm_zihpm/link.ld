/* Linker script of the ACT4 target of rv32im_pipeline_core.
 *
 * The core fetches instructions from a ROM and reads and writes data in a RAM, two separate
 * memories. Every section is loaded at the address it runs from, so the same ELF is a valid
 * program for the Sail model (one flat memory that covers both regions) and for the core, whose
 * simulation loads the instruction region into the ROM and the data region into the RAM.
 *
 * The map is the one in sail.json (memory.regions) and in the testbench:
 *
 *   0x00000000  ROM, 4 MB   code of the test and of the model macros
 *   0x00400000  RAM, 2 MB   .rodata, .data, .bss, the stack
 *   0x005FFFE0  end of the RAM proper; the last 32 bytes hold, outside the RAM region of the
 *               linker (so the sections of the test never reach them):
 *                 0x005FFFE0  tohost     (8 bytes, HTIF)
 *                 0x005FFFE8  fromhost   (8 bytes, HTIF)
 *                 0x005FFFF0  console    (4 bytes, one character per store)
 */

MEMORY
{
  rom (rx) : ORIGIN = 0x00000000, LENGTH = 4M
  ram (rw) : ORIGIN = 0x00400000, LENGTH = 2M - 32
}

TEST_BASE = ORIGIN(rom);
STACK_SIZE = 0x1000;
NUM_HARTS = 1;

OUTPUT_ARCH("riscv")
ENTRY(rvtest_entry_point)

PROVIDE(__stack_size = STACK_SIZE);
PROVIDE(__num_harts = NUM_HARTS);

SECTIONS
{
  .text.init   TEST_BASE : { *(.text.init) } > rom
  .text.rvtest . : { *(.text.rvtest) *(.text.rvtest.*) } > rom
  .text.rvmodel . : { *(.text.rvmodel) *(.text.rvmodel.*) *(.text) *(.text.*) } > rom

  .rodata ORIGIN(ram) : { *(.rodata) *(.rodata.*) *(.srodata) *(.srodata.*) } > ram
  .data . : {
    . = ALIGN(4);
    /* gp reaches +/-0x800 around this point */
    PROVIDE(__global_pointer$ = . + 0x800);
    *(.data) *(.data.*) *(.sdata) *(.sdata.*)
  } > ram

  . = ALIGN(16);
  .bss (NOLOAD) : {
    __bss_start = .;
    *(.sbss) *(.sbss.*) *(.bss) *(.bss.*) *(COMMON)
    . = ALIGN(16);
    __bss_end = .;
  } > ram

  . = ALIGN(16);
  __stack_bottom = .;
  . += __stack_size * __num_harts;
  __stack_top = .;

  ASSERT(__stack_top <= ORIGIN(ram) + LENGTH(ram), "the test does not fit in the RAM of the target")

  /* The HTIF words, from RVMODEL_DATA_SECTION, at the end of the RAM. No "> ram": a section
   * placed exactly at ORIGIN+LENGTH trips the region-overflow check of ld, though the address
   * is real memory. */
  .tohost ORIGIN(ram) + LENGTH(ram) (NOLOAD) : { *(.tohost) }
}

PROVIDE(rv32_act_console = ORIGIN(ram) + LENGTH(ram) + 16);
