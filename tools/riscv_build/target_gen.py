"""Escreve o alvo ACT4 de um perfil: o UDB, a configuração do Sail, o test_config e o config do `certify`.

O alvo de um perfil (UDB, `sail.json`, `test_config.yaml` e o linker) não depende do modelo de memória: o mapa
é o mesmo (BOOT_MEMORY, ROM e RAM de 1 MB) e a ROM e a RAM só mudam de lugar dentro do chip simulado. O que muda
com o modelo de memória é o config do `certify`: os genéricos `ROM_EXTERNAL` e `RAM_EXTERNAL` e a forma das
imagens e do testbench. `gen_profiles.py` e `gen_flash_profiles.py` usam estas funções para os configs
versionados, e `gen_profiles.py --profile P --memory Y --out DIR` para um alvo gerado em tempo de execução.
"""

import json
import os
import re
import shutil
from pathlib import Path

from memory_models import MemoryModel
from profile_params import extension_list, has_csr, is_e, parameter_lines

# Alvo-modelo que todo perfil copia.
BASE = "rv32im-min"

# As extensões do núcleo fora da matriz, com a versão que o UDB do ACT4 declara para cada uma.
_EXTRA_VERSIONS = {
    "Zimop": "= 1.0.0",
    "Zicond": "= 1.0",
    "Zihintntl": "= 1.0.0",
    "Zihintpause": "= 2.0.0",
}


