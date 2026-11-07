# Certification matrix: profiles and memory models

🌐 [Português](../../pt-br/act4/matrix.md) · [English](matrix.md)

## 1. What the matrix crosses

Each certification job is a (profile, memory model) pair. The profile is a set of extensions of the core, such as `rv32im_zicntr`. The memory model says where the ROM and the RAM of the modular simulation platform sit and which caches exist. The ACT4 target of the pair (UDB, Sail configuration, `test_config.yaml`, linker and the `certify` config) is generated at run time and never versioned; the 154 versioned configs of `tools/riscv_build` remain what the generators write, and the CI checks that generation reproduces what is committed.

## 2. The 16 models and the 4 the top accepts

The choice has four axes, in the `--memory` syntax of `riscv-tools`.

| Axis | Values |
| :--- | :--- |
| `rom` | `int` (inside the chip) or `ext` (simulated FLASH chip) |
| `ram` | `int` or `ext` (simulated RAM chip) |
| `icache` | `on` or `off` |
| `dcache` | `on` or `off` |

They give $2^4 = 16$ combinations. The `modular_sim_top` of Insper-RISC-V instantiates the instruction cache only in the external ROM branch and the data cache only in the external RAM branch, and does not declare the `HAS_ICACHE` and `HAS_DCACHE` generics. A cache therefore exists if, and only if, the memory it serves is external:

$$\text{icache} \iff \text{rom} = \text{ext}, \qquad \text{dcache} \iff \text{ram} = \text{ext}$$

That leaves 4 accepted combinations, the architectures `A` (internal ROM and RAM), `B` (internal ROM and external RAM with a data cache), `C` (external ROM with an instruction cache and internal RAM) and `D` (both external, with both caches); they are the `integrated`, `external-data`, `external-instruction` and `external` models of the top. GHDL confirms it: elaborating `act_modular_top` with `ROM_EXTERNAL` and `RAM_EXTERNAL` in the four values reaches the loading of the memory images; asking for `HAS_ICACHE` or `HAS_DCACHE` ends with `cannot find in top entity generic`.

| `rom` | `ram` | `icache` | `dcache` | Accepted | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `int` | `int` | `off` | `off` | yes | Integrated model: both memories answer without wait, and the testbench watches the RAM write bus. |
| `int` | `ext` | `off` | `on` | yes | External data: the data cache sits between the core and the RAM chip, and the testbench reads `tohost` from the chip through the debug port. |
| `ext` | `int` | `on` | `off` | yes | External instructions: the instruction cache sits between the core and the FLASH chip. |
| `ext` | `ext` | `on` | `on` | yes | External model: both caches, one router per cache and an arbiter for the FLASH chip. |
| `int` | any | `on` | any | no | The instruction cache does not exist over an internal ROM. |
| any | `int` | any | `on` | no | The data cache does not exist over an internal RAM. |
| `ext` | any | `off` | any | no | The FLASH chip speaks the line protocol of the cache, and the top has no generic to remove it. |
| any | `ext` | any | `off` | no | The RAM chip speaks the line protocol of the cache, and the top has no generic to remove it. |

The generation command (section 4) rejects each of the 12 refused combinations and states the reason. A cache over an internal memory only adds latency and blocking, because the memory already answers without wait; that combination is valid for `riscv-tools`, but no simulation top builds it.

### 2.1. The Zifencei restriction

The `Zifencei-fence.i-00` test rewrites its own code, so its body runs from the RAM. The instruction fetch only reaches the RAM through the instruction cache, and the write only reaches it through the data cache. A profile with Zifencei therefore runs only on the model with both memories external and both caches. On the other three models the pair is refused.

## 3. Minimal profiles

`tools/riscv_build/minimal_profiles.yaml` lists, for each ACT4 test folder that the core implements, the smallest profile whose extensions contain the `REQUIRED_EXTENSIONS` of the folder's tests, plus the profiles with everything together of each base. The folders come from the ACT4 checkout of the `ci-act4` image, the same commit as the UDB gems.

