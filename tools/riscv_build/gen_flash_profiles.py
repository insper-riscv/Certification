"""Generate the ACT4 targets of the profiles that run on the platform with the FLASH behind the caches.

Usage, from the root of the Certification repository, after gen_profiles.py:

    uv run python tools/riscv_build/gen_flash_profiles.py

For each profile with Zifencei (the SDRAM platforms) it writes tools/riscv_build/act/flash-<name>/
(the profile's UDB and test configuration, a linker script with the code in the FLASH and the data
in the SDRAM, and a Sail configuration with the extra FLASH region) and
tools/riscv_build/config.flash-<name>.yaml, to run with
`riscv-tools --config tools/riscv_build/config.flash-<name>.yaml certify`.
"""
import copy
import json
import re
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
rb = root / "tools/riscv_build"
template = rb / "act/rv32im-sdram-flash"

CACHE_SOURCES = [
    "../Memory/external/cache/dcache.vhd",
    "../Memory/external/cache/flash_chip.vhd",
    "../Memory/external/cache/flash_arbiter.vhd",
    "../Memory/external/cache/mem_region_router.vhd",
]

for cfg in sorted(rb.glob("config.profile-*.yaml")):
    name = cfg.name.removeprefix("config.profile-").removesuffix(".yaml")
    if "zifencei" not in name:
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

    c = cfg.read_text()
    c = c.replace(f"act/profile-{name}/", f"act/{tgt}/")
    c = c.replace("platforms/sdram/rtl/rv32im_sdram_sim_test.vhd", "platforms/sdram-flash/rtl/rv32im_sdram_flash_sim_test.vhd")
    c = c.replace("toplevel: rv32im_sdram_sim_test", "toplevel: rv32im_sdram_flash_sim_test")
    c = c.replace("    - ../Memory/external/cache/icache.vhd\n",
                  "    - ../Memory/external/cache/icache.vhd\n" + "".join(f"    - {s}\n" for s in CACHE_SOURCES))
    c = re.sub(r"  # Where the SDRAM starts:.*\n  sdram_base: (\S+)\n",
               "  # The code is in the FLASH, behind the caches, and the data in the SDRAM; the boot ROM jumps to the FLASH.\n"
               "  flash_base: 0x20000000\n  sdram_base: \\1\n", c)
    c = c.replace('    rom_addr_width: "9"', '    rom_addr_width: "18"')
    c = c.replace("# The ACT4 track", "# The ACT4 track on the platform with the FLASH behind the caches, ")
    (rb / f"config.flash-{name}.yaml").write_text(c)

    exts = re.search(r'extensions: "(.*)"', c).group(1)
    (rb / f"config.flash-board-{name}.yaml").write_text(
        f"""# The ACT4 ELFs of {tgt} on the board (DE0-CV): the platform with the FLASH behind the caches
# supplies the memory map, the JTAG device and the debug ports, and this file adds the ACT4 side. The
# code goes to the FLASH storage (132 KB) over the memory editor and the data to the SDRAM through the
# debug port. The board must be programmed with that platform.
#
#   uv run riscv-tools --config tools/riscv_build/config.flash-board-{name}.yaml certify-board --skip-build
extends: ../../../TopLevel/platforms/sdram-flash/config.yaml

act:
  vendor_dir: vendor/riscv-arch-test
  target_config: tools/riscv_build/act/{tgt}/test_config.yaml
  extensions: "{exts}"
  jobs: 0
  flash_base: 0x20000000
  # the words of the FLASH storage in the FPGA: an ELF whose code is larger is reported, not run
  flash_words: 33792
  sdram_base: 0x40000000
  sdram_region_bytes: 0x100000
  board_timeout_s: 30
  board_display: true
"""
    )

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
    for kind in ("config.flash-", "config.flash-board-"):
        src_cfg = (rb / f"{kind}{name}.yaml").read_text()
        src_cfg = src_cfg.replace(f"act/{tgt}/", f"act/{rtgt}/")
        src_cfg = re.sub(r'extensions: ".*"', 'extensions: "Zifencei"', src_cfg)
        (rb / f"{kind.replace('flash-', 'flash-ram-')}{name}.yaml").write_text(src_cfg)
    print(name, "->", tgt)
