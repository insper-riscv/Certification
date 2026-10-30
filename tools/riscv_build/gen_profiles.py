"""Generate the ACT4 targets of the RV32 profiles (I plus any valid combination of M, Zmmul, Zicsr, Zicntr, Zifencei and Zicclsm).


Usage, from the root of the Certification repository:

    uv run python tools/riscv_build/gen_profiles.py

For each profile it writes tools/riscv_build/act/profile-<name>/ (UDB, Sail configuration and
test configuration) and tools/riscv_build/config.profile-<name>.yaml, to run with
`riscv-tools --config tools/riscv_build/config.profile-<name>.yaml certify`. A profile with
Zifencei uses the SDRAM platform (config.sdram.yaml); the others use the plain one (config.yaml).
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
rb = root / "tools/riscv_build"

# The profiles come from the specification of the core (riscv-tools profiles). One without Zicclsm
# does not declare it, leaves MISALIGNED_LDST off and runs the core with has_zicclsm = false. Zicntr
# implies Zicsr: the hardware turns on both, and the ISA string and the lists of tests cite both.
SPEC = root.parent / "Core/profiles/matrix.yaml"
_listing = subprocess.run(
    ["uv", "run", "riscv-tools", "profiles", "--spec", str(SPEC), "--format", "json"],
    cwd=root, check=True, capture_output=True, text=True,
).stdout
VARIANTS = [(p["name"], set(p["extensions"])) for p in json.loads(_listing)]

for name, ext in VARIANTS:
    sdram = "Zifencei" in ext
    csr = "Zicsr" in ext or "Zicntr" in ext
    base = "rv32im-sdram" if sdram else "rv32im-min"
    tgt = f"profile-{name}"
    dst = rb / "act" / tgt
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(rb / "act" / base, dst)
    (dst / f"{base}.yaml").rename(dst / f"{tgt}.yaml")

    # UDB
    y = (dst / f"{tgt}.yaml").read_text()
    y = y.replace(f"name: {base}", f"name: {tgt}")
    y = re.sub(r"description: >-\n.*?\n(?=implemented_extensions)", f"description: >-\n  {name}, machine mode only.\n", y, flags=re.S)
    lst = ['  - { name: I, version: "= 2.1" }']
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
    if "Zifencei" in ext:
        lst += ['  - { name: Zifencei, version: "= 2.0" }']
    if "Zicclsm" in ext:
        # The core runs misaligned loads and stores in the RAM and the SDRAM.
        lst += ['  - { name: Zicclsm, version: "= 1.0.0" }']
        y = y.replace("MISALIGNED_LDST: false", "MISALIGNED_LDST: true\n  MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE: 4\n  MISALIGNED_SPLIT_STRATEGY: sequential_bytes")
    y = re.sub(r"implemented_extensions:\n(?:  - .*\n)+", "implemented_extensions:\n" + "\n".join(lst) + "\n", y)
    if "M" not in ext:
        y = re.sub(r"  # MISA.*\n  MUTABLE_MISA_M: false\n", "  # MISA\n", y)
    (dst / f"{tgt}.yaml").write_text(y)

    # Sail
    sj = json.loads((dst / "sail.json").read_text())
    flags = {"M": "M" in ext, "Zmmul": "M" in ext or "Zmmul" in ext, "Zicsr": csr, "Zicntr": "Zicntr" in ext, "Zifencei": "Zifencei" in ext}
    flags["Zicclsm"] = "Zicclsm" in ext
    for k, v in flags.items():
        sj["extensions"].setdefault(k, {})["supported"] = v
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

    # certify config
    cfg_src = rb / ("config.sdram.yaml" if sdram else "config.yaml")
    c = cfg_src.read_text()
    c = re.sub(r"target_config: .*", f"target_config: tools/riscv_build/act/{tgt}/test_config.yaml", c)
    exts = ["I"] + (["M"] if "M" in ext else []) + (["Zmmul"] if ("Zmmul" in ext or "M" in ext) else []) + \
           (["Zicsr"] if csr else []) + (["Zicntr"] if "Zicntr" in ext else []) + (["Zifencei"] if "Zifencei" in ext else []) + \
           (["Zicclsm"] if "Zicclsm" in ext else [])
    c = re.sub(r'extensions: ".*"', f'extensions: "{",".join(exts)}"', c)
    c = re.sub(r'(\n    HAS_ZICSR: )".*"', lambda m: f'{m.group(1)}"{str(csr).lower()}"\n    HAS_ZICNTR: "{str("Zicntr" in ext).lower()}"\n    HAS_M: "{str("M" in ext).lower()}"\n    HAS_ZMMUL: "{str("Zmmul" in ext).lower()}"', c)
    if "Zicclsm" not in ext:
        c = re.sub(r'(\n    HAS_ZICSR: ".*")', r'\1\n    HAS_ZICCLSM: "false"', c)
    if sdram:
        c = re.sub(r'(\n    HAS_ZIFENCEI: )".*"', r'\1"true"', c)
    (rb / f"config.profile-{name}.yaml").write_text(c)
    print(name, base, ",".join(exts))
