"""Generate the ACT4 targets of the RV32 profiles (I plus any valid combination of M, Zmmul, Zicsr, Zicntr, Zihpm, Zifencei and Zicclsm).


Usage, from the root of the Certification repository:

    uv run python tools/riscv_build/gen_profiles.py

For each profile it writes tools/riscv_build/act/profile-<name>/ (UDB, Sail configuration and
test configuration) and tools/riscv_build/config.profile-<name>.yaml, to run with
`riscv-tools --config tools/riscv_build/config.profile-<name>.yaml certify`. A profile with
Zifencei needs the caches and has no config here (gen_flash_profiles.py writes it, for the platform with the ROM
and the RAM behind the caches); the others extend config.modular.yaml.
"""
import json, re, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_params import extension_list, has_csr, is_e, parameter_lines, variants, write_modular_config

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
rb = root / "tools/riscv_build"

# The profiles come from the specification of the core (riscv-tools profiles), which is in the
# Insper-RISC-V submodule (profile_params.py).
VARIANTS = variants(root)
write_modular_config(root)

for name, ext in VARIANTS:
    zifencei = "Zifencei" in ext
    csr = has_csr(ext)
    base = "rv32im-min"
    tgt = f"profile-{name}"
    dst = rb / "act" / tgt
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
    y = re.sub(r"description: >-\n.*?\n(?=implemented_extensions)", f"description: >-\n  {name}, machine mode only.\n", y, flags=re.S)
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
        y = re.sub(r"  HPM_COUNTER_EN: \[.*?\]\n", "  HPM_COUNTER_EN: [" + ", ".join(str(b).lower() for b in en) + "]\n", y, flags=re.S)
        y = y.replace("  MCOUNTINHIBIT_IMPLEMENTED: true", "".join(f"  HPM_COUNTER{n}_WIDTH: 64\n" for n in (3, 4, 5, 6)) + "  HPM_EVENTS: [0, 1, 2, 3, 4, 5, 6, 7, 8]\n  MCOUNTINHIBIT_IMPLEMENTED: true")
    y = re.sub(r"implemented_extensions:\n(?:  - .*\n)+", "implemented_extensions:\n" + "\n".join(lst) + "\n", y)
    if "M" not in ext:
        y = re.sub(r"  # MISA.*\n  MUTABLE_MISA_M: false\n", "  # MISA\n", y)
    (dst / f"{tgt}.yaml").write_text(y)

    # Sail
    sj = json.loads((dst / "sail.json").read_text())
    flags = {"M": "M" in ext, "Zmmul": "M" in ext or "Zmmul" in ext, "Zicsr": csr, "Zicntr": "Zicntr" in ext, "Zihpm": "Zihpm" in ext, "Zifencei": "Zifencei" in ext}
    flags["Zicclsm"] = "Zicclsm" in ext
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
        (dst / "run_cmd.txt").write_text((dst / "run_cmd.txt").read_text().replace(base, tgt))

    # certify config: the profile on the modular platform with the memories inside the chip
    # (config.modular.yaml) and only what is the profile's. A profile with Zifencei needs the caches:
    # it runs with the FLASH and the RAM behind them (gen_flash_profiles.py), so it has no config here.
    exts = extension_list(ext, name)
    # RV32E: the toolchain builds with -march=rv32e and -mabi=ilp32e
    isa_lines = "\nisa:\n  base: e\n" if is_e(name) else ""
    config = rb / f"config.profile-{name}.yaml"
    if zifencei:
        config.unlink(missing_ok=True)
        print(name, base, ",".join(exts), "(config: gen_flash_profiles.py)")
        continue
    config.write_text(
        f"""# The ACT4 track of the profile {name} on the modular platform with the memories inside the chip:
# config.modular.yaml with the target, the extensions and the hardware of the profile.
#
#   uv run riscv-tools --config tools/riscv_build/config.profile-{name}.yaml certify
extends: config.modular.yaml
{isa_lines}
sim:
  parameters:
{parameter_lines(ext, name)}
act:
  target_config: tools/riscv_build/act/{tgt}/test_config.yaml
  extensions: "{",".join(exts)}"
"""
    )
    print(name, base, ",".join(exts))
