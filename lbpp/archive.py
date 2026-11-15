# SPDX-License-Identifier: GPL-3.0-or-later
# LBPP Randomizer (see README.md)
"""Reads files from the game's archives (USRDIR/lbp_archive.arc, archives/gui.arc) inside the ISO.

The format, as the game's own loader reads it (its "dearchiver"):
  0x00             u32 ~crc32(archive file name), u32 version (1), u32 count   keystream block 0
  0x0c             MD5 of the 12 bytes above                                   block 0
  0x1c             count x {u32 name hash, u32 offset, u32 size}               block 1
  0x1c + count*12  MD5 of the entry table                                      block (offset / 16)
  ...              the files, each encrypted on its own                        block 0
Everything is AES-128 in counter mode. The key and IV are the same 16 bytes: byte i % 4 of word i
of a table in the executable (0x08bb39b0). The counter block is IV[0:8] then the 64-bit
big-endian block number. Files are named only by ~crc32("/" + lower-case path).

A decrypted file is a container: content, u32 unpacked size, u8 flags (1 = LZO1X), u32, MD5 of
everything before it.
"""
import ctypes
import ctypes.util
import hashlib
import struct
import zlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY_TABLE = 0x08bb39b0


def archive_key(elf):
    """The archive key from the decrypted executable (an lbpp.elf.Elf)."""
    words = struct.unpack("<16I", elf.read(KEY_TABLE, 64))
    return bytes((words[i] >> (i % 4 * 8)) & 0xff for i in range(16))


def name_hash(path):
    return ~zlib.crc32(("/" + path.replace("\\", "/").lstrip("/").lower()).encode()) & 0xffffffff


class Archive:
    """An archive at `offset` in an open file (the ISO)."""

    def __init__(self, f, offset, key):
        self.f, self.base, self.key = f, offset, key
        header = self._decrypt(0, 12, 0)
        if hashlib.md5(header).digest() != self._decrypt(12, 16, 0):
            raise ValueError("archive header checksum mismatch (wrong key or not an archive)")
        _, _, count = struct.unpack("<3I", header)
        table = self._decrypt(0x1c, count * 12, 1)
        end = 0x1c + count * 12
        if hashlib.md5(table).digest() != self._decrypt(end, 16, end // 16):
            raise ValueError("archive table checksum mismatch")
        self.entries = {}
        for i in range(count):
            h, off, size = struct.unpack_from("<3I", table, 12 * i)
            self.entries[h] = (off, size)

    def _read(self, offset, size):
        self.f.seek(self.base + offset)
        return self.f.read(size)

    def _decrypt(self, offset, size, first_block):
        counter = self.key[:8] + struct.pack(">Q", first_block)
        d = Cipher(algorithms.AES(self.key), modes.CTR(counter)).decryptor()
        return d.update(self._read(offset, size)) + d.finalize()

    def stored_size(self, path):
        return self.entries[name_hash(path)][1]

    def has(self, path):
        return name_hash(path) in self.entries

    def read(self, path):
        """A file's contents: decrypted and unpacked."""
        off, size = self.entries[name_hash(path)]
        data = self._decrypt(off, size, 0)
        if not is_container(data):  # streamed audio is stored as it is
            return self._read(off, size)
        return unpack(data)


def is_container(data):
    return len(data) >= 25 and hashlib.md5(data[:-16]).digest() == data[-16:]


def unpack(data):
    size, flags, _ = struct.unpack_from("<IBI", data, len(data) - 25)
    content = data[:-25]
    if flags & 1:
        content = lzo1x_decompress(content, size)
    if len(content) != size:
        raise ValueError(f"unpacked {len(content)} bytes, expected {size}")
    return content


def _liblzo():
    name = ctypes.util.find_library("lzo2")
    for candidate in (name, "liblzo2.so.2", "liblzo2-2.dll", "liblzo2.2.dylib"):
        if not candidate:
            continue
        try:
            func = ctypes.CDLL(candidate).lzo1x_decompress_safe
        except (OSError, AttributeError):
            continue
        func.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p,
                         ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p]
        return func
    return None


LIBLZO = _liblzo()


def lzo1x_decompress(src, size):
    """LZO1X decompression: liblzo2 when it is installed, else the built-in decoder."""
    if LIBLZO:
        out = ctypes.create_string_buffer(size)
        n = ctypes.c_size_t(size)
        if LIBLZO(src, len(src), out, ctypes.byref(n), None) != 0:
            raise ValueError("LZO data error")
        return out.raw[:n.value]
    return lzo1x_decompress_py(src)


def lzo1x_decompress_py(src):
    """LZO1X decoder, following liblzo2's lzo1x_d.ch (used when liblzo2 is not installed)."""
    out = bytearray()
    ip = 0

    def byte():
        nonlocal ip
        ip += 1
        return src[ip - 1]

    def length(t, base):
        nonlocal ip
        if t == 0:
            while src[ip] == 0:
                t += 255
                ip += 1
            t += base + byte()
        return t

    def literals(n):
        nonlocal ip
        out.extend(src[ip:ip + n])
        ip += n

    def copy(dist, n):
        start = len(out) - dist
        if start < 0:
            raise ValueError("LZO data error")
        if n <= dist:
            out.extend(out[start:start + n])
        else:
            chunk = out[start:]
            out.extend((chunk * (n // dist + 1))[:n])

    t = src[0]
    if t > 17:
        ip = 1
        literals(t - 17)
        state = "first_literal_run" if t - 17 >= 4 else "match"
        if state == "match":
            t = byte()
    else:
        state = "start"
    while True:
        if state == "start":
            t = byte()
            if t < 16:
                literals(length(t, 15) + 3)
                state = "first_literal_run"
            else:
                state = "match"
        if state == "first_literal_run":
            t = byte()
            if t < 16:
                copy(1 + 0x800 + (t >> 2) + (byte() << 2), 3)
                state = "match_done"
            else:
                state = "match"
        if state == "match":
            if t >= 64:
                copy(1 + ((t >> 2) & 7) + (byte() << 3), (t >> 5) + 1)
            elif t >= 32:
                n = length(t & 31, 31) + 2
                b0, b1 = byte(), byte()
                copy(1 + (b0 >> 2) + (b1 << 6), n)
            elif t >= 16:
                n = length(t & 7, 7) + 2
                b0, b1 = byte(), byte()
                dist = ((t & 8) << 11) + (b0 >> 2) + (b1 << 6)
                if dist == 0:
                    return bytes(out)
                copy(dist + 0x4000, n)
            else:
                copy(1 + (t >> 2) + (byte() << 2), 2)
        t = src[ip - 2] & 3
        if t == 0:
            state = "start"
        else:
            literals(t)
            t = byte()
            state = "match"
