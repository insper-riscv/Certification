"""Monta a matriz de (perfil, modelo de memória) que os workflows de certificação rodam e a imprime.

Uso, da raiz do repositório:

    uv run python tools/riscv_build/act_matrix.py minimal
    uv run python tools/riscv_build/act_matrix.py all [--only REGEX]
    uv run python tools/riscv_build/act_matrix.py one --profile P --memory rom=ext,ram=ext,icache=on,dcache=on

Os três modos escolhem os perfis (os mínimos de minimal_profiles.yaml, todos os da matriz do Core mais os
mínimos, ou um só) e os cruzam com as 16 combinações de memória e cache. As que o topo modular não aceita
(memory_models.py) ficam de fora, e o motivo é impresso. Com `--github-output` o script grava `matrix=<JSON>` e
`count=<n>` no arquivo de saídas do passo, e com `--summary` acrescenta a tabela em Markdown ao resumo do job.
Toda entrada vem por argumento (nunca interpolada em shell) e é validada contra uma lista branca.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory_models
from memory_models import MemoryModel
from profile_params import find_profile, minimal_profiles, reference_profiles

# Um nome de perfil só tem letras, algarismos e sublinhado; o filtro `--only` é uma expressão regular curta.
_NAME = re.compile(r"[A-Za-z0-9_]+")
_ONLY_MAX = 200


def _profiles(root: Path, mode: str, profile: str | None) -> list[tuple[str, set[str]]]:
    """Escolhe os perfis do modo.

    Parameters
    ----------
    root : Path
        Raiz do repositório.
    mode : str
        `minimal`, `all` ou `one`.
    profile : str or None
        O perfil do modo `one`.

    Returns
    -------
    list of tuple of (str, set of str)
        Nome e extensões de cada perfil, sem repetição.
    """
    if mode == "one":
        assert profile is not None
        return [(profile, find_profile(root, profile))]
    chosen = dict(minimal_profiles(root))
    if mode == "all":
        chosen = {**dict(reference_profiles(root)), **chosen}
    return sorted(chosen.items()) if mode == "all" else list(chosen.items())


def _entries(
    profiles: list[tuple[str, set[str]]], models: list[MemoryModel], only: re.Pattern[str]
) -> tuple[list[dict[str, str]], list[str]]:
    """Cruza perfis e modelos, separando os pares aceitos dos recusados.

    Parameters
    ----------
    profiles : list of tuple of (str, set of str)
        Os perfis.
    models : list of MemoryModel
        Os modelos de memória a considerar.
    only : re.Pattern
        Filtro sobre `<perfil>/<slug do modelo>`.

    Returns
    -------
    tuple of (list of dict of {str: str}, list of str)
        Os pares que rodam, e uma linha por razão distinta de recusa com a quantidade de pares que ela corta.
    """
    run: list[dict[str, str]] = []
    refused: dict[str, int] = {}
    for name, ext in profiles:
        for model in models:
            if not only.search(f"{name}/{model.slug}"):
                continue
            why = memory_models.problems(model, ext)
            if why:
                refused[why[0]] = refused.get(why[0], 0) + 1
                continue
            run.append({"profile": name, "memory": model.spec, "slug": model.slug})
    return run, [f"{count} x {reason}" for reason, count in refused.items()]


def matrix_entries(profiles: list[tuple[str, set[str]]], models: list[MemoryModel]) -> tuple[list[dict[str, str]], list[str]]:
    """Cruza perfis e modelos sem filtro, como o job `plan` do workflow automático.

    Parameters
    ----------
    profiles : list of tuple of (str, set of str)
        Os perfis.
    models : list of MemoryModel
        Os modelos de memória a considerar.

    Returns
    -------
    tuple of (list of dict of {str: str}, list of str)
        Os pares que rodam e as linhas de recusa, como em `_entries`.
    """
    return _entries(profiles, models, re.compile(""))


def _markdown(run: list[dict[str, str]], refused: list[str]) -> str:
    """Escreve a matriz como tabela Markdown, para o resumo do job.

    Parameters
    ----------
    run : list of dict of {str: str}
        Os pares que rodam.
    refused : list of str
        As linhas de recusa.

    Returns
    -------
    str
        O texto Markdown.
    """
    counts: dict[str, list[str]] = {}
    for entry in run:
        counts.setdefault(entry["profile"], []).append(entry["slug"])
    lines = [f"### ACT4 matrix: {len(run)} jobs, {len(counts)} profiles", "", "| Profile | Jobs | Memory models |", "| :--- | ---: | :--- |"]
    lines += [f"| `{name}` | {len(slugs)} | {', '.join(f'`{s}`' for s in slugs)} |" for name, slugs in counts.items()]
    if refused:
        lines += ["", "Pairs left out, with the first reason:", ""] + [f"- {line}" for line in refused]
    return "\n".join(lines) + "\n"


def main() -> None:
    """Lê os argumentos, monta a matriz, imprime e grava as saídas pedidas."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("mode", choices=("minimal", "all", "one"))
    parser.add_argument("--root", default=".", help="root of the repository")
    parser.add_argument("--profile", help="profile of the mode `one`")
    parser.add_argument("--memory", default="all", help="`all` (every model the top accepts) or one model, in the --memory syntax")
    parser.add_argument("--only", default="", help="regular expression over <profile>/<memory slug>; empty keeps everything")
    parser.add_argument("--github-output", help="file of the step outputs of GitHub Actions")
    parser.add_argument("--summary", help="file of the job summary of GitHub Actions")
    args = parser.parse_args()

    if args.mode == "one" and not (args.profile and _NAME.fullmatch(args.profile)):
        parser.error("the mode `one` needs a valid --profile")
    if len(args.only) > _ONLY_MAX:
        parser.error("--only is too long")
    try:
        only = re.compile(args.only)
        models = memory_models.all_models() if args.memory == "all" else [memory_models.parse(args.memory)]
    except (re.error, ValueError) as error:
        parser.error(str(error))

    run, refused = _entries(_profiles(Path(args.root).resolve(), args.mode, args.profile), models, only)
    text = _markdown(run, refused)
    print(text)
    if not run:
        sys.exit("no (profile, memory model) pair is left to run; the reasons are above")
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as handle:
            handle.write(text)
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"matrix={json.dumps(run, separators=(',', ':'))}\ncount={len(run)}\n")


if __name__ == "__main__":
    main()
