#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# LBPP Randomizer (see README.md)
"""Compiles the hooks (hooks/*.c) into lbpp/hooks.bin and lbpp/hooks.json.

Only needed after changing the C code: the randomizer ships the result. Needs the PSP toolchain
(pspdev, https://github.com/pspdev/pspdev): psp-gcc, psp-objcopy and psp-nm on the PATH, or
PSPDEV pointing at it.

    python hooks/build_hooks.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "lbpp"
CAVE_VA = 0x08c0ee00


def tool(name):
    pspdev = os.environ.get("PSPDEV")
    path = Path(pspdev) / "bin" / name if pspdev else shutil.which(name)
    if not path or not Path(path).exists():
        sys.exit(f"{name} not found: install pspdev and put its bin/ on the PATH (or set PSPDEV)")
    return str(path)


def main():
    cflags = ["-O2", "-G0", "-march=allegrex", "-mno-abicalls", "-fno-pic", "-fno-builtin",
              "-ffreestanding", "-nostdlib", "-Wall", "-Werror"]
    with tempfile.TemporaryDirectory() as tmp:
        elf = Path(tmp) / "hooks.elf"
        subprocess.run([tool("psp-gcc"), *cflags, f"-T{HERE / 'link.ld'}", f"-L{HERE}",
                        "-Wl,--no-warn-rwx-segments", "-o", str(elf), *map(str, sorted(HERE.glob("*.c")))],
                       check=True)
        blob = Path(tmp) / "hooks.bin"
        subprocess.run([tool("psp-objcopy"), "-O", "binary", "-j", ".rando", str(elf), str(blob)], check=True)
        nm = subprocess.run([tool("psp-nm"), str(elf)], check=True, capture_output=True, text=True).stdout
        code = blob.read_bytes()
    symbols = {}
    for line in nm.splitlines():
        parts = line.split()
        if len(parts) == 3:
            symbols[parts[2]] = int(parts[0], 16)
    seed = symbols["seed"]
    if CAVE_VA + len(code) > seed:
        sys.exit(f"the hooks ({len(code)} bytes) run into the seed block at {seed:#x}: move it up in game.ld")
    (OUT / "hooks.bin").write_bytes(code)
    hooks = {name: addr for name, addr in symbols.items() if name.startswith("hook_")}
    (OUT / "hooks.json").write_text(json.dumps({"cave": CAVE_VA, "seed": seed, "hooks": hooks}, indent=1) + "\n")
    print(f"hooks: {len(code)} bytes at {CAVE_VA:#x}, seed block at {seed:#x}, {len(hooks)} hooks")


if __name__ == "__main__":
    main()
