"""Generate the ACT4 targets of the 12 RV32 profiles (I plus any of M, Zmmul, Zicsr and Zifencei).

Usage, from the root of the Certification repository:

    uv run python tools/riscv_build/gen_profiles.py

For each profile it writes tools/riscv_build/act/profile-<name>/ (UDB, Sail configuration and
test configuration) and tools/riscv_build/config.profile-<name>.yaml, to run with
`riscv-tools --config tools/riscv_build/config.profile-<name>.yaml certify`. A profile with
Zifencei uses the SDRAM platform (config.sdram.yaml); the others use the plain one (config.yaml).
"""
import json, re, shutil, sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
rb = root / "tools/riscv_build"

VARIANTS = [
    ("rv32i", set()), ("rv32im", {"M"}), ("rv32i_zmmul", {"Zmmul"}), ("rv32i_zicsr", {"Zicsr"}),
    ("rv32i_zifencei", {"Zifencei"}), ("rv32im_zicsr", {"M", "Zicsr"}), ("rv32im_zifencei", {"M", "Zifencei"}),
    ("rv32i_zicsr_zmmul", {"Zmmul", "Zicsr"}), ("rv32i_zifencei_zmmul", {"Zmmul", "Zifencei"}),
    ("rv32i_zicsr_zifencei", {"Zicsr", "Zifencei"}), ("rv32im_zicsr_zifencei", {"M", "Zicsr", "Zifencei"}),
    ("rv32i_zicsr_zifencei_zmmul", {"Zmmul", "Zicsr", "Zifencei"}),
]

for name, ext in VARIANTS:
    sdram = "Zifencei" in ext
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
    if "Zifencei" in ext:
        lst += ['  - { name: Zifencei, version: "= 2.0" }']
    y = re.sub(r"implemented_extensions:\n(?:  - .*\n)+", "implemented_extensions:\n" + "\n".join(lst) + "\n", y)
    if "M" not in ext:
        y = re.sub(r"  # MISA.*\n  MUTABLE_MISA_M: false\n", "  # MISA\n", y)
    (dst / f"{tgt}.yaml").write_text(y)

    # Sail
    sj = json.loads((dst / "sail.json").read_text())
    flags = {"M": "M" in ext, "Zmmul": "M" in ext or "Zmmul" in ext, "Zicsr": "Zicsr" in ext, "Zifencei": "Zifencei" in ext}
    for k, v in flags.items():
        sj["extensions"].setdefault(k, {})["supported"] = v
    (dst / "sail.json").write_text(json.dumps(sj, indent=2))

    # test_config
    t = (dst / "test_config.yaml").read_text()
    t = t.replace(f"name: {base}", f"name: {tgt}").replace(f"udb_config: {base}.yaml", f"udb_config: {tgt}.yaml")
    t = re.sub(r"include_priv_tests: \w+", f"include_priv_tests: {'True' if 'Zicsr' in ext else 'False'}", t)
    (dst / "test_config.yaml").write_text(t)
    if (dst / "run_cmd.txt").exists():
        (dst / "run_cmd.txt").write_text((dst / "run_cmd.txt").read_text().replace(base, tgt))

    # certify config
    cfg_src = rb / ("config.sdram.yaml" if sdram else "config.yaml")
    c = cfg_src.read_text()
    c = re.sub(r"target_config: .*", f"target_config: tools/riscv_build/act/{tgt}/test_config.yaml", c)
    exts = ["I"] + (["M"] if "M" in ext else []) + (["Zmmul"] if "Zmmul" in ext else []) + \
           (["Zicsr"] if "Zicsr" in ext else []) + (["Zifencei"] if "Zifencei" in ext else [])
    c = re.sub(r'extensions: ".*"', f'extensions: "{",".join(exts)}"', c)
    c = re.sub(r'(\n    HAS_ZICSR: )".*"', lambda m: f'{m.group(1)}"{str("Zicsr" in ext).lower()}"\n    HAS_M: "{str("M" in ext).lower()}"\n    HAS_ZMMUL: "{str("Zmmul" in ext).lower()}"', c)
    if sdram:
        c = re.sub(r'(\n    HAS_ZIFENCEI: )".*"', r'\1"true"', c)
    (rb / f"config.profile-{name}.yaml").write_text(c)
    print(name, base, ",".join(exts))
