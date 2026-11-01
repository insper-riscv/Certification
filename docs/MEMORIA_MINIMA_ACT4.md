# Memória mínima para certificar cada extensão no ACT4

## 1. Como os números foram obtidos

Cada teste do ACT4 vira um ELF com o código e as constantes na FLASH (ROM) e os dados, a pilha e as palavras do HTIF na SDRAM (RAM). A ROM de um teste é o tamanho das seções que o ELF coloca a partir de `0x20000000`. A RAM é o tamanho das seções de dados a partir de `0x40000000` somado à pilha de 4096 B que o `link.ld` reserva. As palavras do HTIF (`tohost`, `fromhost` e o buffer de `stdout`) ocupam cerca de 32 B acima desse bloco e não entram na conta.

Os valores vêm dos ELFs do perfil completo (`rv32im_zicclsm_zicntr_zihpm_zifencei`). O teste `Zifencei-fence.i-00` reescreve o próprio código e a FLASH ignora stores, então a linha dele usa a variante `flash-ram`, em que o corpo do teste fica na RAM.

O mínimo de uma extensão é o maior valor de ROM e o maior valor de RAM entre os testes dela, porque a memória precisa comportar o pior teste. Os dois máximos podem vir de testes diferentes. Os totais em KB usam 1 KB igual a 1000 B, arredondado para cima.

A BOOT_ROM da plataforma é uma região à parte, de 2 KB, e não entra nas tabelas.

## 2. Tabelas por extensão

### 2.1 I (base RV32I)

| Teste | ROM (B) | RAM (B) |
| :--- | ---: | ---: |
| `I-add-00` | 37664 | 42784 |
| `I-addi-00` | 33568 | 42560 |
| `I-and-00` | 37664 | 42784 |
| `I-andi-00` | 33568 | 42560 |
| `I-auipc-00` | 21280 | 16288 |
| `I-beq-00` | 58144 | 36848 |
| `I-bge-00` | 58144 | 36848 |
| `I-bgeu-00` | 58144 | 37104 |
| `I-blt-00` | 58144 | 36848 |
| `I-bltu-00` | 58144 | 37104 |
| `I-bne-00` | 58144 | 36848 |
| `I-fence-00` | 21280 | 31632 |
| `I-jal-00` | 131872 | 16112 |
| `I-jalr-00` | 33568 | 20480 |
| `I-lb-00` | 25376 | 20240 |
| `I-lbu-00` | 25376 | 20384 |
| `I-lh-00` | 25376 | 20000 |
| `I-lhu-00` | 25376 | 20144 |
| `I-lui-00` | 21280 | 16176 |
| `I-lw-00` | 25376 | 19888 |
| `I-nop-00` | 21280 | 12896 |
| `I-or-00` | 37664 | 42368 |
| `I-ori-00` | 33568 | 42192 |
| `I-sb-00` | 29472 | 19248 |
| `I-sh-00` | 29472 | 18976 |
| `I-sll-00` | 37664 | 42784 |
| `I-slli-00` | 25376 | 26960 |
| `I-slt-00` | 37664 | 43024 |
| `I-slti-00` | 33568 | 42688 |
| `I-sltiu-00` | 33568 | 43056 |
| `I-sltu-00` | 37664 | 43408 |
| `I-sra-00` | 37664 | 42784 |
| `I-srai-00` | 25376 | 26960 |
| `I-srl-00` | 37664 | 42784 |
| `I-srli-00` | 25376 | 26960 |
| `I-sub-00` | 37664 | 42784 |
| `I-sw-00` | 29472 | 18832 |
| `I-xor-00` | 37664 | 42784 |
| `I-xori-00` | 33568 | 42560 |

**Mínimo para certificar I:** ROM 131872 B (132 KB, teste `I-jal-00`) e RAM 43408 B (44 KB, teste `I-sltu-00`).

### 2.2 M

| Teste | ROM (B) | RAM (B) |
| :--- | ---: | ---: |
| `M-div-00` | 37664 | 42784 |
| `M-divu-00` | 37664 | 43168 |
| `M-mul-00` | 37664 | 42784 |
| `M-mulh-00` | 37664 | 43168 |
| `M-mulhsu-00` | 37664 | 43952 |
| `M-mulhu-00` | 37664 | 43568 |
| `M-rem-00` | 37664 | 42784 |
| `M-remu-00` | 37664 | 43168 |

