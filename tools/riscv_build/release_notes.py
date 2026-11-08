"""Monta o título, as notas, a tag e os logs do release de uma certificação ACT4.

Uso, da raiz do repositório:

    uv run python tools/riscv_build/release_notes.py --results DIR --out DIR --mode auto|manual --kind matrix|profile \\
        --cert-commit SHA --riscv-commit SHA --datetime 2026-11-06T14:03:00Z --run-url URL \\
        [--act4-commit SHA] [--reused-from URL] [--matrix JSON]

`--results` é a pasta que reúne, em uma subpasta por job, o `result.json` e os logs que `act_result.py collect`
escreveu. Em `--out` o script grava

| Arquivo | Conteúdo |
| :--- | :--- |
| `title.txt` | No modo `auto`, a combinação validada (`RV32 I/E M, Zmmul, ...`); no modo `manual`, a data e a hora em UTC mais a matriz ou o perfil |
| `notes.md` | Perfis, ELFs por módulo, modelos de memória, commits e link do run |
| `tag.txt` | `cert-AAAAMMDD-HHMMSS-<sha7 do Certification>` |
| `attachments.txt` | Um caminho por linha: um `logs-<perfil>.tar.gz` por perfil, cada um com menos de 2 GiB |

Todo valor vem dos resultados reais dos jobs (PASS por ELF), nunca do YAML. Se um perfil falhou, se falta um job
da matriz, se um job não tem veredito ou se os jobs rodaram com commits diferentes do ACT4, o script sai com erro
e não escreve nada: só se faz release de uma certificação que passou inteira. Usa apenas a biblioteca padrão.
"""

import argparse
import json
import re
import shutil
import sys
import tarfile
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory_models

# O GitHub recusa um anexo de release com 2 GiB ou mais.
MAX_ATTACHMENT = 2 * 1024**3 - 1

# A ordem canônica dos módulos no título, a mesma de `profile_params.extension_list`; o resto vai no fim, em ordem alfabética.
CANONICAL = ("M", "Zmmul", "Zicsr", "Zicntr", "Zihpm", "Zifencei", "Zicclsm", "Zimop", "Zicond", "Zihintntl", "Zihintpause")

# As pastas de testes que são a base e não um módulo.
_BASES = {"I": "I", "E": "E"}

_HASH = re.compile(r"[0-9a-f]{7,40}")
_NAME = re.compile(r"[A-Za-z0-9_]+")
_URL = re.compile(r"https://[A-Za-z0-9._~:/?#@!$&'()*+,;=%-]+")
_DATE = "%Y-%m-%dT%H:%M:%SZ"


class ReleaseError(Exception):
    """A certificação não pode virar release; a mensagem diz o motivo."""


def load_results(results_dir: Path) -> list[dict]:
    """Lê todos os `result.json` e valida cada um.

    Parameters
    ----------
    results_dir : Path
        A pasta com uma subpasta por job.

    Returns
    -------
    list of dict
        Os resultados, cada um com a chave `dir` (a pasta do job) e ordenados por perfil e modelo de memória.

    Raises
    ------
    ReleaseError
        Se não há resultado, se um tem formato inválido, se um ELF não passou ou se um par se repete.
    """
    found = sorted(results_dir.rglob("result.json"))
    if not found:
        raise ReleaseError(f"no result.json under {results_dir}")
    loaded: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path in found:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            profile, slug, results = data["profile"], data["slug"], data["results"]
            memory_models.parse(data["memory"])
            if data["schema"] != 1 or not _NAME.fullmatch(profile) or not data["extensions"]:
                raise ValueError("schema")
            if not _HASH.fullmatch(data["act4_commit"]) or not isinstance(results, dict):
                raise ValueError("fields")
        except (KeyError, ValueError, TypeError) as error:
            raise ReleaseError(f"{path}: invalid result ({error!r})") from error
        if not results:
            raise ReleaseError(f"{profile} / {slug}: the job has no verdict per ELF")
        failed = sorted(elf for elf, verdict in results.items() if verdict != "PASS")
        if failed:
            raise ReleaseError(f"{profile} / {slug}: {len(failed)} ELF(s) did not pass, first {failed[0]}")
        if (profile, slug) in seen:
            raise ReleaseError(f"{profile} / {slug} appears twice")
        seen.add((profile, slug))
        data["dir"] = path.parent
        loaded.append(data)
    return sorted(loaded, key=lambda d: (d["profile"], d["slug"]))


