"""Escreve e confere os números de `docs/<idioma>/act4/matrix.md` a partir de `minimal_profiles.yaml`.

Uso, da raiz do repositório:

    uv run python tools/riscv_build/act_docs.py write    # reescreve os trechos gerados dos dois idiomas
    uv run python tools/riscv_build/act_docs.py check    # falha se algum trecho difere do que `write` escreveria

Os trechos gerados ficam entre `<!-- gen:NOME -->` e `<!-- /gen -->` (a tabela dos perfis, a fórmula do total de
jobs e os números do dimensionamento). O resto do texto é escrito à mão. A contagem de jobs usa a mesma função
que o job `plan` usa para montar a matriz (`act_matrix`), então a documentação e o workflow não divergem; a
contagem de ELFs por perfil é o campo `tests` do YAML, que `act_inventory.py check` confere contra o ACT4.
"""

import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import act_matrix
import memory_models
from profile_params import MINIMAL, minimal_profiles

# Um trecho gerado: o nome, e o texto antigo entre os marcadores.
_GEN = re.compile(r"<!-- gen:(\w+) -->(.*?)<!-- /gen -->", re.DOTALL)

# Segundos de simulação por ELF, medidos nos jobs de `rv32im_full` (cada teste reanalisa o VHDL); o `max-parallel` do workflow.
_SECONDS_PER_ELF = 10
_MAX_PARALLEL = 16

_TEXT = {
    "pt-br": {
        "header": "| Perfil | Extensões acrescentadas à base | Pasta de testes | Testes | Jobs |",
        "none": "nenhuma",
        "all": "todas as pastas da base juntas",
        "single": "Os perfis {names} rodam em um só modelo cada (seção 2.1); os outros {many} rodam nos {models}. O total do workflow automático é, portanto:",
        "total": "jobs",
        "tests": "testes",
        "profiles": "perfis",
    },
    "en": {
        "header": "| Profile | Extensions added to the base | Test folder | Tests | Jobs |",
        "none": "none",
        "all": "every folder of the base together",
        "single": "The {names} profiles run on one model each (section 2.1); the other {many} run on all {models}. The total of the automatic workflow is therefore:",
        "total": "jobs",
        "tests": "tests",
        "profiles": "profiles",
    },
}


def _jobs_per_profile(root: Path) -> dict[str, int]:
    """Conta, por perfil mínimo, os modelos de memória em que ele roda.

    Parameters
    ----------
    root : Path
        Raiz do repositório.

    Returns
    -------
    dict of {str: int}
        O número de jobs de cada perfil na matriz automática.
    """
    run, _refused = act_matrix.matrix_entries(minimal_profiles(root), memory_models.all_models())
    return dict(Counter(entry["profile"] for entry in run))


def _table(root: Path, lang: str) -> str:
    """Escreve a tabela dos perfis mínimos.

    Parameters
    ----------
    root : Path
        Raiz do repositório.
    lang : str
        `pt-br` ou `en`.

    Returns
    -------
    str
        A tabela em Markdown, com uma linha por perfil.
    """
    text, jobs = _TEXT[lang], _jobs_per_profile(root)
    declared = yaml.safe_load((root / MINIMAL).read_text())["profiles"]
    lines = [text["header"], "| :--- | :--- | :--- | ---: | ---: |"]
    for profile in declared:
        covers = str(profile["covers"])
        folder = f"`{covers.split()[0].removeprefix('tests/')}`" if covers.startswith("tests/") else text["all"]
        extensions = ", ".join(profile["extensions"]) or text["none"]
        lines.append(f"| `{profile['name']}` | {extensions} | {folder} | {profile['tests']} | {jobs[profile['name']]} |")
    return "\n".join(lines)


def _total(root: Path, lang: str) -> str:
    """Escreve a frase e a fórmula do total de jobs.

    Parameters
    ----------
    root : Path
        Raiz do repositório.
    lang : str
        `pt-br` ou `en`.

    Returns
    -------
    str
        O texto em Markdown, com a fórmula em LaTeX.
    """
    text, jobs = _TEXT[lang], _jobs_per_profile(root)
    models = max(jobs.values())
    single = [f"`{name}`" for name, count in jobs.items() if count == 1]
    many = sum(1 for count in jobs.values() if count == models)
    joined = ", ".join(single[:-1]) + (" e " if lang == "pt-br" else " and ") + single[-1] if len(single) > 1 else single[0]
    formula = f"$${many} \\times {models} + {len(single)} \\times 1 = {sum(jobs.values())} \\text{{ {text['total']}}}$$"
    return text["single"].format(names=joined, many=many, models=models) + "\n\n" + formula


def _numbers(root: Path) -> dict[str, str]:
    """Calcula os números do dimensionamento e do resumo dos workflows.

    Parameters
    ----------
    root : Path
        Raiz do repositório.

    Returns
    -------
    dict of {str: str}
        Os valores de `jobs`, `profiles`, `runs`, `hours`, `wall` e `largest`.
    """
    jobs = _jobs_per_profile(root)
    tests = {p["name"]: int(p["tests"]) for p in yaml.safe_load((root / MINIMAL).read_text())["profiles"]}
    runs = sum(tests[name] * count for name, count in jobs.items())
    hours = runs * _SECONDS_PER_ELF / 3600
    biggest = max(tests, key=lambda name: tests[name])
    return {
        "jobs": str(sum(jobs.values())),
        "profiles": str(len(jobs)),
        "runs": str(runs),
        "hours": str(round(hours)),
        "wall": str(max(1, math.ceil(hours / _MAX_PARALLEL))),
        "largest": f"`{biggest}`",
        "largest_tests": str(tests[biggest]),
    }


def render(root: Path, lang: str, current: str) -> str:
    """Troca o conteúdo de cada trecho gerado do texto pelo valor calculado.

    Parameters
    ----------
    root : Path
        Raiz do repositório.
    lang : str
        `pt-br` ou `en`.
    current : str
        O texto atual de `matrix.md`.

    Returns
    -------
    str
        O texto com os trechos gerados atualizados.

    Raises
    ------
    KeyError
        Se o texto cita um trecho que o gerador não conhece.
    """
    values = {"table": "\n" + _table(root, lang) + "\n", "total": "\n" + _total(root, lang) + "\n", **_numbers(root)}
    return _GEN.sub(lambda found: f"<!-- gen:{found.group(1)} -->{values[found.group(1)]}<!-- /gen -->", current)


def doc_path(root: Path, lang: str) -> Path:
    """Dá o caminho do `matrix.md` de um idioma."""
    return root / "docs" / lang / "act4" / "matrix.md"


def main() -> None:
    """Lê o comando e escreve ou confere os dois idiomas."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("mode", choices=("write", "check"))
    parser.add_argument("--root", default=".", help="root of the repository")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    stale = []
    for lang in _TEXT:
        path = doc_path(root, lang)
        current = path.read_text(encoding="utf-8")
        wanted = render(root, lang, current)
        if wanted != current:
            stale.append(str(path.relative_to(root)))
            if args.mode == "write":
                path.write_text(wanted, encoding="utf-8")
    if stale and args.mode == "check":
        sys.exit("these files differ from minimal_profiles.yaml and the matrix of the workflow; run `uv run python tools/riscv_build/act_docs.py write`:\n  " + "\n  ".join(stale))
    print("rewritten: " + ", ".join(stale) if stale else "up to date")


if __name__ == "__main__":
    main()
