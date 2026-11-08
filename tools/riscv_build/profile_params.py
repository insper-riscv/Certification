"""Parâmetros que os geradores dos alvos ACT4 compartilham: os perfis do núcleo e o que cada um liga."""
import json
import os
import subprocess
from pathlib import Path

import yaml

# As extensões que o platform.yaml liga como `extras` e que o gerador sabe acender: cada uma acende o genérico
# `HAS_<NOME>` do topo e entra, nesta ordem, depois das extensões da matriz. Zihintntl e Zihintpause nunca fazem
# parte da matriz do Core. Zimop e Zicond fazem a partir da onda 2 (a matriz do Core as traz); antes dela eram
# extras. Como o conjunto de extensões de um perfil é só um conjunto, a lista vale para as duas versões da matriz.
EXTRAS = ("Zimop", "Zicond", "Zihintntl", "Zihintpause")

# As extensões que a matriz do Core pode trazer e que os perfis de referência não usam: a matriz de 480 perfis
# da onda 2 é a de 120 vezes as combinações com elas, e os perfis que as citam não são gerados nem versionados.
BEYOND_REFERENCE = frozenset({"Zimop", "Zicond"})

# O checkout do ACT4 (riscv-arch-test) da imagem `ci-act4`: os testes, as gems do UDB e o `make` são do mesmo
# commit, gravado em `<pai>/.tag` e no rótulo `act4.commit` da imagem. A variável de ambiente `ACT4_DIR` troca o
# caminho (por exemplo, para um checkout local); é o único lugar do repositório que nomeia esse caminho.
ACT4_DIR = Path(os.environ.get("ACT4_DIR", "/opt/riscv-foundation/act4/riscv-arch-test"))

# A lista dos perfis mínimos, com o critério de cada um.
MINIMAL = "tools/riscv_build/minimal_profiles.yaml"

# A especificação dos perfis é a do Core, que vem no submódulo Insper-RISC-V.
SPEC = "Insper-RISC-V/Core/profiles/matrix.yaml"


