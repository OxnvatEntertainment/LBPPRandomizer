# SPDX-License-Identifier: GPL-3.0-or-later
# LBPP Randomizer (see README.md)
"""Builds a randomized ISO from the player's own LittleBigPlanet ISO."""
import hashlib
import json
from pathlib import Path

from . import archive, elf as elfmod, iso, patches
from .psp_decrypt import decrypt_eboot
from .seed import GameFiles, Seed

HERE = Path(__file__).resolve().parent
EBOOT = "PSP_GAME/SYSDIR/EBOOT.BIN"


def check_game(f):
    """The decrypted executable, after checking that this is the right game."""
    sfo = iso.read_file(f, "PSP_GAME/PARAM.SFO")
    if patches.GAME_ID.encode() not in sfo:
        raise SystemExit(f"this is not LittleBigPlanet {patches.GAME_ID} (the US PSP release)")
    eboot = iso.read_file(f, EBOOT)
    if eboot[:4] == b"\x7fELF":
        raise SystemExit("this ISO's EBOOT.BIN is already decrypted or patched: use the original ISO")
    data = decrypt_eboot(eboot)
    if hashlib.sha1(data).hexdigest() != patches.ELF_SHA1:
        raise SystemExit("this version of the game's executable is not supported")
    return data


def build(iso_in, iso_out, seed_number, short=False, log=print):
    hooks = json.loads((HERE / "hooks.json").read_text())
    code = (HERE / "hooks.bin").read_bytes()
    with open(iso_in, "rb") as f:
        log("checking the game...")
        e = elfmod.Elf(check_game(f))
        key = archive.archive_key(e)
        log("reading the levels...")
        lbp = archive.Archive(f, iso.file_offset(f, "PSP_GAME/USRDIR/lbp_archive.arc")[0], key)
        gui = archive.Archive(f, iso.file_offset(f, "PSP_GAME/USRDIR/archives/gui.arc")[0], key)
        files = GameFiles(lbp, gui)
        log(f"shuffling (seed {seed_number})...")
        seed = Seed(files, seed_number, short)
        block = seed.block(hooks["seed"])
    patches.apply(e, hooks["hooks"])
    cave = code + bytes(hooks["seed"] - hooks["cave"] - len(code)) + block
    log("writing the ISO...")
    iso.replace_file(iso_in, iso_out, EBOOT, e.build(cave))
    return seed
