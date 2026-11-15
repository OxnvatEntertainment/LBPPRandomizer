# SPDX-License-Identifier: GPL-3.0-or-later
# LBPP Randomizer (see README.md)
"""Reading files from the ISO, and replacing one in a copy of it.

The UMD's PSP_GAME/SYSDIR/EBOOT.BIN is the encrypted ~PSP executable. PPSSPP also runs a
plain ELF there, so the patched executable replaces it. The new file goes over the old one
when it fits in the sectors the old one had, otherwise at the end of the image; the directory
record (location and both-endian size) and the volume size are updated to match.
"""
import shutil
import struct
from pathlib import Path

SECTOR = 2048


def _dir_entries(f, lba, size):
    """Yields (name, record offset in the image, extent lba, data size, flags)."""
    f.seek(lba * SECTOR)
    data = f.read(size)
    pos = 0
    while pos < len(data):
        length = data[pos]
        if length == 0:  # records never cross a sector: skip to the next one
            pos = (pos // SECTOR + 1) * SECTOR
            continue
        rec = data[pos:pos + length]
        name_len = rec[32]
        name = rec[33:33 + name_len].split(b";")[0].decode("ascii", "replace")
        extent = struct.unpack_from("<I", rec, 2)[0]
        dsize = struct.unpack_from("<I", rec, 10)[0]
        yield name, lba * SECTOR + pos, extent, dsize, rec[25]
        pos += length


def find_file(f, path):
    f.seek(16 * SECTOR)
    pvd = f.read(SECTOR)
    assert pvd[1:6] == b"CD001", "not an ISO 9660 image"
    root = pvd[156:156 + 34]
    lba, size = struct.unpack_from("<I", root, 2)[0], struct.unpack_from("<I", root, 10)[0]
    parts = path.upper().split("/")
    for i, part in enumerate(parts):
        for name, rec_off, extent, dsize, flags in _dir_entries(f, lba, size):
            if name.upper() == part:
                if i == len(parts) - 1:
                    return rec_off, extent, dsize
                lba, size = extent, dsize
                break
        else:
            raise FileNotFoundError(path)


def file_offset(f, path):
    """(byte offset, size) of a file in an open image."""
    _, extent, size = find_file(f, path)
    return extent * SECTOR, size


def read_file(f, path):
    offset, size = file_offset(f, path)
    f.seek(offset)
    return f.read(size)


def replace_file(iso_in, iso_out, path, data):
    iso_in, iso_out = Path(iso_in), Path(iso_out)
    if iso_in.resolve() != iso_out.resolve():
        shutil.copyfile(iso_in, iso_out)
    with open(iso_out, "r+b") as f:
        rec_off, extent, old_size = find_file(f, path)
        old_sectors = -(-old_size // SECTOR)
        new_sectors = -(-len(data) // SECTOR)
        if new_sectors > old_sectors:
            f.seek(0, 2)
            extent = -(-f.tell() // SECTOR)
        f.seek(extent * SECTOR)
        f.write(data + b"\0" * (new_sectors * SECTOR - len(data)))
        # directory record: extent at +2 (LE) / +6 (BE), size at +10 (LE) / +14 (BE)
        f.seek(rec_off + 2)
        f.write(struct.pack("<I", extent) + struct.pack(">I", extent))
        f.write(struct.pack("<I", len(data)) + struct.pack(">I", len(data)))
        # volume space size (PVD +80, both-endian)
        f.seek(0, 2)
        total = -(-f.tell() // SECTOR)
        f.truncate(total * SECTOR)
        f.seek(16 * SECTOR + 80)
        f.write(struct.pack("<I", total) + struct.pack(">I", total))