<!-- gen:table -->
| Profile | Extensions added to the base | Test folder | Tests | Jobs |
| :--- | :--- | :--- | ---: | ---: |
| `rv32i` | none | `rv32i/I` | 39 | 4 |
| `rv32im` | M | `rv32i/M` | 51 | 4 |
| `rv32i_zmmul` | Zmmul | `rv32i/Zmmul` | 43 | 4 |
| `rv32i_zicntr` | Zicntr | `rv32i/Zicntr` | 47 | 4 |
| `rv32i_zihpm` | Zihpm | `rv32i/Zihpm` | 47 | 4 |
| `rv32i_zicclsm` | Zicclsm | `rv32i/Zicclsm` | 44 | 4 |
| `rv32i_zifencei` | Zifencei | `rv32i/Zifencei` | 40 | 1 |
| `rv32i_zimop` | Zimop | `rv32i/Zimop` | 79 | 4 |
| `rv32i_zicond` | Zicond | `rv32i/Zicond` | 41 | 4 |
| `rv32i_zihintntl` | Zihintntl | `rv32i/Zihintntl` | 43 | 4 |
| `rv32i_zihintpause` | Zihintpause | `rv32i/Zihintpause` | 40 | 4 |
| `rv32e` | none | `rv32e/E` | 39 | 4 |
| `rv32em` | M | `rv32e/M` | 51 | 4 |
| `rv32e_zmmul` | Zmmul | `rv32e/Zmmul` | 43 | 4 |
| `rv32im_full` | M, Zicclsm, Zicntr, Zihpm, Zimop, Zicond, Zihintntl, Zihintpause | every folder of the base together | 113 | 4 |
| `rv32im_full_zifencei` | M, Zicclsm, Zicntr, Zihpm, Zifencei, Zimop, Zicond, Zihintntl, Zihintpause | every folder of the base together | 114 | 1 |
| `rv32em_full` | M, Zicclsm, Zicntr, Zihpm, Zimop, Zicond, Zihintntl, Zihintpause | every folder of the base together | 51 | 4 |
| `rv32em_full_zifencei` | M, Zicclsm, Zicntr, Zihpm, Zifencei, Zimop, Zicond, Zihintntl, Zihintpause | every folder of the base together | 51 | 1 |
<!-- /gen -->

The test count is the number of ELFs that ACT4 generates for the profile, that is, the number of files whose `REQUIRED_EXTENSIONS` the profile covers, including those of the extensions it implies. The `rv32i_zicntr` and `rv32i_zihpm` profiles include Zicsr because the counters are CSRs. Zmmul has its own profile because it is the RTL variant that multiplies without dividing. Zimop, Zicond, Zihintntl and Zihintpause are not part of the profile matrix of the Core; the core turns them on through generics of the top (`HAS_ZIMOP`, `HAS_ZICOND`, `HAS_ZIHINTNTL`, `HAS_ZIHINTPAUSE`), and the generator accepts them in the extension set of a profile.

<!-- gen:total -->
The `rv32i_zifencei`, `rv32im_full_zifencei` and `rv32em_full_zifencei` profiles run on one model each (section 2.1); the other 15 run on all 4. The total of the automatic workflow is therefore:

$$15 \times 4 + 3 \times 1 = 63 \text{ jobs}$$
<!-- /gen -->

## 4. Generating the target at run time

```bash
uv run python tools/riscv_build/gen_profiles.py \
    --profile rv32i_zimop \
    --memory rom=ext,ram=int,icache=on,dcache=off \
    --out build/target --jobs 4
riscv-tools --config build/target/config.yaml certify
```

| Option | Effect |
| :--- | :--- |
| `--profile` | Name of a profile of the Core matrix or of `minimal_profiles.yaml`. |
| `--memory` | Memory model, with the four keys. A combination the top does not accept, or that the profile cannot use, ends the command with the reason. |
| `--out` | Folder that receives `act/<target>/` and `config.yaml`. Inside the repository, or an absolute path. |
| `--jobs` | Value of `act.jobs`, which `certify` passes to the ACT4 `make` as `JOBS=`. Zero lets ACT4 choose. The simulations of `certify` run one at a time. |

The target of a profile (UDB, `sail.json`, `test_config.yaml` and linker) does not depend on the memory model, because the map is the same on the four models. What changes is `config.yaml`.

