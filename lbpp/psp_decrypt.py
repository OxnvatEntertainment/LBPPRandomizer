# SPDX-License-Identifier: GPL-3.0-or-later
# LBPP Randomizer (see README.md)
"""Decrypts the game's EBOOT.BIN (a ~PSP executable, tag 0xD9160BF0, "type 2").

A Python port of the type 2 path of pspdecrypt's PrxDecrypter.cpp (John Kelley and others, GPL-3.0,
https://github.com/John-K/pspdecrypt), itself from PPSSPP. Only what this one game needs is here;
the KIRK CMAC and signature checks are left out because the result is checked against the
known SHA-1 of the decrypted executable instead.
"""
import hashlib
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

TAG = 0xD9160BF0
TAG_KEY = bytes([0x83, 0x83, 0xF1, 0x37, 0x53, 0xD0, 0xBE, 0xFC, 0x8D, 0xA7, 0x32, 0x52, 0x46, 0x0A, 0xC2, 0xC2])
TAG_CODE = 0x5D
KIRK7_KEY_5D = bytes([0x11, 0x5A, 0x5D, 0x20, 0xD5, 0x3A, 0x8D, 0xD3, 0x9C, 0xC5, 0xAF, 0x41, 0x0F, 0x0F, 0x18, 0x6F])
KIRK1_KEY = bytes([0x98, 0xC9, 0x40, 0x97, 0x5C, 0x1D, 0x10, 0xE8, 0x7F, 0xE6, 0x0E, 0xA3, 0xFD, 0x03, 0xA8, 0xBA])
HEADER_SIZE = 0x150


def _cbc_decrypt(key, data):
    d = Cipher(algorithms.AES(key), modes.CBC(bytes(16))).decryptor()
    return d.update(bytes(data)) + d.finalize()


def decrypt_eboot(data):
    """The decrypted executable (ELF) from an encrypted EBOOT.BIN."""
    data = bytes(data)
    if data[:4] != b"~PSP":
        raise ValueError("not an encrypted PSP executable (~PSP)")
    tag, = struct.unpack_from("<I", data, 0xD0)
    if tag != TAG:
        raise ValueError(f"unexpected encryption tag {tag:#010x} (not LittleBigPlanet UCUS-98744?)")
    decrypt_size, = struct.unpack_from("<i", data, 0xB0)

    # the seed, expanded into a 0x90-byte xor buffer (expandSeed)
    seed = b"".join(bytes([i]) + TAG_KEY[1:] for i in range(9))
    xorbuf = _cbc_decrypt(KIRK7_KEY_5D, seed)

    # the type 2 header: tag, 0x58 zeros, id, sha1, kirk header, kirk metadata, PRX header
    t2 = bytearray(data[0xD0:0xD4] + bytes(0x58) + data[0x140:0x150] + data[0x12C:0x140]
                   + data[0x80:0xB0] + data[0xC0:0xD0] + data[0xB0:0xC0] + data[:0x80])
    assert len(t2) == HEADER_SIZE
    t2[0x5C:0xBC] = _cbc_decrypt(KIRK7_KEY_5D, t2[0x5C:0xBC])  # id and what follows, 0x60 bytes
    sha1 = bytes(t2[0x6C:0x80])
    kirk_header, kirk_meta, prx_header = t2[0x80:0xC0], t2[0xC0:0xD0], t2[0xD0:0x150]
    check = hashlib.sha1(t2[0:4] + xorbuf[:0x10] + t2[4:0x5C] + t2[0x5C:0x6C] + kirk_header
                         + kirk_meta + prx_header).digest()
    if check != sha1:
        raise ValueError("EBOOT.BIN header check failed")

    # the KIRK command 1 block, built in place at 0x40 (0x150 - 0x90 - 0x80)
    out = bytearray(data)
    h = bytearray(0x90)
    h[0x70:0x80] = kirk_meta
    head = bytes(a ^ b for a, b in zip(kirk_header, xorbuf[0x10:0x50]))
    head = _cbc_decrypt(KIRK7_KEY_5D, head)
    h[0:0x40] = bytes(a ^ b for a, b in zip(head, xorbuf[0x50:0x90]))
    struct.pack_into("<I", h, 0x60, 1)  # mode: KIRK command 1
    out[0x40:0xD0] = h
    out[0xD0:0x150] = prx_header

    # KIRK command 1: the AES key from the header, then the data
    keys = _cbc_decrypt(KIRK1_KEY, h[0:0x20])
    data_size, data_offset = struct.unpack_from("<II", h, 0x70)
    start = 0x40 + 0x90 + data_offset
    plain = _cbc_decrypt(keys[:16], out[start:start + data_size])
    return plain[:decrypt_size]
