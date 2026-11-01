/* Linker script of the ACT4 target of the platform with the FLASH behind the caches, for the tests
 * that rewrite their own code (the Zifencei tests): the body of the test sits in the SDRAM, where the
 * stores take effect, and only the entry code, the model macros and the constants sit in the FLASH.
 *
 * The code and the constants of the test sit in the FLASH, a chip at 0x20000000 that the core reaches
 * through the instruction and the data cache; the data, the stack and the HTIF words sit in the SDRAM
 * at 0x40000000. The simulation and the board load the ELF as the host does: the FLASH image and the
 * SDRAM image are written at the address each section runs from, and the boot ROM only jumps to the
 * first instruction.
 *
 * The map is the one in sail.json (memory.regions) and in the testbench:
 *
 *   0x20000000  code of the test and of the model macros, then .rodata (the FLASH, read-only)
 *   0x40000000  .data, .bss and the stack, one after the other (the SDRAM)
 *   0x400FFFE0  end of the data region proper; the last 32 bytes hold, outside the region of the
 *               linker (so the sections of the test never reach them):
 *                 0x400FFFE0  tohost     (8 bytes, HTIF)
 *                 0x400FFFE8  fromhost   (8 bytes, HTIF)
 *                 0x400FFFF0  console    (4 bytes, one character per store)
 */

MEMORY
{
  flash (rx)  : ORIGIN = 0x20000000, LENGTH = 1M
  mem   (rwx) : ORIGIN = 0x40000000, LENGTH = 1M - 32
}

TEST_BASE = ORIGIN(flash);
STACK_SIZE = 0x1000;
NUM_HARTS = 1;

OUTPUT_ARCH("riscv")
ENTRY(rvtest_entry_point)

PROVIDE(__stack_size = STACK_SIZE);
PROVIDE(__num_harts = NUM_HARTS);

SECTIONS
{
  .text.init   TEST_BASE : { *(.text.init) } > flash
  .text.rvmodel . : { *(.text.rvmodel) *(.text.rvmodel.*) } > flash
  .rodata . : { *(.rodata) *(.rodata.*) *(.srodata) *(.srodata.*) } > flash

  ASSERT(. <= ORIGIN(flash) + LENGTH(flash), "the test does not fit in the FLASH of the target")

  .text.rvtest ORIGIN(mem) : { *(.text.rvtest) *(.text.rvtest.*) *(.text) *(.text.*) } > mem

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

  ASSERT(. <= ORIGIN(mem) + LENGTH(mem), "the data of the test does not fit in the SDRAM region of the target")

  /* The HTIF words, from RVMODEL_DATA_SECTION, at the end of the data region. */
  .tohost ORIGIN(mem) + LENGTH(mem) (NOLOAD) : { *(.tohost) }
}

PROVIDE(rv32_act_console = ORIGIN(mem) + LENGTH(mem) + 16);
