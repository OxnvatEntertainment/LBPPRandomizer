# SPDX-License-Identifier: GPL-3.0-or-later
# LBPP Randomizer (see README.md)
"""The seed: what is shuffled, worked out from the game's own files, and written as the block the
hooks read (struct seed_data in hooks/seed.h).

- Prizes: every prize bubble of the 38 story levels (a PBUB record names its prize's .meta.biff
  at word 10 and its icon at word 9, as self-relative pointers) goes into one pool, which is
  shuffled. Each prize appears once, so the swap table is keyed by the original prize's name.
- Catalogs: a level loads what its .catalog.biff lists (one RSRC group per resource, holding a
  28-byte DATA record: type hash, stored size, ..., name pointer +0x10, flag +0x18, name length
  +0x19). A prize from another level needs its meta, its icon and what the meta names (a
  sticker's texture...), with the type and stored size another story catalog gives them.
- Levels: The Introduction first, The Procession last, the others shuffled.
- Level descriptors, as profile_load builds them from the default profile: the story.dlv record
  (0x1c bytes), story.slv bytes 0-0x74, the story.sco record (0xfa), story.slv bytes 0x74-0xb6,
  with the LevelId also at +0x38.
"""
import random
import re
import struct

from . import patches

TYPE_META, TYPE_TEXTURE = 0x9a045367, 0x7d99f28d
DESC_SIZE = 0x1cc
SEED_MAGIC, SEED_VERSION = 0x4c425052, 1
META_DEPENDENCY = re.compile(rb"[a-zA-Z0-9_/.]{6,}\.(?:mip|biff|bnk)")


def fnv1a(s):
    h = 0x811c9dc5
    for b in s.encode():
        h = ((h ^ b) * 0x01000193) & 0xffffffff
    return h


def _cstring(data, offset):
    return data[offset:data.index(b"\0", offset)].decode("latin1")


