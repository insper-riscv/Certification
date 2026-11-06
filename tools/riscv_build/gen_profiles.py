"""Generate the ACT4 targets of the RV32 profiles (I plus any valid combination of M, Zmmul, Zicsr, Zicntr, Zihpm, Zifencei and Zicclsm).


Usage, from the root of the Certification repository:

    uv run python tools/riscv_build/gen_profiles.py

For each profile it writes tools/riscv_build/act/profile-<name>/ (UDB, Sail configuration and
test configuration) and tools/riscv_build/config.profile-<name>.yaml, to run with
`riscv-tools --config tools/riscv_build/config.profile-<name>.yaml certify`. A profile with
Zifencei needs the caches and has no config here (gen_flash_profiles.py writes it, for the platform with the ROM
and the RAM behind the caches); the others extend config.modular.yaml.

To certify one profile on one memory model without committing anything, generate its target at run time:

    uv run python tools/riscv_build/gen_profiles.py --profile rv32i_zimop \\
        --memory rom=int,ram=ext,icache=off,dcache=on --out build/target [--jobs 4]
    riscv-tools --config build/target/config.yaml certify

The profile is one of the matrix of the Core or of tools/riscv_build/minimal_profiles.yaml. The memory model
is the `--memory` syntax of riscv-tools with the four keys; the command refuses a combination that the modular
top does not accept and says why (memory_models.py). Nothing else of the versioned targets changes.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory_models
from profile_params import extension_list, find_profile, is_e, parameter_lines, variants, write_modular_config
from target_gen import BASE, write_generated, write_target

parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
parser.add_argument("root", nargs="?", default=None, help="root of the repository (default: the current folder)")
parser.add_argument("--profile", help="generate the target of this profile at run time, instead of the versioned ones")
parser.add_argument("--memory", help="memory model of the generated target (rom=int|ext,ram=int|ext,icache=on|off,dcache=on|off)")
parser.add_argument("--out", help="folder that receives the generated target and its config.yaml")
parser.add_argument("--jobs", type=int, help="act.jobs of the generated config (JOBS= of the make of ACT4; 0 is automatic)")
args = parser.parse_args()

root = Path(args.root) if args.root else Path.cwd()
rb = root / "tools/riscv_build"

if args.profile is not None:
    if not (args.memory and args.out):
        parser.error("--profile needs --memory and --out")
    if not re.fullmatch(r"[A-Za-z0-9_]+", args.profile):
        parser.error(f"'{args.profile}' is not a profile name")
    if args.jobs is not None and not 0 <= args.jobs <= 256:
        parser.error("--jobs is between 0 and 256")
    try:
        model = memory_models.parse(args.memory)
    except ValueError as error:
        parser.error(str(error))
    extensions = find_profile(root, args.profile)
    refused = memory_models.problems(model, extensions)
    if refused:
        sys.exit(f"{args.profile} on {model.spec} is not accepted:\n  " + "\n  ".join(refused))
    out = Path(args.out)
    out = out if out.is_absolute() else root / out
    print(write_generated(root, out.resolve(), args.profile, extensions, model, args.jobs))
    sys.exit(0)
if args.memory or args.out or args.jobs is not None:
    parser.error("--memory, --out and --jobs need --profile")

# The profiles come from the specification of the core (riscv-tools profiles), which is in the
# Insper-RISC-V submodule (profile_params.py).
VARIANTS = variants(root)
write_modular_config(root)

for name, ext in VARIANTS:
    zifencei = "Zifencei" in ext
    tgt = f"profile-{name}"
    write_target(rb, name, ext, rb / "act" / tgt, tgt)

    # certify config: the profile on the modular platform with the memories inside the chip
    # (config.modular.yaml) and only what is the profile's. A profile with Zifencei needs the caches:
    # it runs with the FLASH and the RAM behind them (gen_flash_profiles.py), so it has no config here.
    exts = extension_list(ext, name)
    # RV32E: the toolchain builds with -march=rv32e and -mabi=ilp32e
    isa_lines = "\nisa:\n  base: e\n" if is_e(name) else ""
    config = rb / f"config.profile-{name}.yaml"
    if zifencei:
        config.unlink(missing_ok=True)
        print(name, BASE, ",".join(exts), "(config: gen_flash_profiles.py)")
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
    print(name, BASE, ",".join(exts))
