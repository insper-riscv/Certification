"""Confere se os perfis planejados cobrem todos os ELFs que o ACT4 gera para as extensões do núcleo.

Uso, da raiz do repositório e dentro da imagem `ci-act4`:

    uv run python tools/riscv_build/act_inventory.py check [--workers 4] [--summary ARQUIVO] [--json ARQUIVO]

O conjunto esperado vem do próprio ACT4 (`act --dry-run`, a seleção real de testes pelo UDB), sem o filtro
`EXTENSIONS` e com todas as extensões do núcleo ligadas, para cada base (I e E) e para cada variante de
multiplicação (M e Zmmul). O conjunto coberto é a união dos ELFs que cada perfil de `minimal_profiles.yaml`
gera com a lista de extensões que o `certify` realmente passa ao `make`. O comando falha quando

1. algum ELF esperado não está em nenhum perfil planejado, ou algum perfil gera um ELF que o conjunto esperado
   não tem;
2. o campo `tests` de um perfil do YAML difere do número de ELFs que o ACT4 gera para ele.

Um ELF é identificado por `<base>/<pasta>/<teste>` (por exemplo `rv32i/Zicclsm/Zicclsm-lh-00`). Os testes de
uma pasta que exigem extensões que o núcleo não tem (por exemplo `ZicclsmD-fld-00`, que exige o D) não são
selecionados pelo ACT4 e, portanto, não são esperados.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory_models
from memory_models import MemoryModel
from profile_params import (
    ACT4_DIR,
    EXTRAS,
    is_e,
    minimal_profiles,
    minimal_tests,
    variants,
)
from target_gen import write_generated

# O caminho de um ELF na saída do `act --dry-run`: work/<alvo>/elfs/<base>/<pasta>/<teste>.elf.
_ELF = re.compile(r"/elfs/(rv32[ei])/([^/\s]+)/([^/\s]+)\.elf")

# Os modelos de memória em que o alvo é gerado: a seleção de testes não depende deles, só o Zifencei exige o externo.
_INTERNAL = "rom=int,ram=int,icache=off,dcache=off"
_EXTERNAL = "rom=ext,ram=ext,icache=on,dcache=on"


def parse_elfs(output: str) -> set[str]:
    """Extrai os ELFs de uma saída do `act --dry-run`.

    Parameters
    ----------
    output : str
        A saída padrão do comando, com os caminhos dos ELFs sem quebra de linha no meio.

    Returns
    -------
    set of str
        Os ELFs, no formato `<base>/<pasta>/<teste>`.
    """
    return {"/".join(found) for found in _ELF.findall(output)}


def _model_for(ext: set[str]) -> MemoryModel:
    """Escolhe um modelo de memória que o perfil aceita, para gerar o alvo.

    Parameters
    ----------
    ext : set of str
        As extensões do perfil.

    Returns
    -------
    MemoryModel
        O modelo externo completo se o perfil tem Zifencei, o interno nos outros casos.
    """
    return memory_models.parse(_EXTERNAL if "Zifencei" in ext else _INTERNAL)


def act_elfs(root: Path, name: str, ext: set[str], *, filtered: bool, act_dir: Path = ACT4_DIR) -> set[str]:
    """Pergunta ao ACT4 quais ELFs ele gera para um perfil.

    Parameters
    ----------
    root : Path
        Raiz do repositório.
    name : str
        Nome do perfil; o prefixo `rv32e` escolhe a base E.
    ext : set of str
        As extensões do perfil.
    filtered : bool
        Com True, passa ao ACT4 a lista de extensões do `certify` (o que o job roda); com False, não passa
        filtro nenhum (tudo o que o UDB do perfil seleciona).
    act_dir : Path
        O checkout do ACT4.

    Returns
    -------
    set of str
        Os ELFs que o ACT4 gera.

    Raises
    ------
    RuntimeError
        Se o `act` termina com erro.
    """
    with tempfile.TemporaryDirectory(prefix="act-inventory-") as tmp:
        out = Path(tmp) / "target"
        config = write_generated(root, out, name, ext, _model_for(ext), 1)
        target_config = next((out / "act").glob("*/test_config.yaml"))
        command = ["uv", "run", "act", str(target_config), "--workdir", str(Path(tmp) / "work"), "--test-dir", "tests", "--jobs", "1", "--dry-run"]
        if filtered:
            extensions = re.search(r'extensions: "([^"]+)"', config.read_text())
            assert extensions is not None
            command += ["--extensions", extensions.group(1)]
        # O rich quebra as linhas na largura do terminal; uma largura enorme mantém cada caminho inteiro.
        done = subprocess.run(command, cwd=act_dir, capture_output=True, text=True, env={**os.environ, "COLUMNS": "100000"}, check=False)
    if done.returncode != 0:
        raise RuntimeError(f"act --dry-run of {name} failed:\n{done.stdout[-2000:]}\n{done.stderr[-2000:]}")
    return parse_elfs(done.stdout)


def full_extension_sets(root: Path) -> dict[str, set[str]]:
    """Monta, por base, os conjuntos com todas as extensões do núcleo ligadas.

    A matriz de perfis do Core e os extras da plataforma dão o universo de extensões. Há um conjunto com M e
    outro com Zmmul porque as duas são mutuamente exclusivas (o M implica o Zmmul).

    Parameters
    ----------
    root : Path
        Raiz do repositório.

    Returns
    -------
    dict of {str: set of str}
        O nome sintético do perfil (`rv32i_all_m`, `rv32i_all_zmmul`, `rv32e_all_m`, `rv32e_all_zmmul`) e as suas
        extensões.
    """
    universe = {e for _name, exts in variants(root) for e in exts} | set(EXTRAS)
    sets: dict[str, set[str]] = {}
    for base in ("rv32i", "rv32e"):
        sets[f"{base}_all_m"] = universe - {"Zmmul"}
        sets[f"{base}_all_zmmul"] = universe - {"M"}
    return sets


def compare(expected: set[str], covered: set[str]) -> list[str]:
    """Compara o conjunto esperado de ELFs com o coberto pelos perfis.

    Parameters
    ----------
    expected : set of str
        Os ELFs que o ACT4 gera para as extensões do núcleo.
    covered : set of str
        A união dos ELFs dos perfis planejados.

    Returns
    -------
    list of str
        Uma linha por problema; vazia quando os conjuntos são iguais.
    """
    found = [f"missing from every planned profile: {elf}" for elf in sorted(expected - covered)]
    found += [f"generated by a planned profile but not expected: {elf}" for elf in sorted(covered - expected)]
    return found


def check_counts(declared: dict[str, int], generated: dict[str, int]) -> list[str]:
    """Compara o campo `tests` de cada perfil do YAML com o número de ELFs que o ACT4 gera.

    Parameters
    ----------
    declared : dict of {str: int}
        O `tests` de cada perfil em `minimal_profiles.yaml`.
    generated : dict of {str: int}
        O número de ELFs que o ACT4 gera para cada perfil.

    Returns
    -------
    list of str
        Uma linha por perfil que difere.
    """
    return [
        f"{name}: minimal_profiles.yaml says tests: {declared[name]}, ACT4 generates {generated.get(name)}"
        for name in declared
        if generated.get(name) != declared[name]
    ]


def by_suite(elfs: set[str]) -> Counter[str]:
    """Conta os ELFs por base e pasta de testes.

    Parameters
    ----------
    elfs : set of str
        Os ELFs no formato `<base>/<pasta>/<teste>`.

    Returns
    -------
    Counter of str
        Contagem por `<base>/<pasta>`.
    """
    return Counter("/".join(elf.split("/")[:2]) for elf in elfs)


def _summary(expected: set[str], per_profile: dict[str, set[str]], covered: set[str]) -> str:
    """Escreve a tabela de cobertura em Markdown, para o resumo do job.

    Parameters
    ----------
    expected : set of str
        Os ELFs esperados.
    per_profile : dict of {str: set of str}
        Os ELFs de cada perfil planejado.
    covered : set of str
        A união dos ELFs dos perfis.

    Returns
    -------
    str
        O texto Markdown.
    """
    want, have = by_suite(expected), by_suite(covered)
    lines = [
        f"### ACT4 coverage: {len(covered)} of {len(expected)} expected ELFs",
        "",
        "| Suite | Expected | Covered |",
        "| :--- | ---: | ---: |",
    ]
    lines += [f"| `{suite}` | {want[suite]} | {have[suite]} |" for suite in sorted(want)]
    lines += ["", "| Profile | ELFs |", "| :--- | ---: |"]
    lines += [f"| `{name}` | {len(elfs)} |" for name, elfs in per_profile.items()]
    return "\n".join(lines) + "\n"


def run_check(root: Path, workers: int, act_dir: Path = ACT4_DIR) -> tuple[list[str], str, dict[str, object]]:
    """Calcula o inventário e o compara com os perfis planejados.

    Parameters
    ----------
    root : Path
        Raiz do repositório.
    workers : int
        Quantos `act --dry-run` rodam ao mesmo tempo.
    act_dir : Path
        O checkout do ACT4.

    Returns
    -------
    tuple of (list of str, str, dict)
        Os problemas, o resumo em Markdown e o inventário em formato JSON.
    """
    if any(is_e(name) for name, _ in minimal_profiles(root)):
        # O UDB publicado não declara a extensão E; o overlay a instala no gem (idempotente).
        subprocess.run(["sh", "tools/riscv_build/install_udb_overlay.sh"], cwd=root, check=True)
    planned = minimal_profiles(root)
    universe = full_extension_sets(root)
    jobs: list[tuple[str, set[str], bool]] = [(n, e, True) for n, e in planned] + [(n, e, False) for n, e in universe.items()]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda j: act_elfs(root, j[0], j[1], filtered=j[2], act_dir=act_dir), jobs))
    per_profile = {n: r for (n, _e, filtered), r in zip(jobs, results, strict=True) if filtered}
    expected: set[str] = set()
    for (_n, _e, filtered), r in zip(jobs, results, strict=True):
        if not filtered:
            expected |= r
    covered = set().union(*per_profile.values())
    problems = compare(expected, covered) + check_counts(minimal_tests(root), {n: len(r) for n, r in per_profile.items()})
    inventory = {
        "act4_dir": str(act_dir),
        "expected": sorted(expected),
        "profiles": {n: sorted(r) for n, r in per_profile.items()},
    }
    return problems, _summary(expected, per_profile, covered), inventory


def main() -> None:
    """Lê os argumentos, roda a conferência e sai com erro se algo diverge."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("mode", choices=("check",))
    parser.add_argument("--root", default=".", help="root of the repository")
    parser.add_argument("--workers", type=int, default=4, help="act --dry-run processes at the same time")
    parser.add_argument("--summary", help="file of the job summary of GitHub Actions")
    parser.add_argument("--json", help="file that receives the whole inventory")
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers is between 1 and 16")

    problems, text, inventory = run_check(Path(args.root).resolve(), args.workers)
    print(text)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as handle:
            handle.write(text)
    if args.json:
        Path(args.json).write_text(json.dumps(inventory, indent=1) + "\n", encoding="utf-8")
    if problems:
        sys.exit("ACT4 coverage check failed:\n  " + "\n  ".join(problems))


if __name__ == "__main__":
    main()
