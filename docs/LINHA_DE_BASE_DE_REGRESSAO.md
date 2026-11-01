# Linha de base de regressão

## 1. O que a linha de base registra

Cada tabela abaixo é o resultado de uma execução completa, nas imagens de CI (`ci-vhdl`, `ci-elf` e `ci-act4`) com o `riscv-tools` instalado nelas, e na placa DE0-CV para a parte de hardware. A linha de base serve de comparação para qualquer mudança: um resultado pior que o da tabela é regressão.

| Camada | Onde roda | Seção |
| :--- | :--- | :--- |
| Testes de entidade (cocotb e GHDL) | Cada repositório VHDL, `make test` | 2 |
| Provas formais (SymbiYosys e z3) | Core e Memory | 3 |
| Programas de teste em simulação | Repositório Tests, plataformas `internal-mem`, `sdram`, `sdram-axi` e `sdram-flash` | 4 |
| ACT4 (`riscv-arch-test`) | Repositório Certification, simulação e placa | 5 |
| Tempo e área | Quartus 25.1, projeto da plataforma `sdram-flash` | 6 |

## 2. Testes de entidade

| Repositório | Testes que passam | Testes que falham |
| :--- | ---: | ---: |
| Core | 180 | 0 |
| Memory | 145 | 0 |
| Peripherals | 37 | 0 |
| Common-Components | 29 | 0 |
| TopLevel (`clk_gen_3way` e as 4 plataformas SDRAM) | 13 | 0 |

## 3. Provas formais

| Prova | Resultado | Tempo |
| :--- | :--- | ---: |
| Core: banco de CSRs, unidade de traps, contadores, registro da fusão, com os mutantes | Todas as expectativas cumpridas | 2 min 58 s |
| Memory: pontes AXI4, mestre | Todas as expectativas cumpridas | 107 s |
| Memory: pontes AXI4, escravo | Todas as expectativas cumpridas | 885 s |
| Memory: árbitro da SDRAM | **Falha**: a prova de segurança por k-indução e o limite de 20 ciclos de resposta dão FAIL onde se espera PASS, e o mutante `rdata_swap_i` não altera o arquivo | 2 s |
| Peripherals, Common-Components e TopLevel | Sem provas | n/a |

## 4. Programas de teste em simulação

| Configuração | Plataforma | Programas | Passam | Falham |
| :--- | :--- | ---: | ---: | :--- |
| `config.yaml` | `internal-mem` | 119 | 119 | nenhum |
| `config.sdram.yaml` | `sdram` | 17 | 14 | `cpi-kernels`, `hex-id`, `flash-const` |
| `config.sdram-regression.yaml` | `sdram` | 119 | 116 | `uart-echo`, `uart-errors`, `uart-tx` |
| `config.sdram-axi.yaml` | `sdram-axi` | 119 | 115 | `stdout-truncate`, `uart-echo`, `uart-errors`, `uart-tx` |
| `config.sdram-flash-regression.yaml` | `sdram-flash`, latência padrão do chip (24 e 4 bordas) | 116 | 116 | nenhum |
| `config.sdram-flash-regression-lat2.yaml` | `sdram-flash`, chip de 2 bordas | 116 | 116 | nenhum |
| `config.sdram-flash-regression-lat20.yaml` | `sdram-flash`, chip de 20 bordas | 116 | 116 | nenhum |
| `config.sdram-flash-regression-lat60.yaml` | `sdram-flash`, chip de 60 bordas | 116 | 116 | nenhum |
| `config.sdram-flash.yaml` | `sdram-flash`, programas da plataforma | 15 | 15 | nenhum |
| `config.sdram-flash-lat2.yaml`, `-lat20.yaml` e `-lat60.yaml` | `sdram-flash`, programas da plataforma | 15 cada | 15 cada | nenhum |

### 4.1. Falhas que a linha de base já contém

| Programa | Configurações | Causa |
| :--- | :--- | :--- |
| `cpi-kernels` e `hex-id` | `sdram` | Medem e imprimem pela UART do host, o que só existe na placa; a simulação da plataforma `sdram` não os executa |
| `flash-const` | `sdram` | Lê constantes da FLASH externa, que a plataforma `sdram` não tem |
| `uart-echo`, `uart-errors` e `uart-tx` | `sdram`, `sdram-axi` | Falham nas simulações das plataformas SDRAM com ou sem a unidade de fusão de multiplicação e divisão; a causa não foi investigada |
| `stdout-truncate` | `sdram-axi` | Esgota o limite de 600 000 ciclos sem sinalizar PASS ou FAIL |

## 5. ACT4

| Perfil | Onde | Testes | Passam | Falham |
| :--- | :--- | ---: | ---: | ---: |
| `rv32im_zicclsm_zicntr_zihpm_zifencei` | Simulação, FLASH atrás das caches | 67 | 67 | 0 |
| `rv32i_zicclsm_zicntr_zihpm_zifencei_zmmul` | Simulação, FLASH atrás das caches | 59 | 59 | 0 |
| `rv32im_zicclsm_zicntr_zihpm_zifencei` | Placa DE0-CV | 67 | 67 | 0 |

Os 67 testes do perfil completo incluem o `Zifencei-fence.i-00`, que roda da variante com o corpo do teste na SDRAM. O alvo normal dele falha por projeto, porque a FLASH ignora escritas.

## 6. Tempo e área

| Medida | Valor |
| :--- | :--- |
| Folga do domínio do núcleo a 50 MHz (modelo lento a 85 °C, semente 5 do Quartus) | +0,095 ns |
| Folga do relógio da SDRAM (`DRAM_CLK_pin`) | -0,041 ns |
| ALMs | 5 561 de 18 480 (30 %) |
| Registradores | 7 052 |
| Bits de memória de bloco | 1 171 456 de 3 153 920 (37 %) |

Com a semente 1 o núcleo fica em -0,187 ns, e as sementes 2, 3 e 4 dão -0,348, -0,321 e -1,078 ns, então a semente faz parte da configuração que fecha o tempo.
