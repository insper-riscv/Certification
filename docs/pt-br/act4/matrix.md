# Matriz de certificação: perfis e modelos de memória

🌐 [Português](matrix.md) · [English](../../en/act4/matrix.md)

## 1. O que a matriz cruza

Cada job de certificação é um par (perfil, modelo de memória). O perfil é um conjunto de extensões do núcleo, como `rv32im_zicntr`. O modelo de memória diz onde ficam a ROM e a RAM da plataforma modular de simulação e quais caches existem. O alvo ACT4 do par (UDB, configuração do Sail, `test_config.yaml`, linker e o config do `certify`) é gerado em tempo de execução e nunca é versionado; os 154 configs versionados de `tools/riscv_build` continuam sendo o que os geradores escrevem, e o CI confere que a geração reproduz o que está commitado.

## 2. Os 16 modelos e os 4 que o topo aceita

A escolha tem quatro eixos, na sintaxe `--memory` do `riscv-tools`.

| Eixo | Valores |
| :--- | :--- |
| `rom` | `int` (dentro do chip) ou `ext` (chip de FLASH simulado) |
| `ram` | `int` ou `ext` (chip de RAM simulado) |
| `icache` | `on` ou `off` |
| `dcache` | `on` ou `off` |

Eles dão $2^4 = 16$ combinações. O topo `modular_sim_top` do Insper-RISC-V instancia a cache de instruções apenas no ramo da ROM externa e a de dados apenas no ramo da RAM externa, e não declara os genéricos `HAS_ICACHE` e `HAS_DCACHE`. Por isso a cache existe se, e somente se, a memória que ela serve é externa:

$$\text{icache} \iff \text{rom} = \text{ext}, \qquad \text{dcache} \iff \text{ram} = \text{ext}$$

Sobram 4 combinações aceitas, as arquiteturas `A` (ROM e RAM internas), `B` (ROM interna e RAM externa com cache de dados), `C` (ROM externa com cache de instruções e RAM interna) e `D` (as duas externas, com as duas caches); são os modelos `integrated`, `external-data`, `external-instruction` e `external` do topo. O GHDL confirma: ao elaborar `act_modular_top` com `ROM_EXTERNAL` e `RAM_EXTERNAL` nos quatro valores, a elaboração chega à carga das imagens de memória; ao pedir `HAS_ICACHE` ou `HAS_DCACHE`, ela termina com `cannot find in top entity generic`.

| `rom` | `ram` | `icache` | `dcache` | Aceita | Motivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `int` | `int` | `off` | `off` | sim | Modelo integrado: as duas memórias respondem sem espera, e o testbench observa o barramento de escrita da RAM. |
| `int` | `ext` | `off` | `on` | sim | Dados externos: a cache de dados fica entre o núcleo e o chip de RAM, e o testbench lê o `tohost` do chip pela porta de depuração. |
| `ext` | `int` | `on` | `off` | sim | Instruções externas: a cache de instruções fica entre o núcleo e o chip de FLASH. |
| `ext` | `ext` | `on` | `on` | sim | Modelo externo: as duas caches, um roteador por cache e um árbitro para o chip de FLASH. |
| `int` | qualquer | `on` | qualquer | não | A cache de instruções não existe sobre uma ROM interna. |
| qualquer | `int` | qualquer | `on` | não | A cache de dados não existe sobre uma RAM interna. |
| `ext` | qualquer | `off` | qualquer | não | O chip de FLASH fala o protocolo de linha da cache, e o topo não tem genérico para tirá-la. |
| qualquer | `ext` | qualquer | `off` | não | O chip de RAM fala o protocolo de linha da cache, e o topo não tem genérico para tirá-la. |

O comando de geração (seção 4) rejeita cada uma das 12 combinações recusadas e diz a razão. Uma cache sobre memória interna só adiciona latência e bloqueios, porque a memória já responde sem espera; essa combinação é válida para o `riscv-tools`, mas nenhum topo de simulação a monta.

### 2.1. Restrição do Zifencei

O teste `Zifencei-fence.i-00` reescreve o próprio código, então o corpo dele executa a partir da RAM. A busca de instruções só alcança a RAM pela cache de instruções, e a escrita só chega a ela pela cache de dados. Um perfil com Zifencei roda, portanto, apenas no modelo com as duas memórias externas e as duas caches. Nos outros três modelos o par é recusado.

