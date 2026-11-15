#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# LBPP Randomizer (see README.md)
"""LBPP Randomizer: builds a randomized copy of your LittleBigPlanet (PSP) ISO.

    python lbpp_randomizer.py "LittleBigPlanet.iso" [--seed N] [-o randomized.iso]

Without --seed a random one is picked. The spoiler log (level order and every prize) is written
next to the output ISO. The ISO must be the US release (UCUS-98744); the result runs in PPSSPP.
"""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lbpp import __version__  # noqa: E402
from lbpp.randomizer import build  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="LBPP Randomizer " + __version__)
    ap.add_argument("iso", help="your LittleBigPlanet (PSP, UCUS-98744) ISO")
    ap.add_argument("--seed", type=int, help="the seed (a number); random when left out")
    ap.add_argument("-o", "--output", help="the randomized ISO (default: next to the input)")
    ap.add_argument("--short", action="store_true",
                    help="test build: the run is only The Introduction and The Procession")
    args = ap.parse_args()

    iso_in = Path(args.iso)
    if not iso_in.is_file():
        sys.exit(f"{iso_in}: not found")
    seed = args.seed if args.seed is not None else random.randrange(1, 1 << 31)
    out = Path(args.output) if args.output else iso_in.with_name(f"LBPP Randomizer {seed}.iso")
    if out.resolve() == iso_in.resolve():
        sys.exit("the output must not be the input ISO")
    result = build(iso_in, out, seed, args.short)
    spoiler = out.with_suffix(".spoiler.txt")
    spoiler.write_text(result.spoiler())
    print(f"done: {out}\nspoiler log: {spoiler}")


if __name__ == "__main__":
    main()
