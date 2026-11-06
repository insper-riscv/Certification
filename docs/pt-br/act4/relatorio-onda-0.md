# Relatório do ACT4 da Onda 0

🌐 [Português](relatorio-onda-0.md) · [English](../../en/act4/relatorio-onda-0.md)

## 1. Versões usadas

| Item | Versão |
| :--- | :--- |
| Insper-RISC-V (submódulo) | tag `Onda-0`, commit `ae44830` |
| Insper-RISC-V executado | `422057f`, que difere da tag apenas pelo topo de síntese da placa DE0-CV (sem efeito no ACT4 nem nas simulações) |
| Core | `8a828cc` |
| Memory, Peripherals, Common-Components | `c71106f`, `d7253f6`, `9aa6a75` |
| riscv-arch-test (ACT4) | `bfe6155` |
| `riscv-tools` | 1.9.2, na imagem `ci-act4` |
| Modelo de referência | Sail RISC-V 0.16 |
| UDB | gem `udb` 0.1.18 |
| Simulador | GHDL 6.0.0 com cocotb |

## 2. Perfis executados

Cada perfil rodou em um contêiner da imagem `ci-act4` numa workstation distinta (três ao mesmo tempo), na plataforma modular de simulação. O número de ELFs é a soma dos testes das pastas de cada extensão declarada.

| Perfil | Extensões declaradas | Plataforma | ELFs | Resultado | Tempo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `profile-rv32i` (controle) | I | memórias no chip | 39 | 39 aprovados | 417 s |
| `profile-rv32im` | I, M, Zmmul | memórias no chip | 51 | 51 aprovados | 541 s |
| `flash-rv32im_zicclsm_zicntr_zihpm_zifencei` | I, M, Zmmul, Zicsr, Zicntr, Zihpm, Zifencei, Zicclsm | FLASH e RAM atrás das caches | 67 | 67 aprovados | 656 s |
| `adhoc-zimop` | I, Zimop | memórias no chip | 79 | 79 aprovados | 741 s |
| `adhoc-zicond` | I, Zicond | memórias no chip | 41 | 41 aprovados | 397 s |
| `adhoc-todas` | I, M, Zmmul, Zicsr, Zicntr, Zihpm, Zicclsm, Zimop, Zicond, Zihintntl, Zihintpause | memórias no chip | 113 | 113 aprovados | 1100 s |

Nenhum teste falhou nas execuções finais.

## 3. Cobertura por extensão

| Extensão | ELFs no `riscv-arch-test` em uso | Perfis que a cobrem |
| :--- | :--- | :--- |
| Zimop | 40 | `adhoc-zimop`, `adhoc-todas` |
| Zicond | 2 | `adhoc-zicond`, `adhoc-todas` |
| Zihpm | 2 | perfil Zihpm com Zifencei, `adhoc-todas` |
| Zihintntl | 4 | `adhoc-todas` |
| Zihintpause | 1 | `adhoc-todas` |
| M e Zmmul | 8 e 4 | `profile-rv32im` e os demais com M |

## 4. Perfis `adhoc`

A matriz do Core e os geradores `gen_profiles.py` e `gen_flash_profiles.py` não produzem perfis com Zimop, Zicond, Zihintntl nem Zihintpause, e a matriz não foi alterada. Os três perfis `adhoc` derivam de `profile-rv32i` e `profile-rv32im_zicclsm_zicntr_zihpm` com três mudanças.

1. O UDB do alvo declara a extensão nova (Zimop 1.0.0, Zicond 1.0.0, Zihintntl 1.0.0, Zihintpause 2.0.0).
2. O `sail.json` do alvo marca a extensão como `supported`.
3. O `sim.parameters` do config liga `HAS_<EXTENSÃO>` e a lista `act.extensions` ganha a extensão.

Para os generics chegarem ao núcleo, `act_modular_top` repassa `has_zimop`, `has_zicond`, `has_zihintntl` e `has_zihintpause` ao `modular_sim_top`.

## 5. Zihpm

Os perfis gerados declaram quatro contadores de evento (índices 3 a 6), todos de 64 bits, com os nove eventos do núcleo. O banco completo de 29 contadores não é declarado por nenhum perfil da matriz da Certification, então o ACT4 só exercita as duas provas de Zihpm da pasta do `riscv-arch-test`.

## 6. RV32E

Os perfis `rv32e*` e `rv32em*` precisam do overlay UDB `E.yaml`, instalado pelo passo `sh tools/riscv_build/install_udb_overlay.sh` do fluxo `certification-profiles.yml`. Nenhum perfil RV32E foi executado neste relatório.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
