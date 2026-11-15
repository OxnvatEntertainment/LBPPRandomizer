# LBPP Randomizer

A randomizer for **LittleBigPlanet on the PSP** (US release, UCUS-98744), played in
[PPSSPP](https://www.ppsspp.org/).

Every run is a new trip through the story:

- **The levels come in a random order.** The Introduction is always first and The Procession
  always last. Reaching a level's scoreboard takes you straight to the next one: there is no
  main menu between levels.
- **All 735 prize bubbles of story mode are shuffled together**: stickers, materials,
  costumes, objects and music can turn up in any level.
- **Ace a level** (finish it without dying) to earn a **Teleporter**. Use it from the pause
  menu to go to the main menu and replay any level you have reached. Finishing that level
  brings you back to the furthest one.
- **Collect every prize bubble of a level** to earn a **Skip Level**. Use it from the pause
  menu to be taken straight to the level's scoreboard.
- **The main menu** only offers LittleBigPlanet's story levels: no My Moon, Community Moon or
  My Pod.
- **Nothing is saved.** Every boot starts a fresh run with a fresh profile, and your own save
  data is never read or written. Finishing The Procession ends the run and closes the game.

## What you need

- Your own LittleBigPlanet PSP ISO (the US release, UCUS-98744), dumped from your own UMD. The
  randomizer does not include or download any part of the game.
- [Python](https://www.python.org/) 3.8 or newer, with the `cryptography` package:
  `pip install -r requirements.txt`
- PPSSPP to play.

## Making a randomized ISO

```
python lbpp_randomizer.py "LittleBigPlanet.iso"
```

This writes `LBPP Randomizer <seed>.iso` next to your ISO, plus `LBPP Randomizer <seed>.spoiler.txt`
with the level order and where every prize went. Your ISO is not changed.

- `--seed 12345` picks the seed, so others can play the same randomization (share the number).
- `-o path/to/output.iso` chooses where the randomized ISO goes.
- `--short` makes a test ISO whose run is only The Introduction and The Procession.

It takes a few seconds, plus the time to copy the ISO (about 1.5 GB). Installing liblzo2 makes
it a little faster; it works without it.

Open the randomized ISO in PPSSPP like any other game. It only runs in PPSSPP, not on a real
PSP.

## How it works

The randomizer decrypts the game's executable from your ISO, checks that it is the expected
version, and patches it. New code ("hooks", in `hooks/`) is added after the game's own memory,
and calls in the game are redirected to it. The per-seed data (the prize swaps, the level order
and so on) is worked out from the game's own files in your ISO and stored next to that code.
The patched executable replaces `EBOOT.BIN` in a copy of your ISO.

- `lbpp/psp_decrypt.py` decrypts `EBOOT.BIN` (ported from
  [pspdecrypt](https://github.com/John-K/pspdecrypt)).
- `lbpp/archive.py` reads files from the game's archives.
- `lbpp/seed.py` makes the shuffle and the data block the hooks read.
- `lbpp/patches.py` lists every change made to the executable. Each patch checks the original
  instruction first, so a different version of the game is refused rather than broken.
- `hooks/*.c` is the code added to the game. `lbpp/hooks.bin` is that code compiled. To rebuild
  it after changing the C code, install [pspdev](https://github.com/pspdev/pspdev) and run
  `python hooks/build_hooks.py`.

## Sharing

Share the randomizer and seed numbers, not ISOs: a randomized ISO contains the whole game.

## License

GPL-3.0-or-later; see `LICENSE`. The EBOOT decryption is a port of part of pspdecrypt
(GPL-3.0). LittleBigPlanet is a trademark of Sony Interactive Entertainment. This project is
not affiliated with or endorsed by Sony or Media Molecule.