def check_matrix(results: list[dict], matrix: list[dict]) -> None:
    """Confere se os resultados são exatamente os pares que a matriz planejou.

    Parameters
    ----------
    results : list of dict
        Os resultados lidos.
    matrix : list of dict
        A matriz do `plan`, com `profile` e `slug` em cada par.

    Raises
    ------
    ReleaseError
        Se falta algum par ou sobra algum.
    """
    want = {(m["profile"], m["slug"]) for m in matrix}
    have = {(r["profile"], r["slug"]) for r in results}
    if want - have:
        raise ReleaseError(f"jobs without result: {sorted(want - have)[:5]}")
    if have - want:
        raise ReleaseError(f"results outside the planned matrix: {sorted(have - want)[:5]}")


def base_of(result: dict) -> str:
    """Dá a base ISA (`I` ou `E`) de um resultado, pelos seus ELFs.

    Parameters
    ----------
    result : dict
        Um resultado já validado.

    Returns
    -------
    str
        `I` se os ELFs são `rv32i/...`, `E` se são `rv32e/...`.

    Raises
    ------
    ReleaseError
        Se os ELFs não são todos da mesma base conhecida.
    """
    prefixes = {elf.split("/")[0] for elf in result["results"]}
    if prefixes == {"rv32i"}:
        return "I"
    if prefixes == {"rv32e"}:
        return "E"
    raise ReleaseError(f"{result['profile']}: the ELFs do not belong to one known base ({sorted(prefixes)})")


def module_of(elf: str) -> str:
    """Dá o módulo (a pasta de testes do ACT4) de um ELF `<base>/<pasta>/<teste>`."""
    return elf.split("/")[1]


def order_modules(modules: set[str]) -> list[str]:
    """Põe os módulos na ordem canônica; os desconhecidos vão no fim, em ordem alfabética.

    Parameters
    ----------
    modules : set of str
        Os módulos, sem as bases.

    Returns
    -------
    list of str
        Os módulos ordenados.
    """
    known = [m for m in CANONICAL if m in modules]
    return known + sorted(modules - set(CANONICAL))


def validated_combination(results: list[dict]) -> tuple[list[str], list[str]]:
    """Deriva as bases e os módulos que a certificação validou, dos ELFs que passaram.

    Parameters
    ----------
    results : list of dict
        Os resultados, todos já com todos os ELFs em PASS.

    Returns
    -------
    tuple of (list of str, list of str)
        As bases (`I`, `E`) e os módulos em ordem canônica, sem as bases.
    """
    bases = sorted({base_of(r) for r in results}, key=("I", "E").index)
    modules = {module_of(elf) for r in results for elf in r["results"]} - set(_BASES)
    return bases, order_modules(modules)


def make_title(mode: str, kind: str, when: datetime, results: list[dict]) -> str:
    """Escreve o título do release.

    Parameters
    ----------
    mode : str
        `auto` (merge na `main`) ou `manual`.
    kind : str
        `matrix` ou `profile`.
    when : datetime
        Data e hora UTC do run.
    results : list of dict
        Os resultados.

    Returns
    -------
    str
        No modo `auto`, `RV32 I/E M, Zmmul, ...`; no modo `manual`, `AAAA-MM-DD HH:MM UTC, matriz` ou
        `AAAA-MM-DD HH:MM UTC, perfil <nome>`.
    """
    if mode == "manual":
        stamp = when.strftime("%Y-%m-%d %H:%M UTC")
        return f"{stamp}, matriz" if kind == "matrix" else f"{stamp}, perfil {results[0]['profile']}"
    bases, modules = validated_combination(results)
    return " ".join(["RV32", "/".join(bases)] + ([", ".join(modules)] if modules else []))


def make_tag(when: datetime, cert_commit: str) -> str:
    """Escreve a tag única do release.

    Parameters
    ----------
    when : datetime
        Data e hora UTC do run.
    cert_commit : str
        Commit do Certification.

    Returns
    -------
    str
        `cert-AAAAMMDD-HHMMSS-<sha7>`.
    """
    return f"cert-{when.strftime('%Y%m%d-%H%M%S')}-{cert_commit[:7]}"


def describe_memory(spec: str) -> dict[str, str]:
    """Descreve em português um modelo de memória.

    Parameters
    ----------
    spec : str
        O modelo na sintaxe `--memory` do riscv-tools.

    Returns
    -------
    dict of {str: str}
        As chaves `rom`, `ram`, `icache`, `dcache` e `arch` (a letra A a D da arquitetura coerente).
    """
    model = memory_models.parse(spec)
    return {
        "rom": "externa (chip de FLASH)" if model.rom_external else "interna",
        "ram": "externa (chip de RAM)" if model.ram_external else "interna",
        "icache": "ligada" if model.icache else "desligada",
        "dcache": "ligada" if model.dcache else "desligada",
        "arch": model.architecture or "-",
    }


