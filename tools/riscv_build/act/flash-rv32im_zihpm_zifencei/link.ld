/* Linker script of the ACT4 target of the modular simulation platform (Insper-RISC-V, src/simulation/modular).
 *
 * The map is the one of the platform: a 4 KB boot ROM at the start, the ROM right after it up to 1 MB, and a
 * 1 MB RAM from 0x00100000. The core fetches the code of the test from the ROM and keeps the data in the RAM.
 * Every section is loaded at the address it runs from, so the same ELF is a valid program for the Sail model
 * (one flat memory that covers both regions) and for the core, whose simulation loads the first 4 KB into the
 * boot ROM, the code region into the ROM and the data region into the RAM.
 *
 *   0x00000000  boot ROM, 4 KB   the stub that jumps to the first instruction of the test (RVMODEL_DATA_SECTION)
 *   0x00001000  ROM, 1 MB - 4 KB code of the test and of the model macros
 *   0x00100000  RAM, 1 MB        .rodata, .data, .bss, the stack
 *   0x001FFFE0  end of the RAM proper; the last 32 bytes hold, outside the RAM region of the
 *               linker (so the sections of the test never reach them):
 *                 0x001FFFE0  tohost     (8 bytes, HTIF)
 *                 0x001FFFE8  fromhost   (8 bytes, HTIF)
 *                 0x001FFFF0  console    (4 bytes, one character per store)
 */

MEMORY
{
  boot (rx) : ORIGIN = 0x00000000, LENGTH = 4K
  rom (rx)  : ORIGIN = 0x00001000, LENGTH = 1M - 4K
  ram (rw)  : ORIGIN = 0x00100000, LENGTH = 1M - 32
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
  .text.boot ORIGIN(boot) : { KEEP(*(.text.boot)) } > boot

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