def biff_records(data):
    """(tag, offset, size) of each entry of a biff's directory (the last word is its offset)."""
    directory, = struct.unpack_from("<I", data, len(data) - 4)
    for i in range((len(data) - 4 - directory) // 12):
        tag, off, size = struct.unpack_from("<4sII", data, directory + 12 * i)
        yield tag.decode("latin1").rstrip(), off, size


def level_prizes(level):
    """[(prize, icon)] of a level biff's prize bubbles, in file order."""
    out = []
    for tag, off, size in biff_records(level):
        if tag == "PBUB" and size != 0xffffffff:
            ref = lambda field: _cstring(level, (field + struct.unpack_from("<I", level, field)[0]) & 0xffffffff)
            out.append((ref(off + 40), ref(off + 36)))
    return out


def catalog_records(catalog):
    """{name: (type hash, stored size, flag)} of a catalog's DATA records, in order."""
    out = {}
    for tag, off, size in biff_records(catalog):
        if tag == "DATA" and size == 28:
            p = (off + 0x10 + struct.unpack_from("<I", catalog, off + 0x10)[0]) & 0xffffffff
            name = catalog[p:p + catalog[off + 0x19]].decode("latin1")
            out[name] = (struct.unpack_from("<I", catalog, off)[0],
                         struct.unpack_from("<I", catalog, off + 4)[0], catalog[off + 0x18])
    return out


class GameFiles:
    """What the seed needs from the archives."""

    def __init__(self, lbp_archive, gui_archive):
        self.lbp, self.gui = lbp_archive, gui_archive
        self.levels, self.catalogs = {}, {}
        for level_id, path in patches.STORY.items():
            self.levels[level_id] = level_prizes(self.lbp.read(f"Levels/{path}.level.biff"))
            self.catalogs[level_id] = catalog_records(self.lbp.read(f"Levels/{path}.catalog.biff"))
        self.profile = {x: self.lbp.read(f"myprofile/story.{x}") for x in ("dlv", "slv", "sco")}
        self._metas = {}

    def meta_dependencies(self, meta):
        if meta not in self._metas:
            data = self.gui.read(meta)
            self._metas[meta] = [m.decode().lower() for m in META_DEPENDENCY.findall(data)]
        return self._metas[meta]

    def story_desc(self, level_id):
        dlv, slv, sco = self.profile["dlv"], self.profile["slv"], self.profile["sco"]
        i = level_id - 1
        s = slv[182 * i:182 * (i + 1)]
        desc = bytearray(dlv[28 * i:28 * (i + 1)] + s[:0x74] + sco[250 * i:250 * (i + 1)] + s[0x74:])
        if len(desc) != DESC_SIZE or struct.unpack_from("<i", desc, 0x24)[0] != level_id:
            raise ValueError(f"unexpected story descriptor for level {level_id}")
        struct.pack_into("<i", desc, 0x38, level_id)
        return bytes(desc)


class Seed:
    """A seed's shuffle: the level order, the prize swaps and the catalog additions."""

    def __init__(self, files, number, short=False):
        self.files, self.number = files, number
        rng = random.Random(number)
        self.prizes = [p for level_id in patches.STORY for p in files.levels[level_id]]
        if len({p for p, _ in self.prizes}) != len(self.prizes):
            raise ValueError("a prize appears twice in the story")
        self.shuffled = self.prizes[:]
        rng.shuffle(self.shuffled)
        middle = [i for i in patches.STORY if i not in (patches.FIRST_LEVEL, patches.LAST_LEVEL)]
        rng.shuffle(middle)
        self.order = [patches.FIRST_LEVEL] + middle + [patches.LAST_LEVEL]
        if short:  # a test build: The Introduction, then The Procession
            self.order = [patches.FIRST_LEVEL, patches.LAST_LEVEL]
        self._catalog_additions()

    def _catalog_additions(self):
        known = {}
        for records in self.files.catalogs.values():
            known.update(records)
        self.adds, self.levels = [], []
        k = 0
        for level_id in patches.STORY:
            listed = self.files.catalogs[level_id]
            level_name = next(n for n in listed if n.endswith(".level.biff"))
            have = set(listed)
            new = []
            for _ in self.files.levels[level_id]:
                prize, icon = self.shuffled[k]
                k += 1
                for name, kind in ((prize.lower(), TYPE_META), (icon.lower(), TYPE_TEXTURE)):
                    if name not in have:
                        have.add(name)
                        new.append((kind, self.files.gui.stored_size(name), name, 1))
                for name in self.files.meta_dependencies(prize.lower()):
                    if name not in have and name in known:
                        have.add(name)
                        kind, size, flag = known[name]
                        new.append((kind, size, name, flag))
            if new:
                self.levels.append((fnv1a(level_name), len(self.adds), len(new)))
                self.adds += new

    def spoiler(self):
        lines = [f"LBPP Randomizer seed {self.number}", "", "Level order:"]
        lines += [f"{k + 1:2}. {patches.LEVEL_NAMES[i]}" for k, i in enumerate(self.order)]
        lines += ["", "Prizes (original -> what replaces it):"]
        lines += [f"{o} -> {n}" for (o, _), (n, _) in zip(self.prizes, self.shuffled)]
        return "\n".join(lines) + "\n"

    def block(self, address):
        """The seed block (struct seed_data and what it points to), to load at `address`."""
        out = bytearray(0x2c)
        strings = {}
        pending = []  # (offset of a pointer in out, string)

        def align(n=4):
            out.extend(bytes(-len(out) % n))

        def pointer_to_string(offset, s):
            pending.append((offset, s))

        # prize swaps, sorted by the original's hash
        align()
        swaps_at = len(out)
        rows = sorted((fnv1a(orig), new) for (orig, _), new in zip(self.prizes, self.shuffled))
        if len({h for h, _ in rows}) != len(rows):
            raise ValueError("prize name hash collision")
        for h, (prize, icon) in rows:
            out.extend(struct.pack("<III", h, 0, 0))
            pointer_to_string(len(out) - 8, prize)
            pointer_to_string(len(out) - 4, icon)
        # catalog additions and the levels they belong to
        adds_at = len(out)
        for kind, size, name, flag in self.adds:
            out.extend(struct.pack("<IIIB3x", kind, size, 0, flag))
            pointer_to_string(len(out) - 8, name)
        levels_at = len(out)
        for h, first, count in self.levels:
            out.extend(struct.pack("<Iii", h, first, count))
        # the level order and the descriptors
        order_at = len(out)
        out.extend(struct.pack(f"<{len(self.order)}i", *self.order))
        align(16)
        descs_at = len(out)
        for level_id in range(8, 46):
            out.extend(self.files.story_desc(level_id))
        # the strings
        for offset, s in pending:
            if s not in strings:
                strings[s] = len(out)
                out.extend(s.encode("latin1") + b"\0")
            struct.pack_into("<I", out, offset, address + strings[s])
        align(16)
        struct.pack_into("<3IIiIIiIiI", out, 0, SEED_MAGIC, SEED_VERSION, self.number & 0xffffffff,
                         address + swaps_at, len(rows), address + adds_at, address + levels_at,
                         len(self.levels), address + order_at, len(self.order), address + descs_at)
        return bytes(out)