def module_table(results: list[dict]) -> list[str]:
    """Monta a tabela de ELFs por módulo, a partir dos ELFs que passaram.

    Parameters
    ----------
    results : list of dict
        Os resultados.

    Returns
    -------
    list of str
        As linhas da tabela Markdown.
    """
    distinct: dict[tuple[str, str], set[str]] = {}
    runs: Counter[tuple[str, str]] = Counter()
    for r in results:
        base = base_of(r)
        for elf in r["results"]:
            key = (base, module_of(elf))
            distinct.setdefault(key, set()).add(elf)
            runs[key] += 1
    order = {"I": 0, "E": 1}
    names = order_modules({m for _b, m in distinct} - set(_BASES))
    rows = sorted(distinct, key=lambda k: (order[k[0]], 0 if k[1] in _BASES else 1, names.index(k[1]) if k[1] in names else -1))
    lines = ["| Base | Módulo | ELFs distintos | Execuções |", "| :--- | :--- | ---: | ---: |"]
    lines += [f"| {base} | {module} | {len(distinct[(base, module)])} | {runs[(base, module)]} |" for base, module in rows]
    total = sum(len(v) for v in distinct.values())
    lines.append(f"| Total | | {total} | {sum(runs.values())} |")
    return lines


def make_notes(args: argparse.Namespace, when: datetime, title: str, results: list[dict]) -> str:
    """Escreve as notas do release em Markdown.

    Parameters
    ----------
    args : argparse.Namespace
        Os argumentos validados: modo, tipo, commits e links.
    when : datetime
        Data e hora UTC do run.
    title : str
        O título já montado.
    results : list of dict
        Os resultados.

    Returns
    -------
    str
        O texto das notas.
    """
    by_profile: dict[str, list[dict]] = {}
    for r in results:
        by_profile.setdefault(r["profile"], []).append(r)
    act4 = results[0]["act4_commit"]
    origin = "merge na `main`" if args.mode == "auto" else "execução manual"
    lines = [
        f"# {title}",
        "",
        "## 1. Origem",
        "",
        "| Campo | Valor |",
        "| :--- | :--- |",
        f"| Disparo | {origin} |",
        f"| Data (UTC) | {when.strftime('%Y-%m-%d %H:%M:%S')} |",
        f"| Commit do Certification | `{args.cert_commit}` |",
        f"| Commit do Insper-RISC-V | `{args.riscv_commit}` |",
        f"| Commit do ACT4 (testes e gems da imagem `ci-act4`) | `{act4}` |",
        f"| Run | {args.run_url} |",
    ]
    if args.reused_from:
        lines.append(f"| Resultado reaproveitado do run | {args.reused_from} |")
    lines += ["", "## 2. Perfis testados", "", "| Perfil | Base | Extensões do ACT4 | Modelos de memória | ELFs distintos |", "| :--- | :--- | :--- | ---: | ---: |"]
    for name, group in by_profile.items():
        elfs = {elf for r in group for elf in r["results"]}
        lines.append(f"| `{name}` | {base_of(group[0])} | {', '.join(group[0]['extensions'])} | {len(group)} | {len(elfs)} |")
    lines += ["", "## 3. ELFs testados por módulo", "", *module_table(results)]
    lines += [
        "",
        "## 4. Combinações de memória",
        "",
        ("Cada linha é um job: o perfil rodou com a ROM e a RAM dentro ou fora do chip, e com as caches ligadas exatamente "
         "quando a memória é externa."),
        "",
        "| Perfil | ROM | RAM | Cache de instruções | Cache de dados | Arquitetura | ELFs |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | ---: |",
    ]
    for r in results:
        m = describe_memory(r["memory"])
        lines.append(f"| `{r['profile']}` | {m['rom']} | {m['ram']} | {m['icache']} | {m['dcache']} | {m['arch']} | {len(r['results'])} |")
    lines += ["", "## 5. Logs anexados", "", "Um `logs-<perfil>.tar.gz` por perfil, com `latest.log`, `test_list.md`, `config.yaml` e `result.json` de cada modelo de memória."]
    lines += ["", "---", "", "Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](https://github.com/insper-riscv/Certification/blob/main/LICENSE)."]
    return "\n".join(lines) + "\n"


