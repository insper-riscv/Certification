"""Generate the ACT4 targets of the profiles with Zifencei, which run with the ROM and the RAM behind the caches.

Usage, from the root of the Certification repository, after gen_profiles.py:

    uv run python tools/riscv_build/gen_flash_profiles.py

FENCE.I invalidates the instruction cache, so a profile with Zifencei needs the external model of the modular
simulation platform: the code in the ROM (a FLASH chip behind the instruction cache) and the data in the RAM
(a chip behind the data cache). For each of these profiles it writes tools/riscv_build/act/flash-<name>/ (the
profile's target with the linker script of the template), tools/riscv_build/act/flash-ram-<name>/ (the variant
of the Zifencei test, whose body runs from the RAM) and tools/riscv_build/config.flash-<name>.yaml and
config.flash-ram-<name>.yaml, to run with
`riscv-tools --config tools/riscv_build/config.flash-<name>.yaml certify`.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_params import extension_list, is_e, parameter_lines, variants

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
rb = root / "tools/riscv_build"
template = rb / "act/rv32im-min"


def sim_config(target: str, extensions: str, params: str, ram_variant: bool, rtgt: str, e_base: bool) -> str:
    """Escreve o config de simulação de um alvo na plataforma modular com a ROM e a RAM atrás das caches."""
    ram_lines = "" if ram_variant else (
        "  # tests that rewrite their own code run from the variant, with the body in the RAM\n"
        "  ram_tests: [Zifencei-fence.i-00]\n"
        f"  ram_target_config: tools/riscv_build/act/{rtgt}/test_config.yaml\n"
        '  ram_extensions: "Zifencei"\n'
    )
    isa = "isa:\n  base: e\n\n" if e_base else ""
    return (
        f"# The ACT4 track of {target} on the modular platform with the ROM and the RAM behind the caches: the\n"
        "# platform (config.modular.yaml) with the target, the extensions and the hardware of the profile.\n"
        "#\n"
        f"#   uv run riscv-tools --config tools/riscv_build/config.{target}.yaml certify\n"
        "extends: config.modular.yaml\n"
        "\n"
        f"{isa}"
        "sim:\n"
        "  parameters:\n"
        # the code of the ELF from address 0 is also the image of the boot ROM, which holds its first 4 KB
        '    BOOT_ROM_FILE: "{hex_path}"\n'
        '    ROM_FILE: "{hex_path}"\n'
        '    RAM_FILE: "{sdram_hex_path}"\n'
        '    ROM_EXTERNAL: "true"\n'
        '    RAM_EXTERNAL: "true"\n'
        f"{params}"
        "\n"
        "act:\n"
        f"  target_config: tools/riscv_build/act/{target}/test_config.yaml\n"
        f'  extensions: "{extensions}"\n'
        f"{ram_lines}"
        "  # The code is in the ROM, behind the instruction cache, and the data in the RAM, behind the data cache; the\n"
        "  # images start at the address 0 of the ROM (the boot ROM stub is in the first 4 KB) and at the base of the RAM.\n"
        "  flash_base: 0x0\n"
        "  sdram_base: 0x100000\n"
    )


for name, ext in variants(root):
    if "Zifencei" not in ext:
        continue
    src = rb / "act" / f"profile-{name}"
    tgt = f"flash-{name}"
    rtgt = f"flash-ram-{name}"
    exts = ",".join(extension_list(ext, name))
    params = parameter_lines(ext, name)

    for target, linker in ((tgt, "link.ld"), (rtgt, "link-ram.ld")):
        dst = rb / "act" / target
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        (dst / f"profile-{name}.yaml").rename(dst / f"{target}.yaml")
        shutil.copyfile(template / linker, dst / "link.ld")
        for fname in (f"{target}.yaml", "test_config.yaml", "run_cmd.txt"):
            f = dst / fname
            if f.exists():
                f.write_text(f.read_text().replace(f"profile-{name}", target))

    (rb / f"config.{tgt}.yaml").write_text(sim_config(tgt, exts, params, False, rtgt, is_e(name)))
    (rb / f"config.{rtgt}.yaml").write_text(sim_config(rtgt, "Zifencei", params, True, rtgt, is_e(name)))
    print(name, "->", tgt)
