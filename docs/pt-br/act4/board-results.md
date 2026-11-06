# ACT4 na placa DE0-CV

🌐 [Português](board-results.md) · [English](../../en/act4/board-results.md)

## 1. Condições

| Item | Valor |
| :--- | :--- |
| Perfil | `rv32im_full_zifencei`: I, M, Zmmul, Zicsr, Zicntr, Zihpm, Zifencei, Zicclsm, Zimop, Zicond, Zihintntl e Zihintpause |
| Bitstream | `de0-cv.sof` do Insper-RISC-V `ceea999` (FLASH de duas portas regravada pelo carregador JTAG, controlador de FLASH e PLIC no topo), clock do núcleo de 50 MHz |
| ACT4 | `riscv-arch-test` fixado em `vendor/`, Sail como modelo de referência |
| Placas | notebook e PC1 em paralelo, ELFs repartidos por `--part 0/2` e `1/2` |

## 2. Alvo da placa

O alvo da placa (`gen_profiles.py --profile rv32im_full_zifencei --board --out build/target`) é o da plataforma modular com o mapa da DE0-CV. O código e as constantes ficam na FLASH a partir de `0x1200`, depois da página de cabeçalho da banca A e do payload de duas instruções que salta para o teste, e os dados, a pilha e o HTIF ficam na SDRAM em `0x40000000`. A memória de boot só executa uma banca com cabeçalho válido, e por isso o host escreve o cabeçalho, o payload e o ELF numa só imagem. O `Zifencei-fence.i-00` roda da variante com o corpo do teste na SDRAM.

## 3. Resumo

114 de 114 ELFs passaram, 57 em cada placa.

## 4. Veredito por ELF

