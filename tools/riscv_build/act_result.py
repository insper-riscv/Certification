"""Recolhe o resultado de um job de certificação ACT4 para o release.

Uso, da raiz do repositório e depois do `riscv-tools --config build/target/config.yaml certify`:

    uv run python tools/riscv_build/act_result.py collect --profile P --memory rom=int,ram=int,icache=off,dcache=off \\
        --config build/target/config.yaml --out build/act4-result
    uv run python tools/riscv_build/act_result.py commit

O `certify` escreve o resumo `PASS`/`FAIL` por teste em `logs/certification/latest.log`, e o `make` do ACT4 grava
os ELFs em `<ACT4_DIR>/work/<alvo>/elfs/<base>/<pasta>/<teste>.elf` e a lista de testes selecionados em
`<ACT4_DIR>/work/<alvo>/test_list.md`. O `collect` junta essas duas fontes em `result.json`, que dá o veredito
de cada ELF com o seu módulo (a pasta de testes), e copia o log, a lista e o `config.yaml` para a pasta de
saída, que o workflow sobe como artifact `act4-result-<perfil>-<modelo>`. Nada precisa mudar no riscv-tools.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory_models
from profile_params import ACT4_DIR

# A linha do resumo do `certify`: dois espaços, o veredito e o nome do teste.
_VERDICT = re.compile(r"^  (PASS|FAIL)  (\S+)$")

# O nome de um perfil e de um modelo de memória só têm estes caracteres.
_NAME = re.compile(r"[A-Za-z0-9_]+")

SCHEMA = 1


def act4_commit(act_dir: Path = ACT4_DIR) -> str:
    """Lê o commit do ACT4 da imagem.

    A imagem grava o commit na primeira linha de `<pai do checkout>/.tag`; sem esse arquivo, vale o `HEAD` do
    checkout.

    Parameters
    ----------
    act_dir : Path
        O checkout do ACT4.

    Returns
    -------
    str
        O hash de 40 caracteres do commit.

    Raises
    ------
    SystemExit
        Se nenhuma das duas fontes dá um hash.
    """
    tag = act_dir.parent / ".tag"
    candidates = []
    if tag.is_file():
        candidates.append(tag.read_text().splitlines()[0].strip() if tag.read_text().strip() else "")
    git = subprocess.run(["git", "-C", str(act_dir), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    candidates.append(git.stdout.strip())
    for candidate in candidates:
        if re.fullmatch(r"[0-9a-f]{40}", candidate):
            return candidate
    raise SystemExit(f"cannot read the ACT4 commit from {tag} or from the git checkout {act_dir}")


def parse_summary(log: str) -> dict[str, bool]:
    """Lê o resumo `=== Summary ===` que o `certify` imprime no fim do log.

    Parameters
    ----------
    log : str
        O texto de `latest.log`.

    Returns
    -------
    dict of {str: bool}
        O veredito de cada teste (True para PASS), na ordem do log; vazio se o resumo não existe.
    """
    marker = log.rfind("=== Summary ===")
    if marker < 0:
        return {}
    verdicts: dict[str, bool] = {}
    for line in log[marker:].splitlines()[1:]:
        found = _VERDICT.match(line)
        if found:
            verdicts[found.group(2)] = found.group(1) == "PASS"
    return verdicts


def elf_keys(work: Path) -> dict[str, str]:
    """Mapeia o nome de cada ELF de uma pasta de trabalho do ACT4 para `<base>/<pasta>/<teste>`.

    Parameters
    ----------
    work : Path
        `<ACT4_DIR>/work/<alvo>`.

    Returns
    -------
    dict of {str: str}
        Do nome do teste ao seu identificador; os ELFs `.sig.elf` ficam de fora, como no `certify`.
    """
    found: dict[str, str] = {}
    for elf in sorted((work / "elfs").rglob("*.elf")):
        if elf.name.endswith(".sig.elf"):
            continue
        found[elf.stem] = "/".join(elf.relative_to(work / "elfs").with_suffix("").parts)
    return found


def _target_name(test_config: Path) -> str:
    """Lê o campo `name` de um `test_config.yaml` do ACT4."""
    return str(yaml.safe_load(test_config.read_text())["name"])


def collect(args: argparse.Namespace) -> None:
    """Grava `result.json` e copia o log, a lista de testes e o config do job.

    Parameters
    ----------
    args : argparse.Namespace
        `profile`, `memory`, `config`, `out`, `root`, `vendor_dir` e `log`.

    Raises
    ------
    SystemExit
        Se o log não existe ou o config não declara o alvo.
    """
    root = Path(args.root).resolve()
    model = memory_models.parse(args.memory)
    config = yaml.safe_load((root / args.config).read_text())
    act = config["act"]
    log_path = root / args.log
    if not log_path.is_file():
        raise SystemExit(f"{log_path} does not exist: certify did not run")
    log = log_path.read_text(errors="replace")
    verdicts = parse_summary(log)

    work_root = Path(args.vendor_dir) / "work"
    targets = [_target_name(root / act["target_config"])]
    if act.get("ram_target_config"):
        targets.append(_target_name(root / act["ram_target_config"]))
    keys: dict[str, str] = {}
    for target in targets:
        keys.update({stem: key for stem, key in elf_keys(work_root / target).items() if stem not in keys})
    results = {keys.get(stem, f"unknown/unknown/{stem}"): "PASS" if ok else "FAIL" for stem, ok in verdicts.items()}

    out = Path(args.out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    shutil.copyfile(log_path, out / "latest.log")
    shutil.copyfile(root / args.config, out / "config.yaml")
    test_list = work_root / targets[0] / "test_list.md"
    if test_list.is_file():
        shutil.copyfile(test_list, out / "test_list.md")
    data = {
        "schema": SCHEMA,
        "profile": args.profile,
        "memory": model.spec,
        "slug": model.slug,
        "extensions": str(act["extensions"]).split(","),
        "act4_commit": act4_commit(Path(args.vendor_dir)),
        "results": results,
    }
    (out / "result.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    passed = sum(1 for v in results.values() if v == "PASS")
    print(f"{args.profile} / {model.slug}: {passed} PASS of {len(results)} ELFs; result in {out}")


def main() -> None:
    """Lê os argumentos e roda o subcomando."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("collect", help="write result.json and copy the logs of one job")
    one.add_argument("--profile", required=True)
    one.add_argument("--memory", required=True, help="--memory syntax of riscv-tools")
    one.add_argument("--config", default="build/target/config.yaml", help="config.yaml that certify ran, from the root")
    one.add_argument("--out", default="build/act4-result", help="folder that receives the files")
    one.add_argument("--root", default=".")
    one.add_argument("--log", default="logs/certification/latest.log", help="log of certify, from the root")
    one.add_argument("--vendor-dir", default=str(ACT4_DIR), help="the ACT4 checkout that certify used (default: ACT4_DIR)")
    sub.add_parser("commit", help="print the ACT4 commit of the image")
    args = parser.parse_args()
    if args.command == "commit":
        print(act4_commit())
        return
    if not _NAME.fullmatch(args.profile):
        parser.error("--profile is not a profile name")
    collect(args)


if __name__ == "__main__":
    main()
