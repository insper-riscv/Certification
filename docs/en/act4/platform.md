# ACT4 simulation platform

🌐 [Português](../../pt-br/act4/platform.md) · [English](platform.md)

## 1. What runs

The 120 profiles of the Core matrix (`Insper-RISC-V/Core/profiles/matrix.yaml`) run on the modular simulation platform of Insper-RISC-V (`src/simulation/modular`). The top that cocotb simulates is `act_modular_top` (`tools/riscv_build/act/sim/`), which gives the modular top the ports the testbenches observe.

| Group | Profiles | Model | ROM | RAM | Testbench |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Without Zifencei | 60 | `integrated` | 1 MB inside the chip | 1 MB inside the chip | `test_act.py` watches the RAM write bus |
| With Zifencei | 60 | `external` | 1 MB behind the 4 kbit instruction cache | 1 MB behind the 4 kbit data cache | `test_act_sdram.py` reads `tohost` from the RAM chip through the debug port |

## 2. Memory map

| Region | Start | Size |
| :--- | :--- | :--- |
| BOOT_ROM | `0x00000000` | 4 KB |
| ROM | `0x00001000` | 1 MB minus 4 KB |
| RAM | `0x00100000` | 1 MB |

The three HTIF words sit at the end of the RAM, at `0x001FFFE0` (`tohost`), `0x001FFFE8` (`fromhost`) and `0x001FFFF0` (console). The ELF of each test loads every section at the address it runs from. The first 4 KB of the ELF are the BOOT_ROM, with a stub that jumps to `0x00001000`, and the rest of the code is the ROM. In the profiles with Zifencei, the `Zifencei-fence.i-00` test rewrites its own code and uses the `flash-ram` variant, with the body of the test in the RAM.

## 3. Generated files

| File | Generator |
| :--- | :--- |
| `tools/riscv_build/config.platform-*.yaml` | `riscv-tools platform sync`, from the submodule |
| `tools/riscv_build/config.modular.yaml` | `gen_profiles.py`, with the sources of `config.platform-de0-cv.yaml` |
| `tools/riscv_build/act/profile-*/` and `config.profile-*.yaml` | `gen_profiles.py`, one per profile of the matrix |
| `tools/riscv_build/act/flash-*/`, `act/flash-ram-*/` and `config.flash-*.yaml` | `gen_flash_profiles.py`, one per profile with Zifencei |
| `build/target/` (target of a profile on a memory model) | `gen_profiles.py --profile ... --memory ... --out ...`, at run time and not versioned; see [the certification matrix](matrix.md) |

The RV32E base profiles (`rv32e*` and `rv32em*`) use `isa.base: e`, the `HAS_E` generic and the `ilp32e` ABI. The published UDB does not declare the `E` extension, so the UDB of these profiles carries `arch_overlay: rv32e`, and `sh tools/riscv_build/install_udb_overlay.sh` installs the `tools/riscv_build/act/udb-overlay` folder with that extension into `ci-act4` before `certify`.

## 4. How to run a profile

```bash
uv sync
riscv-tools --config tools/riscv_build/config.profile-rv32im_zicsr.yaml certify
```

To certify a profile on another memory model, section 4 of [the certification matrix](matrix.md) generates the target at run time.

The run needs the raised stack limit, which `certify` sets, and about 6 GiB of RAM per simulation. The result is in `logs/certification/latest.log`.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
