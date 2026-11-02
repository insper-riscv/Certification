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
| `Insper-RISC-V/` | Submódulo com o núcleo, as memórias, os periféricos e os topos de simulação das plataformas, na versão que este repositório fixa |
| `tools/riscv_build/config.platform-*.yaml` | Configuração de cada plataforma (fontes VHDL, topo e mapa de memória), escrita por `riscv-tools platform sync` a partir do submódulo e nunca editada à mão |
| `tools/riscv_build/config.yaml` | Estende a plataforma `internal-mem` e acrescenta a seção `act:` (suíte e extensões); `config.profile-*.yaml` é a de cada perfil sem Zifencei, e `config.flash-*.yaml`, a de cada perfil com Zifencei |

O VHDL vem do submódulo [Insper-RISC-V](https://github.com/insper-riscv/Insper-RISC-V), que traz o `Core` (o processador), a `Memory` (as memórias), os `Peripherals` e os topos de simulação das plataformas. Os caminhos dos arquivos de configuração das plataformas começam por `Insper-RISC-V/`, a pasta do submódulo.

## 3. Escopo

A certificação cobre as extensões `I`, `M`, `Zmmul`, `Zicsr`, `Zicntr`, `Zihpm`, `Zifencei` e `Zicclsm`, listadas em `act.extensions` na configuração. Cada uma das 60 combinações válidas dessas extensões sobre a base `I`, lidas da matriz de perfis do Core (`profiles/matrix.yaml`), é um perfil do núcleo com seu próprio alvo, gerado por `tools/riscv_build/gen_profiles.py`; um perfil sem `Zifencei` roda com `riscv-tools --config tools/riscv_build/config.profile-<nome>.yaml certify` na plataforma `internal-mem`. Os perfis com `Zifencei` precisam das caches e rodam na plataforma `de0-cv`, com a FLASH atrás delas, por `tools/riscv_build/config.flash-<nome>.yaml`; os alvos `flash-ram-*` rodam o teste que reescreve o próprio código a partir da SDRAM.

## 4. Execução

```bash
git clone --recurse-submodules https://github.com/insper-riscv/Certification.git
cd Certification
uv sync
riscv-tools --config tools/riscv_build/config.yaml certify
```

As ferramentas vêm da imagem `ci-act4` do repositório [Infra](https://github.com/insper-riscv/Infra): GCC RISC-V, Spike, Sail, GHDL, uv e Ruby com Bundler e as gems do UDB do ACT4. O fluxo completo está em `.github/workflows/certification.yml`. A execução de todos os perfis, com um runner separado por perfil, está em `.github/workflows/certification-profiles.yml`; ela lê os arquivos `tools/riscv_build/config.profile-<nome>.yaml` e `tools/riscv_build/config.flash-<nome>.yaml` e aceita, no disparo manual, uma expressão regular sobre o nome do perfil.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](LICENSE).
