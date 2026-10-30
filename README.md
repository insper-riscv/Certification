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
| `tools/riscv_build/act/rv32im-sdram/` | Alvo com o código e os dados na SDRAM, para as extensões que dependem dela (Zifencei) |
| `tools/riscv_build/act/profile-*/` | Um alvo por perfil do núcleo (UDB, configuração do Sail e `test_config.yaml`), gerado por `tools/riscv_build/gen_profiles.py` |
| `tools/riscv_build/act/sim/test_act.py` | Testbench cocotb que observa a palavra HTIF `tohost` |
| `tools/riscv_build/config.yaml` | Seção `sim:` (fontes VHDL e topo) e seção `act:` (suíte e extensões); `config.sdram.yaml` é a variante com a SDRAM e `config.profile-*.yaml`, a de cada perfil |
| `tools/Tools` | Pacote `riscv-tools`, cujo comando `certify` conduz todo o fluxo |

O VHDL vem de repositórios irmãos clonados lado a lado: [Core](https://github.com/insper-riscv/Core) (`../Core`, o processador), [Memory](https://github.com/insper-riscv/Memory) (`../Memory`, as memórias) e [TopLevel](https://github.com/insper-riscv/TopLevel) (`../TopLevel`, o topo de simulação).

## 3. Escopo

A certificação cobre as extensões `I`, `M`, `Zmmul`, `Zicsr` e `Zifencei`, listadas em `act.extensions` na configuração. Cada uma das 12 combinações dessas extensões sobre a base `I` é um perfil do núcleo, com seu próprio alvo; a lista está em `tools/riscv_build/gen_profiles.py`, e um perfil roda com `uv run riscv-tools --config tools/riscv_build/config.profile-<nome>.yaml certify`. Os perfis com `Zifencei` usam a plataforma com SDRAM.

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

As ferramentas vêm da imagem `ci-act4` do repositório [Infra](https://github.com/insper-riscv/Infra): GCC RISC-V, Spike, Sail, GHDL, uv e Ruby com Bundler e as gems do UDB do ACT4. O fluxo completo está em `.github/workflows/certification.yml`. A execução de todos os perfis, com um runner separado por perfil, está em `.github/workflows/certification-profiles.yml`; ela lê os arquivos `tools/riscv_build/config.profile-<nome>.yaml` e aceita, no disparo manual, a ramificação dos repositórios irmãos e uma expressão regular sobre o nome do perfil.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](LICENSE).
