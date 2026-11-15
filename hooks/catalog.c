/* SPDX-License-Identifier: GPL-3.0-or-later. LBPP Randomizer (see README.md). */
/* Loading the prizes a level did not have before the shuffle.
   A level's catalog (.catalog.biff) lists every resource the level loads: one RSRC group per
   resource holding a 28-byte DATA record {type hash, stored size, 0, 0, name, 0, flag (1: in
   gui.arc), name length, ...}. Only a prize's .meta.biff and its icon .mip are listed (costume
   meshes and object catalogs load later, on demand), so a prize from another level needs those
   two added. catalog_load_walk (0x0894c920) walks the top-level groups with catalog_parse as the
   callback (address loaded at 0x0894c940/4); this callback stands in for it, and after the group
   naming the level's own .level.biff, feeds catalog_parse a group for each added resource. */
#include "game.h"
#include "seed.h"

#define TAG_RSRC 0x43525352
#define TAG_DATA 0x41544144

struct biff_entry {
    u32 tag, offset, size;  /* offset 0xffffffff: a group of size / 12 entries */
};

struct catalog_data {      /* a DATA record, its pointers already made absolute */
    u32 type, stored_size, unknown[2];
    const char *name, *name2;
    u8 flag, name_len, name2_len, pad;
};

static u32 fnv1a_n(const char *s, int n)
{
    u32 h = 0x811c9dc5;
    while (n-- > 0)
        h = (h ^ (u8)*s++) * 0x01000193;
    return h;
}

static const struct catalog_level *find_level(u32 hash)
{
    int i;
    for (i = 0; i < catalog_level_count; i++)
        if (catalog_levels[i].hash == hash)
            return &catalog_levels[i];
    return 0;
}

int hook_catalog_parse(struct biff_entry *entry, u32 base, void *ctx)
{
    int result = catalog_parse(entry, base, ctx);
    const struct biff_entry *child = entry + 1;
    const struct catalog_data *rec;
    const struct catalog_level *level;
    int i;

    if (entry->tag != TAG_RSRC || entry->offset != 0xffffffff || entry->size < 12 ||
        child->tag != TAG_DATA || child->size < sizeof(struct catalog_data))
        return result;
    rec = (const struct catalog_data *)(base + child->offset);
    if (!rec->name || !rec->name_len)
        return result;
    level = find_level(fnv1a_n(rec->name, rec->name_len));
    if (!level)
        return result;

    for (i = 0; i < level->count; i++) {
        const struct catalog_add *add = &catalog_adds[level->first + i];
        struct biff_entry fake[2];
        struct catalog_data data;
        int k;
        const char *p;

        data.type = add->type;
        data.stored_size = add->stored_size;
        data.unknown[0] = data.unknown[1] = 0;
        data.name = add->name;
        data.name2 = 0;
        data.flag = add->flag;
        for (k = 0, p = add->name; *p; p++)
            k++;
        data.name_len = (u8)k;
        data.name2_len = 0;
        data.pad = 0;
        fake[0].tag = TAG_RSRC;
        fake[0].offset = 0xffffffff;
        fake[0].size = sizeof(struct biff_entry);
        fake[1].tag = TAG_DATA;
        fake[1].offset = (u32)&data - base;
        fake[1].size = sizeof(struct catalog_data);
        catalog_parse(fake, base, ctx);
    }
    return result;
}
