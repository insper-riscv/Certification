# Release da certificação

🌐 [Português](release.md) · [English](../../en/act4/release.md)

## 1. O que é publicado

Quando uma certificação passa por inteiro, o workflow publica um release do GitHub com os logs anexados. O release é o registro da certificação: os testes e as gems do ACT4 vêm da imagem `ghcr.io/insper-riscv/ci-act4:latest`, todos do mesmo commit do ACT4, e esse commit vai na descrição. Nada no repositório fixa a versão da suíte.

Um run que falha, em qualquer par (perfil, modelo de memória), não publica nada.

## 2. Quando o release sai

| Disparo | Workflow | O que é certificado | Título do release |
| :--- | :--- | :--- | :--- |
| Push na `main` | `certification` | A matriz mínima inteira. Se um pull request já certificou a mesma árvore, o resultado dele é reaproveitado. | A combinação validada, por exemplo `RV32 I/E M, Zmmul, Zicclsm, Zihintntl` |
| Manual | `certification` | A matriz mínima inteira | Data e hora em UTC, `AAAA-MM-DD HH:MM UTC, matriz` |
| Manual | `certification-profiles` | A matriz exaustiva, escolhida no disparo, com a chave `CERTIFICATION_RUN_SECRET` | Data e hora em UTC, `matriz` |
| Manual | `certification-profile` | Um perfil e um modelo de memória | Data e hora em UTC, `perfil <nome>` |

A tag é única, no formato `cert-AAAAMMDD-HHMMSS-<7 do commit>`, porque várias certificações podem ter o mesmo título.

## 3. O que a descrição traz

| Item | Conteúdo |
| :--- | :--- |
| Perfis | Todos os perfis testados na matriz, ou o único perfil do run manual de um perfil |
| ELFs por módulo | Quantos ELFs passaram em cada módulo (I, E, M, Zmmul, Zicsr, Zicntr, Zihpm, Zicclsm, Zifencei, Zimop, Zicond, Zihintntl, Zihintpause) |
| Memória | Para cada perfil, o modelo usado: ROM e RAM internas ou externas e se há cache de instruções e de dados |
| Versões | O commit do ACT4 da imagem, o commit do Insper-RISC-V e o commit da Certification |
| Run | O endereço do run que gerou o resultado, e o do run reaproveitado quando houve reuso |

O título automático lista só o que foi de fato validado: a base I ou E entra se ao menos um perfil dela passou, e os módulos entram na ordem canônica.

## 4. Os logs anexados

Cada perfil tem um arquivo `logs-<perfil>.tar.gz` com o `latest.log` da certificação e o veredito de cada ELF. Cada anexo tem menos de 2 GiB.

## 5. Como o resultado de um pull request é reaproveitado

O pull request roda a matriz mínima e, ao passar, sobe o artifact `ci-pass-act4-<chave>` com os resultados. A chave vem da ação `ci-plan` do Infra e inclui o digest da imagem `ci-act4`, então uma imagem nova, com outro commit do ACT4, nunca reaproveita o resultado de uma imagem antiga. No push na `main`, se a chave é a mesma, o job `act4` é pulado e o job `release` monta o release a partir desse resultado.

## 6. Cobertura

O job `plan` falha quando a união dos ELFs dos perfis planejados difere do conjunto de ELFs que o ACT4 gera para as extensões do núcleo nas bases I e E, ou quando `matrix.md` não traz os números da matriz. Os números de `matrix.md` são gerados por `tools/riscv_build/act_docs.py`.