def pack_logs(results: list[dict], target: Path) -> list[Path]:
    """Empacota os logs, um `.tar.gz` por perfil.

    Parameters
    ----------
    results : list of dict
        Os resultados, com a pasta de cada job em `dir`.
    target : Path
        A pasta que recebe os arquivos.

    Returns
    -------
    list of Path
        Os arquivos criados, em ordem de perfil.

    Raises
    ------
    ReleaseError
        Se um arquivo passa do limite de anexo do GitHub.
    """
    target.mkdir(parents=True)
    packed: list[Path] = []
    for name in sorted({r["profile"] for r in results}):
        archive = target / f"logs-{name}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            for r in (r for r in results if r["profile"] == name):
                for item in sorted(r["dir"].iterdir()):
                    if item.is_file() and not item.is_symlink():
                        tar.add(item, arcname=f"{name}/{r['slug']}/{item.name}")
        if archive.stat().st_size > MAX_ATTACHMENT:
            raise ReleaseError(f"{archive.name} has {archive.stat().st_size} bytes, over the 2 GiB limit of a release asset")
        packed.append(archive)
    return packed


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Lê e valida os argumentos.

    Parameters
    ----------
    argv : list of str or None
        A linha de comando; `None` usa `sys.argv`.

    Returns
    -------
    argparse.Namespace
        Os argumentos, com `when` já convertido para `datetime`.
    """
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--results", required=True, type=Path, help="folder with one subfolder per job (result.json and logs)")
    parser.add_argument("--out", required=True, type=Path, help="folder that receives title.txt, notes.md, tag.txt, attachments.txt and logs/")
    parser.add_argument("--mode", required=True, choices=("auto", "manual"))
    parser.add_argument("--kind", required=True, choices=("matrix", "profile"))
    parser.add_argument("--cert-commit", required=True, help="commit of the Certification")
    parser.add_argument("--riscv-commit", required=True, help="commit of the Insper-RISC-V submodule")
    parser.add_argument("--act4-commit", help="commit of the ACT4 of the image; must match the jobs")
    parser.add_argument("--datetime", required=True, dest="when", help="UTC date and time, 2026-11-06T14:03:00Z")
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--reused-from", help="run whose result a push to the main reused")
    parser.add_argument("--matrix", help="JSON of the planned matrix; every pair must have a result")
    args = parser.parse_args(argv)
    for flag in ("cert_commit", "riscv_commit", "act4_commit"):
        value = getattr(args, flag)
        if value is not None and not _HASH.fullmatch(value):
            parser.error(f"--{flag.replace('_', '-')} is not a commit hash")
    for flag in ("run_url", "reused_from"):
        value = getattr(args, flag)
        if value is not None and not _URL.fullmatch(value):
            parser.error(f"--{flag.replace('_', '-')} is not an https link")
    try:
        args.when = datetime.strptime(args.when, _DATE).replace(tzinfo=UTC)
    except ValueError:
        parser.error("--datetime must look like 2026-11-06T14:03:00Z")
    return args


def build(args: argparse.Namespace) -> dict[str, Any]:
    """Valida os resultados e monta os arquivos do release em uma pasta temporária.

    Parameters
    ----------
    args : argparse.Namespace
        Os argumentos validados.

    Returns
    -------
    dict of {str: Any}
        O título, as notas, a tag e os resultados, para o chamador gravar.

    Raises
    ------
    ReleaseError
        Se a certificação não pode virar release.
    """
    results = load_results(args.results)
    if args.matrix:
        check_matrix(results, json.loads(args.matrix))
    if args.kind == "profile" and len(results) != 1:
        raise ReleaseError("a run of one profile and one memory model must have exactly one result")
    commits = {r["act4_commit"] for r in results}
    if len(commits) != 1:
        raise ReleaseError(f"the jobs ran with different ACT4 commits: {sorted(commits)}")
    if args.act4_commit and not next(iter(commits)).startswith(args.act4_commit):
        raise ReleaseError(f"--act4-commit {args.act4_commit} is not the commit the jobs recorded ({next(iter(commits))})")
    title = make_title(args.mode, args.kind, args.when, results)
    return {"title": title, "notes": make_notes(args, args.when, title, results), "tag": make_tag(args.when, args.cert_commit), "results": results}


def main(argv: list[str] | None = None) -> int:
    """Roda o script; devolve o código de saída.

    Parameters
    ----------
    argv : list of str or None
        A linha de comando; `None` usa `sys.argv`.

    Returns
    -------
    int
        0 quando os arquivos foram escritos; 1 quando a certificação não pode virar release (nada é escrito).
    """
    args = parse_args(argv)
    if args.out.exists() and any(args.out.iterdir()):
        print(f"error: {args.out} is not empty", file=sys.stderr)
        return 1
    try:
        made = build(args)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="release-", dir=args.out.parent) as tmp:
            stage = Path(tmp) / "out"
            packed = pack_logs(made["results"], stage / "logs")
            (stage / "title.txt").write_text(made["title"] + "\n", encoding="utf-8")
            (stage / "notes.md").write_text(made["notes"], encoding="utf-8")
            (stage / "tag.txt").write_text(made["tag"] + "\n", encoding="utf-8")
            (stage / "attachments.txt").write_text("".join(f"{args.out / 'logs' / p.name}\n" for p in packed), encoding="utf-8")
            if args.out.exists():
                args.out.rmdir()
            shutil.move(str(stage), str(args.out))
    except (ReleaseError, ValueError, OSError) as error:
        print(f"error: {error}; no release", file=sys.stderr)
        return 1
    print(f"{made['tag']}\n{made['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