def write_target(rb: Path, name: str, ext: set[str], dst: Path, tgt: str, rel: str | None = None) -> None:
    """Copia o alvo-modelo para `dst` e o ajusta ao perfil.

    Parameters
    ----------
    rb : Path
        A pasta `tools/riscv_build` do repositório, onde está `act/rv32im-min`.
    name : str
        Nome do perfil (`rv32im_zicntr`); a base `rv32e` vem do prefixo.
    ext : set of str
        As extensões do perfil.
    dst : Path
        Pasta do alvo; se existe, é apagada antes.
    tgt : str
        Nome do alvo, que vai nos campos `name` do UDB e do test_config.
    rel : str, optional
        Caminho de `dst` a partir da raiz do repositório, que o `run_cmd.txt` cita; sem ele, o alvo é
        `tools/riscv_build/act/<tgt>`.
    """
    csr = has_csr(ext)
    base = BASE
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(rb / "act" / base, dst)
    (dst / f"{base}.yaml").rename(dst / f"{tgt}.yaml")

    # UDB
    y = (dst / f"{tgt}.yaml").read_text()
    y = y.replace(f"name: {base}", f"name: {tgt}")
    if is_e(name):
        # The UDB of the published gems has no E extension; act/udb-overlay declares it, and
        # install_udb_overlay.sh puts that folder in the gem as the overlay named rv32e.
        y = y.replace("type: fully configured", "type: fully configured\narch_overlay: rv32e", 1)
    y = re.sub(r"description: >-\n.*?\n(?=implemented_extensions)", f"description: >-\n  {name}, machine mode only.\n", y, flags=re.DOTALL)
    # The RV32E profiles declare the E base (16 registers) in place of I.
    lst = ['  - { name: E, version: "= 2.0.0" }' if is_e(name) else '  - { name: I, version: "= 2.1" }']
    if "M" in ext:
        lst += ['  - { name: M, version: "= 2.0" }', '  - { name: Zmmul, version: "= 1.0.0" }']
    if "Zmmul" in ext:
        lst += ['  - { name: Zmmul, version: "= 1.0.0" }']
    # The UDB schema cannot describe a fully configured core without Sm (it needs MXLEN), and Sm
    # needs Zicsr, so every target declares both. Which tests are generated follows `extensions`
    # of the certify config, and the priv tests are off without Zicsr.
    lst += ['  - { name: Zicsr, version: "= 2.0" }', '  - { name: Sm, version: "= 1.12.0" }']
    if "Zicntr" in ext:
        lst += ['  - { name: Zicntr, version: "= 2.0" }']
        # The time CSR exists: the core counts it itself, from a divider of its clock.
        y = y.replace("  MCOUNTINHIBIT_IMPLEMENTED: false", "  MCOUNTINHIBIT_IMPLEMENTED: false\n  TIME_CSR_IMPLEMENTED: true")
    if "Zihpm" in ext:
        lst += ['  - { name: Zihpm, version: "= 2.0.0" }']
    if "Zifencei" in ext:
        lst += ['  - { name: Zifencei, version: "= 2.0" }']
    for extra, version in _EXTRA_VERSIONS.items():
        if extra in ext:
            lst += [f'  - {{ name: {extra}, version: "{version}" }}']
    if "Zicclsm" in ext:
        # The core runs misaligned loads and stores in the RAM and the SDRAM.
        lst += ['  - { name: Zicclsm, version: "= 1.0.0" }']
        y = y.replace("MISALIGNED_LDST: false", "MISALIGNED_LDST: true\n  MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE: 4\n  MISALIGNED_SPLIT_STRATEGY: sequential_bytes")
    # mcountinhibit exists with Zicntr or Zihpm: mcycle (bit 0), minstret (bit 2) and one bit per event counter
    # (bits 3 to 6). The event counters are the indices 3 to 6; every counter is 64 bits wide.
    if "Zicntr" in ext or "Zihpm" in ext:
        inhibit = [i in ((0, 2) if "Zicntr" in ext else ()) or (i in (3, 4, 5, 6) and "Zihpm" in ext) for i in range(32)]
        y = y.replace("  MCOUNTINHIBIT_IMPLEMENTED: false", "  MCOUNTINHIBIT_IMPLEMENTED: true\n  COUNTINHIBIT_EN: [" + ", ".join(str(b).lower() for b in inhibit) + "]")
    if "Zihpm" in ext:
        en = [i in (3, 4, 5, 6) for i in range(32)]
        y = re.sub(r"  HPM_COUNTER_EN: \[.*?\]\n", "  HPM_COUNTER_EN: [" + ", ".join(str(b).lower() for b in en) + "]\n", y, flags=re.DOTALL)
        y = y.replace("  MCOUNTINHIBIT_IMPLEMENTED: true", "".join(f"  HPM_COUNTER{n}_WIDTH: 64\n" for n in (3, 4, 5, 6)) + "  HPM_EVENTS: [0, 1, 2, 3, 4, 5, 6, 7, 8]\n  MCOUNTINHIBIT_IMPLEMENTED: true")
    y = re.sub(r"implemented_extensions:\n(?:  - .*\n)+", "implemented_extensions:\n" + "\n".join(lst) + "\n", y)
    if "M" not in ext:
        y = re.sub(r"  # MISA.*\n  MUTABLE_MISA_M: false\n", "  # MISA\n", y)
    (dst / f"{tgt}.yaml").write_text(y)

    # Sail
    sj = json.loads((dst / "sail.json").read_text())
    flags = {"M": "M" in ext, "Zmmul": "M" in ext or "Zmmul" in ext, "Zicsr": csr, "Zicntr": "Zicntr" in ext, "Zihpm": "Zihpm" in ext, "Zifencei": "Zifencei" in ext}
    flags["Zicclsm"] = "Zicclsm" in ext
    flags.update({extra: extra in ext for extra in _EXTRA_VERSIONS})
    sj["base"]["E"] = is_e(name)
    for k, v in flags.items():
        sj["extensions"].setdefault(k, {})["supported"] = v
    if "Zicntr" in ext or "Zihpm" in ext:
        bits = (0x5 if "Zicntr" in ext else 0) | (0x78 if "Zihpm" in ext else 0)
        sj["base"]["mcountinhibit"] = {"supported": True, "writable_bits": {"len": 32, "value": f"{bits:#x}"}}
    if "Zihpm" in ext:
        sj["base"]["writable_hpm_counters"] = {"len": 32, "value": "0x78"}
        sj["base"]["hpmevent_width_bits"] = 4
    if "Zicclsm" in ext:
        # The main memory (RAM and SDRAM) runs a misaligned access; the flash and the peripherals still raise it.
        sj["memory"]["misaligned"]["exceptions"]["load_store"] = {"None": None}
        for region in sj["memory"]["regions"]:
            if region["attributes"]["mem_type"] == "MainMemory":
                region["attributes"]["misaligned_exceptions"]["load_store"] = {"None": None}
    (dst / "sail.json").write_text(json.dumps(sj, indent=2))

    # test_config
    t = (dst / "test_config.yaml").read_text()
    t = t.replace(f"name: {base}", f"name: {tgt}").replace(f"udb_config: {base}.yaml", f"udb_config: {tgt}.yaml")
    t = re.sub(r"include_priv_tests: \w+", f"include_priv_tests: {'True' if csr else 'False'}", t)
    (dst / "test_config.yaml").write_text(t)
    if (dst / "run_cmd.txt").exists():
        (dst / "run_cmd.txt").write_text((dst / "run_cmd.txt").read_text().replace(f"tools/riscv_build/act/{base}", rel or f"tools/riscv_build/act/{tgt}"))


