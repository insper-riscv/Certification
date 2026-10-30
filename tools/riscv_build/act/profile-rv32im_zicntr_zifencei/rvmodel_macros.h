# rvmodel_macros.h
# DUT-specific macro definitions for rv32im_pipeline_core (RV32IM/src)
# under ACT4 — I/M only, no Zicsr, no trap/privilege support.
#
# See link.ld for why this differs from every other config's
# rvmodel_macros.h in this vendored framework: Harvard MODIFICADO
# (separate instruction/data buses, ROM has no write path), so
# RVMODEL_BOOT below does the ROM->RAM copy + bss-zero + sp/gp setup
# this project's own crt0.S does for its regular tests — none of that
# is needed on the unified-memory targets (spike, cva6, ...) this
# macro file was originally modeled on.

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

# tests/env/sail_macros.h unconditionally requires these two for every
# .sig.elf (signature-mode) build, regardless of ref_model_exe — a
# framework quirk confirmed by actually building against it:
# build_plan.py only auto-supplies them via sail.json when
# ref_model_type==SAIL (config.py), but riscv_arch_test.h includes
# sail_macros.h for EVERY .sig.elf build, Spike-referenced ones
# included. Since this project's own ref_model_exe is spike (see
# test_config.yaml), sail.json's own platform.clint/
# simple_interrupt_generator.base values (present here anyway, for if
# this ever switches to Sail) never actually reach the compiler —
# these values are pure placeholders to satisfy sail_macros.h's
# #ifndef guard, never used by anything that runs.
#define SAIL_CLINT_BASE_ADDRESS 0x2000000
#define SAIL_SIMPLE_INTERRUPT_GENERATOR_BASE_ADDRESS 0xC000000

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .balign 8; .global tohost; tohost: .dword 0;         \
        .balign 8; .global fromhost; fromhost: .dword 0;     \
        .popsection

##### STARTUP #####

# RVMODEL_BOOT: the core has no CSRs and no privilege modes, so RVMODEL_BOOT_TO_MMODE stays
# undefined and RVMODEL_BOOT is the only boot-time hook. The simulation loads the data of the
# ELF straight into the RAM, so the boot only sets the registers a test relies on:
#   1. gp, with `.option norelax`: a `la` of a symbol within +/-0x800 of gp would otherwise be
#      relaxed into a gp-relative access while gp is still zero.
#   2. sp, at the top of the stack that the linker script reserves.
#define RVMODEL_BOOT                                    \
  .option push                                          ;\
  .option norelax                                       ;\
1:auipc gp, %pcrel_hi(__global_pointer$)                 ;\
  addi  gp, gp, %pcrel_lo(1b)                            ;\
  .option pop                                           ;\
  la    sp, __stack_top

// Left undefined on purpose, see the comment above.
//#define RVMODEL_BOOT_TO_MMODE

##### TERMINATION #####

# tohost HTIF encoding: 1 = pass, 3 = fail ((1 << 1) | 1). After writing it the test jumps to
# rv32_wait_restart, the routine of the boot ROM (fixed at 0x100) that parks the core until the
# host sets the go flag again; a self loop in the ELF would keep the core from ever restarting.
#define BOOT_ROM_WAIT_RESTART 0x100

#define RVMODEL_HALT_PASS  \
  li x1, 1                ;\
  la t0, tohost           ;\
  write_tohost_pass:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  li t1, BOOT_ROM_WAIT_RESTART ;\
  jr t1                   ;\

#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  li t1, BOOT_ROM_WAIT_RESTART ;\
  jr t1                   ;\

##### IO #####

# No initialization needed — the "console" is a single plain RAM
# word (rv32_act_console, see link.ld), watched directly off the
# ram_addr/ram_wdata bus by tools/riscv_build/act/sim/test_act.py,
# not a real UART with a status/ready register to poll.
//#define RVMODEL_IO_INIT(_R1, _R2, _R3)

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  la   _R2, rv32_act_console ;                        \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */              \
3:

#endif
