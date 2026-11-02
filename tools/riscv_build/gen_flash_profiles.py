"""Generate the ACT4 targets of the profiles that run on the platform with the FLASH behind the caches.

Usage, from the root of the Certification repository, after gen_profiles.py:

    uv run python tools/riscv_build/gen_flash_profiles.py

For each profile with Zifencei it writes tools/riscv_build/act/flash-<name>/ (the profile's UDB and
test configuration, a linker script with the code in the FLASH and the data in the SDRAM, and a Sail
configuration with the extra FLASH region) and tools/riscv_build/config.flash-<name>.yaml, to run with
`riscv-tools --config tools/riscv_build/config.flash-<name>.yaml certify`. The configs extend
config.platform-de0-cv.yaml, the platform with the FLASH behind the caches, which `riscv-tools platform
sync` writes from the Insper-RISC-V submodule.
"""
import copy
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_params import extension_list, parameter_lines, variants

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
rb = root / "tools/riscv_build"
template = rb / "act/rv32im-sdram-flash"

for name, ext in variants(root):
    if "Zifencei" not in ext:
        continue
    src = rb / "act" / f"profile-{name}"
    tgt = f"flash-{name}"
    dst = rb / "act" / tgt
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    (dst / f"profile-{name}.yaml").rename(dst / f"{tgt}.yaml")
    shutil.copyfile(template / "link.ld", dst / "link.ld")

    for fname in (f"{tgt}.yaml", "test_config.yaml", "run_cmd.txt"):
        f = dst / fname
        if f.exists():
            f.write_text(f.read_text().replace(f"profile-{name}", tgt))

    sj = json.loads((dst / "sail.json").read_text())
    sdram = next(r for r in sj["memory"]["regions"] if r["attributes"]["mem_type"] == "MainMemory")
    flash = copy.deepcopy(sdram)
    flash["base"]["value"] = "0x20000000"
    flash["size"]["value"] = "0x100000"
    # Sail accepts a main memory only if it is writable; the programs never store to the code region
    sj["memory"]["regions"].append(flash)
    sj["memory"]["regions"].sort(key=lambda r: int(r["base"]["value"], 16))
    (dst / "sail.json").write_text(json.dumps(sj, indent=2))

    exts = ",".join(extension_list(ext))
    rtgt = f"flash-ram-{name}"
    params = parameter_lines(ext)

    def sim_config(target: str, extensions: str, ram_variant: bool) -> str:
        """Escreve o config de simulação de um alvo na plataforma com a FLASH atrás das caches."""
        ram_lines = "" if ram_variant else (
            "  # tests that rewrite their own code run from the variant, with the body in the SDRAM\n"
            "  ram_tests: [Zifencei-fence.i-00]\n"
            f"  ram_target_config: tools/riscv_build/act/{rtgt}/test_config.yaml\n"
            '  ram_extensions: "Zifencei"\n'
        )
        return (
            f"# The ACT4 track of {target} on the platform with the FLASH behind the caches: the platform\n"
            "# (config.platform-de0-cv.yaml) with the target, the extensions and the hardware of the profile.\n"
            "#\n"
            f"#   uv run riscv-tools --config tools/riscv_build/config.{target}.yaml certify\n"
            "extends: config.platform-de0-cv.yaml\n"
            "\n"
            "paths:\n"
            "  build_dir: build\n"
            "\n"
            "sim:\n"
            "  parameters:\n"
            '    BOOT_ROM_FILE: "{boot_hex_path}"\n'
            '    ROM_FILE: "{hex_path}"\n'
            '    SDRAM_FILE: "{sdram_hex_path}"\n'
            f"{params}"
            "\n"
            "act:\n"
            "  vendor_dir: vendor/riscv-arch-test\n"
            f"  target_config: tools/riscv_build/act/{target}/test_config.yaml\n"
            f'  extensions: "{extensions}"\n'
            "  jobs: 0\n"
            f"{ram_lines}"
            "  # The code is in the FLASH, behind the caches, and the data in the SDRAM; the boot ROM jumps to the FLASH.\n"
            "  flash_base: 0x20000000\n"
            "  sdram_base: 0x40000000\n"
            "  sim_parameters:\n"
            '    rom_addr_width: "18"\n'
            '    ram_addr_width: "9"\n'
        )

    def board_config(target: str, extensions: str, ram_variant: bool) -> str:
        """Escreve o config do alvo na placa (DE0-CV): a plataforma dá o mapa de memória e o JTAG."""
        ram_lines = "" if ram_variant else (
            "  # tests that rewrite their own code run from the variant, with the body in the SDRAM\n"
            "  ram_tests: [Zifencei-fence.i-00]\n"
            f"  ram_target_config: tools/riscv_build/act/{rtgt}/test_config.yaml\n"
            '  ram_extensions: "Zifencei"\n'
        )
        return (
            f"# The ACT4 ELFs of {target} on the board (DE0-CV): the platform with the FLASH behind the caches\n"
            "# supplies the memory map, the JTAG device and the debug ports, and this file adds the ACT4 side. The\n"
            "# code goes to the FLASH storage (132 KB) over the memory editor and the data to the SDRAM through the\n"
            "# debug port. The board must be programmed with that platform.\n"
            "#\n"
            f"#   uv run riscv-tools --config tools/riscv_build/config.{'flash-ram-board-' + name if ram_variant else 'flash-board-' + name}.yaml certify-board --skip-build\n"
            "extends: config.platform-de0-cv.yaml\n"
            "\n"
            "paths:\n"
            "  build_dir: build\n"
            "\n"
            "act:\n"
            "  vendor_dir: vendor/riscv-arch-test\n"
            f"  target_config: tools/riscv_build/act/{target}/test_config.yaml\n"
            f'  extensions: "{extensions}"\n'
            "  jobs: 0\n"
            f"{ram_lines}"
            "  flash_base: 0x20000000\n"
            "  # the words of the FLASH storage in the FPGA: an ELF whose code is larger is reported, not run\n"
            "  flash_words: 33792\n"
            "  sdram_base: 0x40000000\n"
            "  sdram_region_bytes: 0x100000\n"
            "  board_timeout_s: 30\n"
            "  board_display: true\n"
        )

    (rb / f"config.flash-{name}.yaml").write_text(sim_config(tgt, exts, ram_variant=False))
    (rb / f"config.flash-board-{name}.yaml").write_text(board_config(tgt, exts, ram_variant=False))

    # The Zifencei test rewrites its own code, which a FLASH ignores: its body runs from the SDRAM.
    rtgt = f"flash-ram-{name}"
    rdst = rb / "act" / rtgt
    if rdst.exists():
        shutil.rmtree(rdst)
    shutil.copytree(dst, rdst)
    (rdst / f"{tgt}.yaml").rename(rdst / f"{rtgt}.yaml")
    shutil.copyfile(template / "link-ram.ld", rdst / "link.ld")
    for fname in (f"{rtgt}.yaml", "test_config.yaml", "run_cmd.txt"):
        f = rdst / fname
        if f.exists():
            f.write_text(f.read_text().replace(tgt, rtgt))
    (rb / f"config.flash-ram-{name}.yaml").write_text(sim_config(rtgt, "Zifencei", ram_variant=True))
    (rb / f"config.flash-ram-board-{name}.yaml").write_text(board_config(rtgt, "Zifencei", ram_variant=True))
    print(name, "->", tgt)