def _relative(path: Path, root: Path) -> str:
    """Escreve o caminho a partir da raiz do repositório, ou o absoluto se ele está fora da raiz.

    Parameters
    ----------
    path : Path
        O caminho.
    root : Path
        A raiz do repositório.

    Returns
    -------
    str
        O caminho em formato POSIX.
    """
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def write_generated(root: Path, out: Path, name: str, ext: set[str], model: MemoryModel, jobs: int | None) -> Path:
    """Gera, sem versionar, o alvo ACT4 de um perfil para um modelo de memória e o config do `certify`.

    O alvo é o do perfil (UDB, `sail.json`, `test_config.yaml` e o linker); o config estende
    `config.modular.yaml` e acrescenta os genéricos do perfil e do modelo de memória. Com a RAM externa,
    o config usa as imagens e o testbench da plataforma com o chip de RAM (`flash_base` e `sdram_base`); com
    a RAM interna, o testbench observa o barramento da RAM do núcleo. Um perfil com Zifencei roda o
    `Zifencei-fence.i-00` a partir da variante com o corpo do teste na RAM, como os configs versionados.

    Parameters
    ----------
    root : Path
        Raiz do repositório.
    out : Path
        Pasta que recebe `act/<alvo>/` e `config.yaml`.
    name : str
        Nome do perfil.
    ext : set of str
        As extensões do perfil.
    model : MemoryModel
        O modelo de memória, já validado por `memory_models.problems`.
    jobs : int or None
        Paralelismo do `make` do ACT4 (`act.jobs`); `None` deixa o que o `config.modular.yaml` diz (0, automático).

    Returns
    -------
    Path
        O `config.yaml` gerado, para o `riscv-tools --config`.
    """
    rb = root / "tools/riscv_build"
    tgt = f"{name}__{model.slug}"
    target = out / "act" / tgt
    write_target(rb, name, ext, target, tgt, _relative(target, root))
    exts = ",".join(extension_list(ext, name))
    ram_variant = "Zifencei" in ext and not is_e(name)
    ram_lines = ""
    if ram_variant:
        ram = out / "act" / f"{tgt}-ram"
        write_target(rb, name, ext, ram, f"{tgt}-ram", _relative(ram, root))
        shutil.copyfile(rb / "act" / BASE / "link-ram.ld", ram / "link.ld")
        ram_lines = (
            "  # tests that rewrite their own code run from the variant, with the body in the RAM\n"
            "  ram_tests: [Zifencei-fence.i-00]\n"
            f"  ram_target_config: {_relative(ram / 'test_config.yaml', root)}\n"
            '  ram_extensions: "Zifencei"\n'
        )
    images = ""
    place = ""
    if model.ram_external:
        # the chip of the RAM holds the data image, and the testbench reads the tohost word from it
        images = (
            '    BOOT_MEMORY_FILE: "{hex_path}"\n'
            '    ROM_FILE: "{hex_path}"\n'
            '    RAM_FILE: "{sdram_hex_path}"\n'
        )
        place = "  flash_base: 0x0\n  sdram_base: 0x100000\n"
    isa = "isa:\n  base: e\n\n" if is_e(name) else ""
    jobs_line = f"  jobs: {jobs}\n" if jobs is not None else ""
    base = Path(root / "tools/riscv_build/config.modular.yaml")
    config = out / "config.yaml"
    config.write_text(
        f"# The ACT4 track of {name} on the modular platform with {model.spec}, generated at run time by\n"
        "# gen_profiles.py (nothing of this folder is versioned): the platform (config.modular.yaml) with the\n"
        "# target, the extensions and the hardware of the profile.\n"
        "#\n"
        f"#   riscv-tools --config {_relative(config, root)} certify\n"
        f"extends: {Path(os.path.relpath(base, out)).as_posix()}\n"
        "\n"
        f"{isa}"
        "sim:\n"
        "  parameters:\n"
        f"{images}"
        f'    ROM_EXTERNAL: "{str(model.rom_external).lower()}"\n'
        f'    RAM_EXTERNAL: "{str(model.ram_external).lower()}"\n'
        f"{parameter_lines(ext, name)}"
        "\n"
        "act:\n"
        f"{jobs_line}"
        f"  target_config: {_relative(target / 'test_config.yaml', root)}\n"
        f'  extensions: "{exts}"\n'
        f"{ram_lines}"
        f"{place}"
    )
    return config


# O mapa da placa DE0-CV: a FLASH de 252 KB a partir de 0x1000 e a SDRAM a partir de 0x40000000, de que o ACT4 usa 1 MB.
_BOARD_FLASH = (0x1000, 0x3F000)
_BOARD_SDRAM = (0x40000000, 0x100000)


def _board_region(region: dict, base: int, size: int) -> dict:
    """Devolve uma cópia da região de memória principal do Sail com outro endereço e tamanho."""
    copy = json.loads(json.dumps(region))
    copy["base"]["value"] = f"{base:#x}"
    copy["size"]["value"] = f"{size:#x}"
    return copy


