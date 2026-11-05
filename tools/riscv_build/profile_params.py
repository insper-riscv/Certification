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
    return {name: str(value).lower() for name, value in flags.items()}


def parameter_lines(ext: set[str], name: str = "rv32i") -> str:
    """Escreve os genéricos HAS_* do perfil como linhas de `sim.parameters` de um config."""
    return "".join(f'    {key}: "{value}"\n' for key, value in hardware_flags(ext, name).items())


# Do que o submódulo traz, o que a plataforma modular não usa: o controlador e o modelo de SDRAM, a
# depuração por JTAG, o display e o topo da DE0-CV.
_NOT_MODULAR = ("sdram", "jtag", "seg7", "seg_display", "de0_cv", "de0-cv")

_MODULAR_PLATFORM = "Insper-RISC-V/src/simulation/modular"


def write_modular_config(root: Path) -> None:
    """Escreve config.modular.yaml: a plataforma modular de simulação, com as fontes lidas do submódulo.

    As fontes são as de `config.platform-de0-cv.yaml` (o núcleo, os blocos comuns, as memórias, as caches e o
    interconector, na ordem de análise), sem o que é da SDRAM, do JTAG, do display e do topo da DE0-CV, mais o
    chip de RAM, o pacote do mapa e o topo modular, e o topo de simulação do ACT4 desta pasta.
    """
    # `riscv-tools platform sync` escreve a lista como itens `    - caminho` abaixo de `vhdl_sources:`.
    lines = (root / "tools/riscv_build/config.platform-de0-cv.yaml").read_text().splitlines()
    start = lines.index("  vhdl_sources:") + 1
    listed = []
    for line in lines[start:]:
        if not line.startswith("  - "):
            break
        listed.append(line[4:].strip())
    sources = [s for s in listed if not any(k in s for k in _NOT_MODULAR)]
    # ram_chip depende só dos blocos comuns; entra logo depois das memórias de simulação.
    at = sources.index(next(s for s in sources if s.endswith("rom_simulation.vhd"))) + 1
    sources.insert(at, "Insper-RISC-V/Memory/src/RAM/SoC/ram_chip.vhd")
    sources += [
        f"{_MODULAR_PLATFORM}/modular_map_pkg.vhd",
        f"{_MODULAR_PLATFORM}/modular_sim_top.vhd",
        "tools/riscv_build/act/sim/act_modular_top.vhd",
    ]
    listing = "".join(f"    - {s}\n" for s in sources)
    (root / "tools/riscv_build/config.modular.yaml").write_text(
        f"""# The ACT4 track on the modular simulation platform (Insper-RISC-V, src/simulation/modular): the ROM and the RAM of
# 1 MB each, inside the chip (integrated model) or behind the caches of 4 kbit (external model, for the
# profiles with Zifencei). Written by gen_profiles.py from config.platform-de0-cv.yaml; nobody edits it.
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
{listing}  # The images the harness writes for each ELF: the boot ROM is the first 4 KB of the code, the ROM the
  # code region and the RAM the data region.
  parameters:
    BOOT_ROM_FILE: "{{boot_hex_path}}"
    ROM_FILE: "{{hex_path}}"
    RAM_FILE: "{{ram_hex_path}}"

act:
  vendor_dir: vendor/riscv-arch-test
  jobs: 0
  # Where the data region of the ELFs starts (the RAM) and the size of the boot ROM.
  ram_base: 0x100000
  boot_rom_bytes: 0x1000
"""
    )