## 3. Perfis mínimos

`tools/riscv_build/minimal_profiles.yaml` lista, para cada pasta de testes do ACT4 que o núcleo implementa, o menor perfil cujas extensões contêm o `REQUIRED_EXTENSIONS` dos testes da pasta, mais os perfis com tudo junto de cada base. As pastas vêm do checkout do ACT4 da imagem `ci-act4`, o mesmo commit das gems do UDB.

<!-- gen:table -->
| Perfil | Extensões acrescentadas à base | Pasta de testes | Testes | Jobs |
| :--- | :--- | :--- | ---: | ---: |
| `rv32i` | nenhuma | `rv32i/I` | 39 | 4 |
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
| `rv32e` | nenhuma | `rv32e/E` | 39 | 4 |
| `rv32em` | M | `rv32e/M` | 51 | 4 |
| `rv32e_zmmul` | Zmmul | `rv32e/Zmmul` | 43 | 4 |
| `rv32im_full` | M, Zicclsm, Zicntr, Zihpm, Zimop, Zicond, Zihintntl, Zihintpause | todas as pastas da base juntas | 113 | 4 |
| `rv32im_full_zifencei` | M, Zicclsm, Zicntr, Zihpm, Zifencei, Zimop, Zicond, Zihintntl, Zihintpause | todas as pastas da base juntas | 114 | 1 |
| `rv32em_full` | M, Zicclsm, Zicntr, Zihpm, Zimop, Zicond, Zihintntl, Zihintpause | todas as pastas da base juntas | 51 | 4 |
| `rv32em_full_zifencei` | M, Zicclsm, Zicntr, Zihpm, Zifencei, Zimop, Zicond, Zihintntl, Zihintpause | todas as pastas da base juntas | 51 | 1 |
<!-- /gen -->

A contagem de testes é a dos ELFs que o ACT4 gera para o perfil, isto é, a dos arquivos cujo `REQUIRED_EXTENSIONS` o perfil cobre, incluindo os das extensões que ele implica. Os perfis `rv32i_zicntr` e `rv32i_zihpm` incluem o Zicsr porque os contadores são CSRs. O Zmmul tem perfil próprio porque é a variante de RTL que multiplica sem dividir. Zimop, Zicond, Zihintntl e Zihintpause não fazem parte da matriz de perfis do Core; o núcleo as liga por genéricos do topo (`HAS_ZIMOP`, `HAS_ZICOND`, `HAS_ZIHINTNTL`, `HAS_ZIHINTPAUSE`), e o gerador as aceita no conjunto de extensões do perfil.

<!-- gen:total -->
Os perfis `rv32i_zifencei`, `rv32im_full_zifencei` e `rv32em_full_zifencei` rodam em um só modelo cada (seção 2.1); os outros 15 rodam nos 4. O total do workflow automático é, portanto:

$$15 \times 4 + 3 \times 1 = 63 \text{ jobs}$$
<!-- /gen -->

## 4. Gerar o alvo em tempo de execução

```bash
uv run python tools/riscv_build/gen_profiles.py \
    --profile rv32i_zimop \
    --memory rom=ext,ram=int,icache=on,dcache=off \
    --out build/target --jobs 4
riscv-tools --config build/target/config.yaml certify
```

| Opção | Efeito |
| :--- | :--- |
| `--profile` | Nome de um perfil da matriz do Core ou de `minimal_profiles.yaml`. |
| `--memory` | Modelo de memória, com as quatro chaves. Uma combinação que o topo não aceita, ou que o perfil não pode usar, termina o comando com a razão. |
| `--out` | Pasta que recebe `act/<alvo>/` e `config.yaml`. Dentro do repositório, ou em um caminho absoluto. |
| `--jobs` | Valor de `act.jobs`, que o `certify` repassa ao `make` do ACT4 como `JOBS=`. Zero deixa o ACT4 escolher. As simulações do `certify` rodam uma por vez. |

O alvo de um perfil (UDB, `sail.json`, `test_config.yaml` e linker) não depende do modelo de memória, porque o mapa é o mesmo nos quatro modelos. O que muda é o `config.yaml`.

| Modelo da RAM | Imagens | Testbench |
| :--- | :--- | :--- |
| `int` | Três imagens: BOOT_ROM, ROM e RAM | `test_act.py`, que observa o barramento de escrita da RAM do núcleo |
| `ext` | Imagem da FLASH e imagem do chip de RAM (`flash_base` e `sdram_base`) | `test_act_sdram.py`, que lê o `tohost` do chip pela porta de depuração |

