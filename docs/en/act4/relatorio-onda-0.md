# ACT4 report of Wave 0

🌐 [Português](../../pt-br/act4/relatorio-onda-0.md) · [English](relatorio-onda-0.md)

## 1. Versions used

| Item | Version |
| :--- | :--- |
| Insper-RISC-V (submodule) | tag `Onda-0`, commit `ae44830` |
| Insper-RISC-V executed | `422057f`, which differs from the tag only in the synthesis top of the DE0-CV board (no effect on ACT4 or on the simulations) |
| Core | `8a828cc` |
| Memory, Peripherals, Common-Components | `c71106f`, `d7253f6`, `9aa6a75` |
| riscv-arch-test (ACT4) | `bfe6155` |
| `riscv-tools` | 1.9.2, in the `ci-act4` image |
| Reference model | Sail RISC-V 0.16 |
| UDB | `udb` gem 0.1.18 |
| Simulator | GHDL 6.0.0 with cocotb |

## 2. Profiles executed

Each profile ran in a container of the `ci-act4` image on a distinct workstation (three at a time), on the modular simulation platform. The number of ELFs is the sum of the tests of the folder of each declared extension.

| Profile | Declared extensions | Platform | ELFs | Result | Time |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `profile-rv32i` (control) | I | on-chip memories | 39 | 39 passed | 417 s |
| `profile-rv32im` | I, M, Zmmul | on-chip memories | 51 | 51 passed | 541 s |
| `flash-rv32im_zicclsm_zicntr_zihpm_zifencei` | I, M, Zmmul, Zicsr, Zicntr, Zihpm, Zifencei, Zicclsm | FLASH and RAM behind the caches | 67 | 67 passed | 656 s |
| `adhoc-zimop` | I, Zimop | on-chip memories | 79 | 79 passed | 741 s |
| `adhoc-zicond` | I, Zicond | on-chip memories | 41 | 41 passed | 397 s |
| `adhoc-todas` | I, M, Zmmul, Zicsr, Zicntr, Zihpm, Zicclsm, Zimop, Zicond, Zihintntl, Zihintpause | on-chip memories | 113 | 113 passed | 1100 s |

No test failed in the final runs.

## 3. Coverage by extension

| Extension | ELFs in the `riscv-arch-test` in use | Profiles that cover it |
| :--- | :--- | :--- |
| Zimop | 40 | `adhoc-zimop`, `adhoc-todas` |
| Zicond | 2 | `adhoc-zicond`, `adhoc-todas` |
| Zihpm | 2 | Zihpm profile with Zifencei, `adhoc-todas` |
| Zihintntl | 4 | `adhoc-todas` |
| Zihintpause | 1 | `adhoc-todas` |
| M and Zmmul | 8 and 4 | `profile-rv32im` and the other profiles with M |

## 4. The `adhoc` profiles

The matrix of the Core and the generators `gen_profiles.py` and `gen_flash_profiles.py` produce no profile with Zimop, Zicond, Zihintntl or Zihintpause, and the matrix was not changed. The three `adhoc` profiles derive from `profile-rv32i` and `profile-rv32im_zicclsm_zicntr_zihpm` with three changes.

1. The UDB of the target declares the new extension (Zimop 1.0.0, Zicond 1.0.0, Zihintntl 1.0.0, Zihintpause 2.0.0).
2. The `sail.json` of the target marks the extension as `supported`.
3. The `sim.parameters` of the config turns on `HAS_<EXTENSION>` and the `act.extensions` list gains the extension.

For the generics to reach the core, `act_modular_top` forwards `has_zimop`, `has_zicond`, `has_zihintntl` and `has_zihintpause` to `modular_sim_top`.

## 5. Zihpm

The generated profiles declare four event counters (indices 3 to 6), all 64 bits wide, with the nine events of the core. No profile of the Certification matrix declares the full bank of 29 counters, so ACT4 exercises only the two Zihpm tests of the `riscv-arch-test` folder.

## 6. RV32E

The `rv32e*` and `rv32em*` profiles need the UDB overlay `E.yaml`, installed by the step `sh tools/riscv_build/install_udb_overlay.sh` of the `certification-profiles.yml` workflow. No RV32E profile was executed for this report.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
