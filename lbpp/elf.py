# SPDX-License-Identifier: GPL-3.0-or-later
# LBPP Randomizer (see README.md)
"""Patching the decrypted executable: word patches inside the image, plus a code cave after .bss.

The executable has one LOAD segment (0x08804000, memsz 0x40adb8, so it ends at 0x08c0edb8).
The cave is placed after it: the segment's file size grows to cover .bss (written as zeros,
which is what the loader would have given it) and the cave. PPSSPP loads the whole segment
at its fixed address, and nothing in the game uses the memory past .bss (the C heap comes
from a "UserSbrk" partition block, not from _end).
"""
import struct

LOAD_VA = 0x08804000
LOAD_OFF = 0x1000
CAVE_VA = 0x08c0ee00  # first free address after .bss, 64-byte aligned


class Elf:
    def __init__(self, data):
        self.data = bytearray(data)
        e = self.data
        assert e[:4] == b"\x7fELF"
        self.phoff, self.shoff = struct.unpack_from("<II", e, 0x1c)
        self.shentsize, self.shnum, self.shstrndx = struct.unpack_from("<HHH", e, 0x2e)
        (_, self.p_off, self.p_va, _, self.filesz, self.memsz, _, _) = struct.unpack_from(
            "<8I", e, self.phoff)
        assert self.p_va == LOAD_VA and self.p_off == LOAD_OFF
        self.end_va = LOAD_VA + self.memsz
        assert CAVE_VA >= self.end_va

    def off(self, va):
        assert LOAD_VA <= va < LOAD_VA + self.filesz, hex(va)
        return va - LOAD_VA + LOAD_OFF

    def read(self, va, size):
        o = self.off(va)
        return bytes(self.data[o:o + size])

    def read32(self, va):
        return struct.unpack_from("<I", self.data, self.off(va))[0]

    def write32(self, va, word, expect=None):
        if expect is not None and self.read32(va) != expect:
            raise ValueError(f"{va:08x}: found {self.read32(va):08x}, expected {expect:08x}")
        struct.pack_into("<I", self.data, self.off(va), word)

    def build(self, cave=b""):
        """Returns the patched ELF with `cave` loaded at CAVE_VA."""
        e = self.data
        seg_end_off = LOAD_OFF + self.filesz
        image = bytes(e[:seg_end_off])
        tail = bytes(e[seg_end_off:])  # .shstrtab and the section headers
        if cave:
            pad = CAVE_VA - (LOAD_VA + self.filesz)
            image += b"\0" * pad + cave
        new_filesz = len(image) - LOAD_OFF
        new_memsz = max(self.memsz, new_filesz)
        shift = len(image) - seg_end_off
        out = bytearray(image + tail)
        # program header sizes
        struct.pack_into("<II", out, self.phoff + 16, new_filesz, new_memsz)
        # section header table moves with the tail; so do sections stored after the segment
        struct.pack_into("<I", out, 0x20, self.shoff + shift)
        for i in range(self.shnum):
            sh = self.shoff + shift + i * self.shentsize
            sh_off = struct.unpack_from("<I", out, sh + 16)[0]
            sh_addr = struct.unpack_from("<I", out, sh + 12)[0]
            if sh_addr == 0 and sh_off >= seg_end_off:
                struct.pack_into("<I", out, sh + 16, sh_off + shift)
        return bytes(out)
