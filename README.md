# Certification

ACT4 ([riscv-arch-test](https://github.com/riscv/riscv-arch-test))
certification of the RV32IM core. One job: run the official suite against
the core in simulation (cocotb/GHDL) and report the result. It never runs
on the board.

| Path | What |
| :--- | :--- |
| `vendor/riscv-arch-test` | the official suite, a pinned submodule |
| `tools/riscv_build/act/rv32im-min/` | the DUT target: `test_config.yaml`, the UDB YAML, `rvmodel_macros.h`, `link.ld`, and `spike-rv32im-min`, Spike with this target's memory map (the reference model) |
| `tools/riscv_build/act/sim/test_act.py` | the cocotb testbench: watches the HTIF `tohost` word |
| `tools/riscv_build/config.yaml` | `sim:` (VHDL sources, toplevel) and `act:` (suite, extensions) |
| `tools/Tools` | `riscv-tools`, whose `certify` command drives all of it |

The VHDL comes from sibling checkouts of
[Core](https://github.com/insper-riscv/Core) (`../Core`, the processor),
[Memory](https://github.com/insper-riscv/Memory) (`../Memory`, the memories) and
[RV32IM](https://github.com/insper-riscv/RV32IM) (`../RV32IM/src`, the simulation top).

## Run

```bash
git clone --recurse-submodules https://github.com/insper-riscv/Certification.git
git clone https://github.com/insper-riscv/Core.git     # next to it
git clone https://github.com/insper-riscv/Memory.git   # next to it
git clone https://github.com/insper-riscv/RV32IM.git   # next to it
cd Certification
uv sync
uv run riscv-tools --config tools/riscv_build/config.yaml certify
```

Needs the `infra-toolchain` image's tools (RISC-V GCC, Spike, GHDL) plus
`build-essential`, `device-tree-compiler` and [mise](https://mise.jdx.dev)
(Ruby/Bundler for ACT4's UDB); CI does exactly this in
`.github/workflows/certification.yml`.

## Scope and state

I and M only: the core has no CSR/trap/privilege support yet. Extensions
are added to `act.extensions` as the core grows them.

The build of the ACT4 ELFs currently fails at `rvmodel_macros.h` (macros
missing for this target). That failure predates this repository (it moved
here unchanged from `Testes`) and is the first thing to fix here.

## License

Apache License 2.0, see [LICENSE](LICENSE).
