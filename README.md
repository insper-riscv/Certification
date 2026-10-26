# Certification

🌐 [Português](README.md) · [English](README.en.md)

Certificação do núcleo RISC-V RV32IM com a suíte oficial ACT4 ([riscv-arch-test](https://github.com/riscv/riscv-arch-test)), executada em simulação (cocotb/GHDL). Este repositório roda a suíte contra o núcleo e reporta o resultado; nunca executa na placa.

## 1. Documentação

- [AUTHORS.md](AUTHORS.md): autores com commits no repositório, com nome e conta do GitHub.
- [CONTRIBUTING.md](CONTRIBUTING.md): regras obrigatórias de contribuição, normas C23 e Python, regras de documentação e verificação antes de abrir Pull Request.
- [CITATION.cff](CITATION.cff): metadados para citação do software.

## 2. Estrutura do Repositório

| Caminho | Conteúdo |
| :--- | :--- |
| `vendor/riscv-arch-test` | Suíte oficial, em versão fixada como submódulo |
| `tools/riscv_build/act/rv32im-min/` | Alvo do DUT: `test_config.yaml`, o YAML do UDB, `rvmodel_macros.h`, `link.ld` e `spike-rv32im-min` (Spike com o mapa de memória deste alvo, usado como modelo de referência) |
| `tools/riscv_build/act/sim/test_act.py` | Testbench cocotb que observa a palavra HTIF `tohost` |
| `tools/riscv_build/config.yaml` | Seção `sim:` (fontes VHDL e topo) e seção `act:` (suíte e extensões) |
| `tools/Tools` | Pacote `riscv-tools`, cujo comando `certify` conduz todo o fluxo |

O VHDL vem de repositórios irmãos clonados lado a lado: [Core](https://github.com/insper-riscv/Core) (`../Core`, o processador), [Memory](https://github.com/insper-riscv/Memory) (`../Memory`, as memórias) e [TopLevel](https://github.com/insper-riscv/TopLevel) (`../TopLevel`, o topo de simulação).

## 3. Escopo

A certificação cobre as extensões `I` e `M`, listadas em `act.extensions` na configuração.

## 4. Execução

```bash
git clone --recurse-submodules https://github.com/insper-riscv/Certification.git
git clone https://github.com/insper-riscv/Core.git      # ao lado
git clone https://github.com/insper-riscv/Memory.git    # ao lado
git clone https://github.com/insper-riscv/TopLevel.git  # ao lado
cd Certification
uv sync
uv run riscv-tools --config tools/riscv_build/config.yaml certify
```

São necessárias as ferramentas da imagem `infra-toolchain` (GCC RISC-V, Spike, GHDL), além de `build-essential`, `device-tree-compiler` e [mise](https://mise.jdx.dev) (Ruby/Bundler para o UDB do ACT4). O fluxo completo está em `.github/workflows/certification.yml`.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](LICENSE).