**Mínimo para certificar M:** ROM 37664 B (38 KB, teste `M-div-00`) e RAM 43952 B (44 KB, teste `M-mulhsu-00`).

### 2.3 Zmmul

| Teste | ROM (B) | RAM (B) |
| :--- | ---: | ---: |
| `Zmmul-mul-00` | 37664 | 44352 |
| `Zmmul-mulh-00` | 37664 | 44736 |
| `Zmmul-mulhsu-00` | 37664 | 45520 |
| `Zmmul-mulhu-00` | 37664 | 45136 |

**Mínimo para certificar Zmmul:** ROM 37664 B (38 KB, teste `Zmmul-mul-00`) e RAM 45520 B (46 KB, teste `Zmmul-mulhsu-00`).

### 2.4 Zicsr

| Teste | ROM (B) | RAM (B) |
| :--- | ---: | ---: |
| `Zicsr-csrrc-00` | 29472 | 20496 |
| `Zicsr-csrrci-00` | 25376 | 17200 |
| `Zicsr-csrrs-00` | 29472 | 20496 |
| `Zicsr-csrrsi-00` | 25376 | 17200 |
| `Zicsr-csrrw-00` | 29472 | 20496 |
| `Zicsr-csrrwi-00` | 25376 | 17200 |

**Mínimo para certificar Zicsr:** ROM 29472 B (30 KB, teste `Zicsr-csrrc-00`) e RAM 20496 B (21 KB, teste `Zicsr-csrrc-00`).

### 2.5 Zicntr

| Teste | ROM (B) | RAM (B) |
| :--- | ---: | ---: |
| `Zicntr-csrrc-00` | 21280 | 13200 |
| `Zicntr-csrrs-00` | 21280 | 13200 |

**Mínimo para certificar Zicntr:** ROM 21280 B (22 KB, teste `Zicntr-csrrc-00`) e RAM 13200 B (14 KB, teste `Zicntr-csrrc-00`).

### 2.6 Zihpm

| Teste | ROM (B) | RAM (B) |
| :--- | ---: | ---: |
| `Zihpm-csrrc-00` | 21280 | 16960 |
| `Zihpm-csrrs-00` | 21280 | 16960 |

**Mínimo para certificar Zihpm:** ROM 21280 B (22 KB, teste `Zihpm-csrrc-00`) e RAM 16960 B (17 KB, teste `Zihpm-csrrc-00`).

### 2.7 Zicclsm

| Teste | ROM (B) | RAM (B) |
| :--- | ---: | ---: |
| `Zicclsm-lh-00` | 21280 | 15408 |
| `Zicclsm-lhu-00` | 21280 | 15440 |
| `Zicclsm-lw-00` | 21280 | 15392 |
| `Zicclsm-sh-00` | 21280 | 14416 |
| `Zicclsm-sw-00` | 21280 | 14400 |

**Mínimo para certificar Zicclsm:** ROM 21280 B (22 KB, teste `Zicclsm-lh-00`) e RAM 15440 B (16 KB, teste `Zicclsm-lhu-00`).

### 2.8 Zifencei

| Teste | ROM (B) | RAM (B) |
| :--- | ---: | ---: |
| `Zifencei-fence.i-00` | 864 | 29584 |

**Mínimo para certificar Zifencei:** ROM 864 B (1 KB, teste `Zifencei-fence.i-00`) e RAM 29584 B (30 KB, teste `Zifencei-fence.i-00`).

## 3. Resumo e maior par

| Extensão | Testes | ROM mínima | RAM mínima |
| :--- | ---: | ---: | ---: |
| I | 39 | 132 KB | 44 KB |
| M | 8 | 38 KB | 44 KB |
| Zmmul | 4 | 38 KB | 46 KB |
| Zicsr | 6 | 30 KB | 21 KB |
| Zicntr | 2 | 22 KB | 14 KB |
| Zihpm | 2 | 22 KB | 17 KB |
| Zicclsm | 5 | 22 KB | 16 KB |
| Zifencei | 1 | 1 KB | 30 KB |
| **Maior par (todas as extensões)** | 67 | **132 KB** | **46 KB** |

O maior par é 132 KB de ROM e 46 KB de RAM (131872 B e 45520 B). Qualquer memória com pelo menos esse par certifica todas as extensões do perfil completo.