| RAM model | Images | Testbench |
| :--- | :--- | :--- |
| `int` | Three images: BOOT_ROM, ROM and RAM | `test_act.py`, which watches the RAM write bus of the core |
| `ext` | FLASH image and RAM chip image (`flash_base` and `sdram_base`) | `test_act_sdram.py`, which reads `tohost` from the chip through the debug port |

The `ROM_EXTERNAL` and `RAM_EXTERNAL` generics of `act_modular_top` follow the model. A profile with Zifencei also gets the `-ram` target, with the body of the test in the RAM, and `config.yaml` declares it in `ram_tests`. RV32E profiles need the UDB overlay (`sh tools/riscv_build/install_udb_overlay.sh`) before `certify`.

`tools/riscv_build/act_matrix.py` builds and prints the matrix of the workflows, with the pairs left out and the reason of each.

## 5. Workflows

| Workflow | Trigger | Crosses | Controls |
| :--- | :--- | :--- | :--- |
| `certification (ACT4)` | `pull_request`, `push` on `main` | The <!-- gen:profiles -->18<!-- /gen --> minimal profiles with the accepted models (<!-- gen:jobs -->63<!-- /gen --> jobs) | `max-parallel` of 16, `concurrency` per branch, `act.jobs` of 4 |
| `certification (ACT4, all profiles and memory models)` | Manual, with a key | Every profile (the 120 reference ones of the Core matrix, without Zimop and Zicond, and the minimal ones) with the accepted models | `confirmation` (value of the secret `CERTIFICATION_RUN_SECRET`), `target`, `jobs`, `max-parallel`, `memory`, `only` |
| `certification (ACT4, one profile and memory model)` | Manual | One profile and one model | `profile`, `memory`, `target`, `jobs` |

The `target` input is `simulated` (GHDL on GitHub runners) or `real` (the DE0-CV board, on a self-hosted runner). The value `real` ends the workflow with a message, because the board runner is not configured. Every input reaches the shell through environment variables and goes through a character whitelist before use, and the `plan` job prints the matrix to the log and to the job summary before any simulation.

## 6. Sizing

Each job simulates the tests of the profile one by one, and each test reanalyzes the VHDL before simulating.

| Profile | Architecture | Tests | Time | Peak RAM | Workstation |
| :--- | :--- | ---: | ---: | ---: | :--- |
| `rv32i_zicntr` | `A` | 47 | 488 s | 5.9 GiB | workstation3 |
| `rv32i_zicclsm` | `D` | 44 | 409 s | 3.0 GiB | workstation4 |
| `rv32i_zifencei` | `D` | 40 | 394 s | 3.0 GiB | workstation2 |
| `rv32im_full` | `B` | 113 | 894 s | 3.0 GiB | workstation2 |
| `rv32i_zimop` | `C` | 79 | 810 s | 5.9 GiB | workstation3 |
| `rv32e` | `C` | 39 | 440 s | 5.9 GiB | workstation4 |

The table lists pairs run with `--jobs 6` in 6-CPU containers of the `ci-act4` image; every test passed. The time is wall-clock, and the peak RAM is that of the largest process of the simulation. With an internal RAM (architectures `A` and `C`) the peak is 5.9 GiB, and with an external RAM (`B` and `D`) it is 3.0 GiB. One test takes 8 to 10 s, almost all of it analyzing the VHDL.

The <!-- gen:jobs -->63<!-- /gen --> jobs of the automatic workflow add up to <!-- gen:runs -->3289<!-- /gen --> test runs, about <!-- gen:hours -->9<!-- /gen --> hours of simulation, not counting the recursive checkout, `uv sync` and the generation of the ELFs. With `max-parallel` of 16 the estimate for the certification is about <!-- gen:wall -->1<!-- /gen --> h, and the largest job takes about 15 minutes of simulation (<!-- gen:largest -->`rv32im_full_zifencei`<!-- /gen -->, with <!-- gen:largest_tests -->114<!-- /gen --> tests). The testbench of the internal RAM waits up to 8 million cycles for `tohost`, because an external ROM behind the instruction cache multiplies the duration of the long tests. The memory limit of a standard GitHub runner (16 GiB) fits any job.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
