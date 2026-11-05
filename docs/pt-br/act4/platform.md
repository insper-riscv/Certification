# Plataforma de simulação do ACT4

🌐 [Português](platform.md) · [English](../../en/act4/platform.md)

## 1. O que roda

Os 120 perfis da matriz do Core (`Insper-RISC-V/Core/profiles/matrix.yaml`) rodam na plataforma modular de simulação do Insper-RISC-V (`src/simulation/modular`). O topo que o cocotb simula é `act_modular_top` (`tools/riscv_build/act/sim/`), que dá ao topo modular as portas observadas pelos testbenches.

| Grupo | Perfis | Modelo | ROM | RAM | Testbench |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Sem Zifencei | 60 | `integrated` | 1 MB dentro do chip | 1 MB dentro do chip | `test_act.py` observa o barramento de escrita da RAM |
| Com Zifencei | 60 | `external` | 1 MB atrás da cache de instruções de 4 kbit | 1 MB atrás da cache de dados de 4 kbit | `test_act_sdram.py` lê o `tohost` do chip de RAM pela porta de depuração |

## 2. Mapa de memória

| Região | Início | Tamanho |
| :--- | :--- | :--- |
| BOOT_ROM | `0x00000000` | 4 KB |
| ROM | `0x00001000` | 1 MB menos 4 KB |
| RAM | `0x00100000` | 1 MB |

As três palavras do HTIF ficam no fim da RAM, em `0x001FFFE0` (`tohost`), `0x001FFFE8` (`fromhost`) e `0x001FFFF0` (console). O ELF de cada teste carrega cada seção no endereço em que ela executa. Os primeiros 4 KB do ELF são a BOOT_ROM, com um trecho que salta para `0x00001000`, e o restante do código é a ROM. Nos perfis com Zifencei, o teste `Zifencei-fence.i-00` reescreve o próprio código e usa a variante `flash-ram`, com o corpo do teste na RAM.

## 3. Arquivos gerados

| Arquivo | Gerador |
| :--- | :--- |
| `tools/riscv_build/config.platform-*.yaml` | `riscv-tools platform sync`, a partir do submódulo |
| `tools/riscv_build/config.modular.yaml` | `gen_profiles.py`, com as fontes de `config.platform-de0-cv.yaml` |
| `tools/riscv_build/act/profile-*/` e `config.profile-*.yaml` | `gen_profiles.py`, um por perfil da matriz |
| `tools/riscv_build/act/flash-*/`, `act/flash-ram-*/` e `config.flash-*.yaml` | `gen_flash_profiles.py`, um por perfil com Zifencei |

Os perfis de base RV32E (`rv32e*` e `rv32em*`) usam `isa.base: e`, o genérico `HAS_E` e o ABI `ilp32e`. O UDB publicado não declara a extensão `E`, então o UDB desses perfis traz `arch_overlay: rv32e`, e `sh tools/riscv_build/install_udb_overlay.sh` instala em `ci-act4` a pasta `tools/riscv_build/act/udb-overlay` com essa extensão antes do `certify`.

## 4. Como rodar um perfil

```bash
uv sync
riscv-tools --config tools/riscv_build/config.profile-rv32im_zicsr.yaml certify
```

A execução precisa do limite de pilha elevado, que o `certify` ajusta, e de cerca de 6 GiB de RAM por simulação. O resultado fica em `logs/certification/latest.log`.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