| ELF | Placa | Veredito |
| :--- | :--- | :--- |
| `I-add-00` | notebook | PASS |
| `I-addi-00` | PC1 | PASS |
| `I-and-00` | notebook | PASS |
| `I-andi-00` | PC1 | PASS |
| `I-auipc-00` | notebook | PASS |
| `I-beq-00` | PC1 | PASS |
| `I-bge-00` | notebook | PASS |
| `I-bgeu-00` | PC1 | PASS |
| `I-blt-00` | notebook | PASS |
| `I-bltu-00` | PC1 | PASS |
| `I-bne-00` | notebook | PASS |
| `I-fence-00` | PC1 | PASS |
| `I-jal-00` | notebook | PASS |
| `I-jalr-00` | PC1 | PASS |
| `I-lb-00` | notebook | PASS |
| `I-lbu-00` | PC1 | PASS |
| `I-lh-00` | notebook | PASS |
| `I-lhu-00` | PC1 | PASS |
| `I-lui-00` | notebook | PASS |
| `I-lw-00` | PC1 | PASS |
| `I-nop-00` | notebook | PASS |
| `I-or-00` | PC1 | PASS |
| `I-ori-00` | notebook | PASS |
| `I-sb-00` | PC1 | PASS |
| `I-sh-00` | notebook | PASS |
| `I-sll-00` | PC1 | PASS |
| `I-slli-00` | notebook | PASS |
| `I-slt-00` | PC1 | PASS |
| `I-slti-00` | notebook | PASS |
| `I-sltiu-00` | PC1 | PASS |
| `I-sltu-00` | notebook | PASS |
| `I-sra-00` | PC1 | PASS |
| `I-srai-00` | notebook | PASS |
| `I-srl-00` | PC1 | PASS |
| `I-srli-00` | notebook | PASS |
| `I-sub-00` | PC1 | PASS |
| `I-sw-00` | notebook | PASS |
| `I-xor-00` | PC1 | PASS |
| `I-xori-00` | notebook | PASS |
| `M-div-00` | PC1 | PASS |
| `M-divu-00` | notebook | PASS |
| `M-mul-00` | PC1 | PASS |
| `M-mulh-00` | notebook | PASS |
| `M-mulhsu-00` | PC1 | PASS |
| `M-mulhu-00` | notebook | PASS |
| `M-rem-00` | PC1 | PASS |
| `M-remu-00` | notebook | PASS |
| `Zicclsm-lh-00` | PC1 | PASS |
| `Zicclsm-lhu-00` | notebook | PASS |
| `Zicclsm-lw-00` | PC1 | PASS |
| `Zicclsm-sh-00` | notebook | PASS |
| `Zicclsm-sw-00` | PC1 | PASS |
| `Zicntr-csrrc-00` | notebook | PASS |
| `Zicntr-csrrs-00` | PC1 | PASS |
| `Zicond-czero.eqz-00` | notebook | PASS |
| `Zicond-czero.nez-00` | PC1 | PASS |
| `Zicsr-csrrc-00` | notebook | PASS |
| `Zicsr-csrrci-00` | PC1 | PASS |
| `Zicsr-csrrs-00` | notebook | PASS |
| `Zicsr-csrrsi-00` | PC1 | PASS |
| `Zicsr-csrrw-00` | notebook | PASS |
| `Zicsr-csrrwi-00` | PC1 | PASS |
| `Zifencei-fence.i-00` | notebook | PASS |
| `Zihintntl-ntl.all-00` | PC1 | PASS |
| `Zihintntl-ntl.p1-00` | notebook | PASS |
| `Zihintntl-ntl.pall-00` | PC1 | PASS |
| `Zihintntl-ntl.s1-00` | notebook | PASS |
| `Zihintpause-pause-00` | PC1 | PASS |
| `Zihpm-csrrc-00` | notebook | PASS |
| `Zihpm-csrrs-00` | PC1 | PASS |
| `Zimop-mop.r.0-00` | notebook | PASS |
| `Zimop-mop.r.1-00` | PC1 | PASS |
| `Zimop-mop.r.10-00` | notebook | PASS |
| `Zimop-mop.r.11-00` | PC1 | PASS |
| `Zimop-mop.r.12-00` | notebook | PASS |
| `Zimop-mop.r.13-00` | PC1 | PASS |
| `Zimop-mop.r.14-00` | notebook | PASS |
| `Zimop-mop.r.15-00` | PC1 | PASS |
| `Zimop-mop.r.16-00` | notebook | PASS |
| `Zimop-mop.r.17-00` | PC1 | PASS |
| `Zimop-mop.r.18-00` | notebook | PASS |
| `Zimop-mop.r.19-00` | PC1 | PASS |
| `Zimop-mop.r.2-00` | notebook | PASS |
| `Zimop-mop.r.20-00` | PC1 | PASS |
| `Zimop-mop.r.21-00` | notebook | PASS |
| `Zimop-mop.r.22-00` | PC1 | PASS |
| `Zimop-mop.r.23-00` | notebook | PASS |
| `Zimop-mop.r.24-00` | PC1 | PASS |
| `Zimop-mop.r.25-00` | notebook | PASS |
| `Zimop-mop.r.26-00` | PC1 | PASS |
| `Zimop-mop.r.27-00` | notebook | PASS |
| `Zimop-mop.r.28-00` | PC1 | PASS |
| `Zimop-mop.r.29-00` | notebook | PASS |
| `Zimop-mop.r.3-00` | PC1 | PASS |
| `Zimop-mop.r.30-00` | notebook | PASS |
| `Zimop-mop.r.31-00` | PC1 | PASS |
| `Zimop-mop.r.4-00` | notebook | PASS |
| `Zimop-mop.r.5-00` | PC1 | PASS |
| `Zimop-mop.r.6-00` | notebook | PASS |
| `Zimop-mop.r.7-00` | PC1 | PASS |
| `Zimop-mop.r.8-00` | notebook | PASS |
| `Zimop-mop.r.9-00` | PC1 | PASS |
| `Zimop-mop.rr.0-00` | notebook | PASS |
| `Zimop-mop.rr.1-00` | PC1 | PASS |
| `Zimop-mop.rr.2-00` | notebook | PASS |
| `Zimop-mop.rr.3-00` | PC1 | PASS |
| `Zimop-mop.rr.4-00` | notebook | PASS |
| `Zimop-mop.rr.5-00` | PC1 | PASS |
| `Zimop-mop.rr.6-00` | notebook | PASS |
| `Zimop-mop.rr.7-00` | PC1 | PASS |
| `Zmmul-mul-00` | notebook | PASS |
| `Zmmul-mulh-00` | PC1 | PASS |
| `Zmmul-mulhsu-00` | notebook | PASS |
| `Zmmul-mulhu-00` | PC1 | PASS |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