def variants(root: Path) -> list[tuple[str, set[str]]]:
    """Lista os perfis do núcleo, cada um com o seu conjunto de extensões.

    Um perfil sem Zicclsm não o declara, deixa MISALIGNED_LDST desligado e roda o núcleo com
    has_zicclsm falso. O Zicntr implica o Zicsr: o hardware liga os dois, e a string da ISA e as
    listas de testes citam os dois.
    """
    listing = subprocess.run(
        ["uv", "run", "riscv-tools", "profiles", "--spec", str(root / SPEC), "--format", "json"],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout
    return [(p["name"], set(p["extensions"])) for p in json.loads(listing)]


def reference_profiles(root: Path) -> list[tuple[str, set[str]]]:
    """Lista os perfis de referência: os da matriz do Core que não citam extensões além da referência.

    Com a matriz de 120 perfis é a matriz inteira; com a de 480 (que acrescenta Zimop e Zicond) são os mesmos
    120 nomes. Os outros perfis da matriz continuam aceitos por nome (`find_profile`), mas não são gerados em
    massa nem entram na matriz manual de todos os perfis.

    Parameters
    ----------
    root : Path
        Raiz do repositório.

    Returns
    -------
    list of tuple of (str, set of str)
        Nome e extensões de cada perfil de referência.
    """
    return [(name, ext) for name, ext in variants(root) if not ext & BEYOND_REFERENCE]


def minimal_profiles(root: Path) -> list[tuple[str, set[str]]]:
    """Lê os perfis mínimos do critério `REQUIRED_EXTENSIONS` do ACT4.

    Parameters
    ----------
    root : Path
        Raiz do repositório.

    Returns
    -------
    list of tuple of (str, set of str)
        O nome de cada perfil mínimo e o seu conjunto de extensões, na ordem do arquivo.
    """
    data = yaml.safe_load((root / MINIMAL).read_text())
    return [(p["name"], set(p["extensions"])) for p in data["profiles"]]


def minimal_tests(root: Path) -> dict[str, int]:
    """Lê quantos ELFs o `minimal_profiles.yaml` declara para cada perfil mínimo.

    Parameters
    ----------
    root : Path
        Raiz do repositório.

    Returns
    -------
    dict of {str: int}
        O campo `tests` de cada perfil, pelo nome.
    """
    data = yaml.safe_load((root / MINIMAL).read_text())
    return {p["name"]: int(p["tests"]) for p in data["profiles"]}


def find_profile(root: Path, name: str) -> set[str]:
    """Acha as extensões de um perfil pelo nome, entre os mínimos e os da matriz do Core.

    Parameters
    ----------
    root : Path
        Raiz do repositório.
    name : str
        Nome do perfil, como em `minimal_profiles.yaml` ou na matriz (`rv32im_zicntr`).

    Returns
    -------
    set of str
        As extensões do perfil.

    Raises
    ------
    SystemExit
        Se nenhum perfil tem esse nome.
    """
    known = dict(minimal_profiles(root))
    if name not in known:
        known.update(variants(root))
    if name not in known:
        raise SystemExit(f"no profile named '{name}'")
    return known[name]


def has_csr(ext: set[str]) -> bool:
    """Diz se o perfil tem CSRs: qualquer um dos Zicsr, Zicntr ou Zihpm os traz."""
    return "Zicsr" in ext or "Zicntr" in ext or "Zihpm" in ext


def is_e(name: str) -> bool:
    """Diz se o perfil é de base RV32E (16 registradores): o nome começa por `rv32e`."""
    return name.startswith("rv32e")


def extension_list(ext: set[str], name: str = "rv32i") -> list[str]:
    """Monta a lista de extensões que o `certify` repassa ao ACT4, na ordem canônica."""
    return (
        ["E" if is_e(name) else "I"]
        + (["M"] if "M" in ext else [])
        + (["Zmmul"] if ("Zmmul" in ext or "M" in ext) else [])
        + (["Zicsr"] if has_csr(ext) else [])
        + (["Zicntr"] if "Zicntr" in ext else [])
        + (["Zihpm"] if "Zihpm" in ext else [])
        + (["Zifencei"] if "Zifencei" in ext else [])
        + (["Zicclsm"] if "Zicclsm" in ext else [])
        + [extra for extra in EXTRAS if extra in ext]
    )


def hardware_flags(ext: set[str], name: str = "rv32i") -> dict[str, str]:
    """Dá os genéricos HAS_* que ligam, no topo de simulação, o que o perfil implementa."""
    flags = {
        "HAS_E": is_e(name),
        "HAS_ZICSR": has_csr(ext),
        "HAS_ZICCLSM": "Zicclsm" in ext,
        "HAS_ZICNTR": "Zicntr" in ext,
        "HAS_ZIHPM": "Zihpm" in ext,
        "HAS_M": "M" in ext,
        "HAS_ZMMUL": "Zmmul" in ext,
    }
    if "Zifencei" in ext:
        flags["HAS_ZIFENCEI"] = True
    for extra in EXTRAS:
        if extra in ext:
            flags[f"HAS_{extra.upper()}"] = True
    return {name: str(value).lower() for name, value in flags.items()}


def parameter_lines(ext: set[str], name: str = "rv32i") -> str:
    """Escreve os genéricos HAS_* do perfil como linhas de `sim.parameters` de um config."""
    return "".join(f'    {key}: "{value}"\n' for key, value in hardware_flags(ext, name).items())


_MODULAR_PLATFORM = "Insper-RISC-V/src/simulation/modular"


def _modular_sources(root: Path) -> list[str]:
    """Lê as fontes VHDL do `config.yaml` da plataforma modular do Insper-RISC-V, na ordem de análise.

    Essa lista é gerada pelo `make generate-sources` do Insper-RISC-V a partir do `provides` dos módulos, então
    acompanha o topo modular sem filtro nenhum aqui. Os caminhos dela são relativos ao Insper-RISC-V.
    """
    lines = (root / _MODULAR_PLATFORM / "config.yaml").read_text().splitlines()
    start = lines.index("  vhdl_sources:") + 1
    listed = []
    for line in lines[start:]:
        if not line.startswith("    - "):
            break
        listed.append(f"Insper-RISC-V/{line[6:].strip()}")
    return listed


def write_modular_config(root: Path) -> None:
    """Escreve config.modular.yaml: a plataforma modular de simulação, com as fontes lidas do submódulo.

    As fontes são as do `config.yaml` modular do Insper-RISC-V (o núcleo, os blocos comuns, as memórias, as
    caches, os periféricos, o interconector e o topo modular), mais o topo de simulação do ACT4 desta pasta.
    """
    sources = [*_modular_sources(root), "tools/riscv_build/act/sim/act_modular_top.vhd"]
    listing = "".join(f"    - {s}\n" for s in sources)
    (root / "tools/riscv_build/config.modular.yaml").write_text(
        f"""# The ACT4 track on the modular simulation platform (Insper-RISC-V, src/simulation/modular): the ROM and the RAM of
# 1 MB each, inside the chip (integrated model) or behind the caches of 4 kbit (external model, for the
# profiles with Zifencei). Written by gen_profiles.py from the config.yaml of the modular platform of the Insper-RISC-V submodule; nobody edits it.
#
# The VHDL comes from the Insper-RISC-V submodule; the top that cocotb drives is act_modular_top, which gives
# the modular top the ports the testbenches of tools/riscv_build/act/sim observe.

toolchain:
  gcc: riscv32-unknown-elf-gcc
  objcopy: riscv32-unknown-elf-objcopy

isa:
  base: i
  default_ext: ""
  canonical_order: "MAFDQLCBJTPVNH"

# Only the fields `certify` needs; ACT4 brings its own linker script, memory map and halt/print macros.
memory:
  tohost_addr: 0x001FFFE0

paths:
  build_dir: build

sim:
  toplevel: act_modular_top
  ghdl_std: "08"
  # In dependency order, relative to this project's root.
  vhdl_sources:
{listing}  # The images the harness writes for each ELF: the boot memory is the first 4 KB of the code, the ROM the
  # code region and the RAM the data region.
  parameters:
    BOOT_MEMORY_FILE: "{{boot_hex_path}}"
    ROM_FILE: "{{hex_path}}"
    RAM_FILE: "{{ram_hex_path}}"

act:
  # The checkout of ACT4 in the ci-act4 image: its tests, its gems and its make are of one commit, which every run records.
  vendor_dir: {ACT4_DIR}
  jobs: 0
  # Where the data region of the ELFs starts (the RAM) and the size of the boot memory.
  ram_base: 0x100000
  boot_memory_bytes: 0x1000
"""
    )