Os genéricos `ROM_EXTERNAL` e `RAM_EXTERNAL` do `act_modular_top` acompanham o modelo. Um perfil com Zifencei ganha também o alvo `-ram`, com o corpo do teste na RAM, e o `config.yaml` o declara em `ram_tests`. Os perfis de base RV32E precisam do overlay do UDB (`sh tools/riscv_build/install_udb_overlay.sh`) antes do `certify`.

`tools/riscv_build/act_matrix.py` monta e imprime a matriz dos workflows, com os pares deixados de fora e o motivo de cada um.

## 5. Workflows

| Workflow | Disparo | Cruza | Controles |
| :--- | :--- | :--- | :--- |
| `certification (ACT4)` | `pull_request`, `push` na `main` | Os <!-- gen:profiles -->18<!-- /gen --> perfis mínimos com os modelos aceitos (<!-- gen:jobs -->63<!-- /gen --> jobs) | `max-parallel` de 16, `concurrency` por ramo, `act.jobs` de 4 |
| `certification (ACT4, all profiles and memory models)` | Manual, com chave | Todos os perfis (os 120 de referência da matriz do Core, sem Zimop e Zicond, e os mínimos) com os modelos aceitos | `confirmation` (valor do segredo `CERTIFICATION_RUN_SECRET`), `target`, `jobs`, `max-parallel`, `memory`, `only` |
| `certification (ACT4, one profile and memory model)` | Manual | Um perfil e um modelo | `profile`, `memory`, `target`, `jobs` |

A entrada `target` vale `simulated` (GHDL em runners do GitHub) ou `real` (a placa DE0-CV, em um runner self-hosted). O valor `real` termina o workflow com uma mensagem, porque o runner da placa não está configurado. Todas as entradas chegam ao shell por variáveis de ambiente e passam por uma lista branca de caracteres antes do uso, e o job `plan` imprime a matriz no log e no resumo do job antes de qualquer simulação.

## 6. Dimensionamento

Cada job simula os testes do perfil um a um, e cada teste reanalisa o VHDL antes de simular.

| Perfil | Arquitetura | Testes | Tempo | RAM de pico | Estação |
| :--- | :--- | ---: | ---: | ---: | :--- |
| `rv32i_zicntr` | `A` | 47 | 488 s | 5,9 GiB | workstation3 |
| `rv32i_zicclsm` | `D` | 44 | 409 s | 3,0 GiB | workstation4 |
| `rv32i_zifencei` | `D` | 40 | 394 s | 3,0 GiB | workstation2 |
| `rv32im_full` | `B` | 113 | 894 s | 3,0 GiB | workstation2 |
| `rv32i_zimop` | `C` | 79 | 810 s | 5,9 GiB | workstation3 |
| `rv32e` | `C` | 39 | 440 s | 5,9 GiB | workstation4 |

A tabela traz pares rodados com `--jobs 6` em contêineres de 6 CPUs, cada um com a imagem `ci-act4`; todos os testes passaram. O tempo é de parede, e a RAM de pico é a do maior processo da simulação. Com a RAM interna (arquiteturas `A` e `C`) o pico é de 5,9 GiB, e com a RAM externa (`B` e `D`) de 3,0 GiB. Um teste leva de 8 a 10 s, quase todo na análise do VHDL.

Os <!-- gen:jobs -->63<!-- /gen --> jobs do workflow automático somam <!-- gen:runs -->3289<!-- /gen --> execuções de teste, cerca de <!-- gen:hours -->9<!-- /gen --> horas de simulação, sem contar o checkout recursivo, o `uv sync` e a geração dos ELFs. Com `max-parallel` de 16 a estimativa para a certificação é da ordem de <!-- gen:wall -->1<!-- /gen --> h, e o maior job leva cerca de 15 minutos de simulação (<!-- gen:largest -->`rv32im_full_zifencei`<!-- /gen -->, com <!-- gen:largest_tests -->114<!-- /gen --> testes). O testbench da RAM interna espera até 8 milhões de ciclos pelo `tohost`, porque a ROM externa atrás da cache de instruções multiplica a duração dos testes longos. O limite de memória de um runner padrão do GitHub (16 GiB) comporta qualquer job.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
