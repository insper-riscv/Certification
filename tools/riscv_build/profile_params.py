"""Parâmetros que os geradores dos alvos ACT4 compartilham: os perfis do núcleo e o que cada um liga."""
import json
import subprocess
from pathlib import Path

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


def has_csr(ext: set[str]) -> bool:
    """Diz se o perfil tem CSRs: qualquer um dos Zicsr, Zicntr ou Zihpm os traz."""
    return "Zicsr" in ext or "Zicntr" in ext or "Zihpm" in ext


def extension_list(ext: set[str]) -> list[str]:
    """Monta a lista de extensões que o `certify` repassa ao ACT4, na ordem canônica."""
    return (
        ["I"]
        + (["M"] if "M" in ext else [])
        + (["Zmmul"] if ("Zmmul" in ext or "M" in ext) else [])
        + (["Zicsr"] if has_csr(ext) else [])
        + (["Zicntr"] if "Zicntr" in ext else [])
        + (["Zihpm"] if "Zihpm" in ext else [])
        + (["Zifencei"] if "Zifencei" in ext else [])
        + (["Zicclsm"] if "Zicclsm" in ext else [])
    )


def hardware_flags(ext: set[str]) -> dict[str, str]:
    """Dá os genéricos HAS_* que ligam, no topo de simulação, o que o perfil implementa."""
    flags = {
        "HAS_ZICSR": has_csr(ext),
        "HAS_ZICCLSM": "Zicclsm" in ext,
        "HAS_ZICNTR": "Zicntr" in ext,
        "HAS_ZIHPM": "Zihpm" in ext,
        "HAS_M": "M" in ext,
        "HAS_ZMMUL": "Zmmul" in ext,
    }
    if "Zifencei" in ext:
        flags["HAS_ZIFENCEI"] = True
    return {name: str(value).lower() for name, value in flags.items()}


def parameter_lines(ext: set[str]) -> str:
    """Escreve os genéricos HAS_* do perfil como linhas de `sim.parameters` de um config."""
    return "".join(f'    {name}: "{value}"\n' for name, value in hardware_flags(ext).items())