def write_board_target(rb: Path, name: str, ext: set[str], dst: Path, tgt: str, rel: str | None = None, ram_variant: bool = False) -> None:
    """Escreve o alvo ACT4 de um perfil para o mapa da placa DE0-CV.

    É o alvo da plataforma modular (`write_target`) com três trocas: o linker, que põe o código e as constantes na FLASH
    (a partir de 0x1200, depois da página de cabeçalho da banca e do payload) e os dados, a pilha e o HTIF na SDRAM em
    0x40000000; o `rvmodel_macros.h`, que ao terminar salta para a espera de reinício da boot memory; e as regiões de
    memória do Sail.

    Parameters
    ----------
    rb : Path
        A pasta `tools/riscv_build` do repositório.
    name, ext, dst, tgt, rel
        Como em `write_target`.
    ram_variant : bool
        Usa o linker da variante em que o corpo do teste fica na SDRAM (os testes que reescrevem o próprio código).
    """
    write_target(rb, name, ext, dst, tgt, rel)
    template = rb / "act" / "board-template"
    shutil.copyfile(template / ("link-ram.ld" if ram_variant else "link.ld"), dst / "link.ld")
    (dst / "link-ram.ld").unlink(missing_ok=True)
    shutil.copyfile(template / "rvmodel_macros.h", dst / "rvmodel_macros.h")
    sj = json.loads((dst / "sail.json").read_text())
    main = next(r for r in sj["memory"]["regions"] if r["attributes"]["mem_type"] == "MainMemory")
    sdram = _board_region(main, *_BOARD_SDRAM)
    main["base"]["value"] = f"{_BOARD_FLASH[0]:#x}"
    main["size"]["value"] = f"{_BOARD_FLASH[1]:#x}"
    sj["memory"]["regions"].append(sdram)
    (dst / "sail.json").write_text(json.dumps(sj, indent=2))


def write_board(root: Path, out: Path, name: str, ext: set[str], jobs: int | None) -> Path:
    """Gera, sem versionar, o alvo ACT4 de um perfil para a placa DE0-CV e o config do `certify-board`.

    O config estende `config.platform-de0-cv.yaml`, que traz o mapa, o dispositivo JTAG e as portas de depuração, e
    acrescenta o lado do ACT4: o código vai para a FLASH pela banca A (cabeçalho, payload que salta para
    `flash_entry` e o código) e os dados para a SDRAM pela porta de depuração. Um perfil com Zifencei roda o
    `Zifencei-fence.i-00` da variante com o corpo do teste na SDRAM.

    Parameters
    ----------
    root, out, name, ext, jobs
        Como em `write_generated`.

    Returns
    -------
    Path
        O `config.yaml` gerado, para o `riscv-tools --config`.
    """
    rb = root / "tools/riscv_build"
    tgt = f"{name}__board"
    target = out / "act" / tgt
    write_board_target(rb, name, ext, target, tgt, _relative(target, root))
    ram_lines = ""
    if "Zifencei" in ext:
        ram = out / "act" / f"{tgt}-ram"
        write_board_target(rb, name, ext, ram, f"{tgt}-ram", _relative(ram, root), ram_variant=True)
        ram_lines = (
            "  # tests that rewrite their own code run from the variant, with the body in the SDRAM\n"
            "  ram_tests: [Zifencei-fence.i-00]\n"
            f"  ram_target_config: {_relative(ram / 'test_config.yaml', root)}\n"
            '  ram_extensions: "Zifencei"\n'
        )
    jobs_line = f"  jobs: {jobs}\n" if jobs is not None else ""
    base = rb / "config.platform-de0-cv.yaml"
    config = out / "config.yaml"
    config.write_text(
        f"# The ACT4 track of {name} on the DE0-CV board, generated at run time by gen_profiles.py --board\n"
        "# (nothing of this folder is versioned): the platform of the board with the target of the profile.\n"
        "#\n"
        f"#   riscv-tools --config {_relative(config, root)} certify-board\n"
        f"extends: {Path(os.path.relpath(base, out)).as_posix()}\n"
        "\n"
        "paths:\n"
        "  build_dir: build\n"
        "\n"
        "act:\n"
        "  vendor_dir: vendor/riscv-arch-test\n"
        f"{jobs_line}"
        f"  target_config: {_relative(target / 'test_config.yaml', root)}\n"
        f'  extensions: "{",".join(extension_list(ext, name))}"\n'
        f"{ram_lines}"
        "  # the bank A (flash.banks of the platform) starts with the header page and the payload that jumps to the entry\n"
        "  flash_base: 0x1000\n"
        "  flash_bank: A\n"
        "  flash_entry: 0x1200\n"
        "  # the words of the FLASH storage in the FPGA (addressed raw from 0, 256 KB): a larger ELF is reported, not run\n"
        "  flash_words: 65536\n"
        "  sdram_base: 0x40000000\n"
        "  sdram_region_bytes: 0x100000\n"
        "  board_timeout_s: 30\n"
        "  board_display: true\n"
    )
    return config
