/* SPDX-License-Identifier: GPL-3.0-or-later. LBPP Randomizer (see README.md). */
/* The per-seed tables. The randomizer (lbpp/seed.py) writes them as one block at the address
   of `seed` (game.ld), right after the compiled hooks; its pointers are absolute. */
#ifndef SEED_H
#define SEED_H
#include "game.h"

#define SEED_MAGIC 0x4c425052  /* "RPBL" */
#define SEED_VERSION 1

struct prize_swap {
    u32 hash;           /* FNV-1a of the original prize path */
    const char *prize;  /* the prize that replaces it */
    const char *icon;
};

struct catalog_add {    /* a resource added to a level's catalog */
    u32 type;           /* resource type hash: 0x9a045367 meta biff, 0x7d99f28d texture... */
    u32 stored_size;    /* its size as stored in the archive */
    const char *name;
    u8 flag;            /* 1: in gui.arc */
    u8 pad[3];
};

struct catalog_level {
    u32 hash;           /* FNV-1a of the level's .level.biff name as its catalog lists it */
    int first, count;   /* its entries in catalog_adds */
};

struct seed_data {
    u32 magic, version, seed;
    const struct prize_swap *prize_swaps;
    int prize_swap_count;
    const struct catalog_add *catalog_adds;
    const struct catalog_level *catalog_levels;
    int catalog_level_count;
    const int *chain_order;     /* LevelIds in play order */
    int chain_length;
    u8 (*story_descs)[0x1cc];   /* LevelId 8-45: the default profile's level descriptors */
};

extern struct seed_data seed;

#define prize_swaps (seed.prize_swaps)
#define prize_swap_count (seed.prize_swap_count)
#define catalog_adds (seed.catalog_adds)
#define catalog_levels (seed.catalog_levels)
#define catalog_level_count (seed.catalog_level_count)
#define chain_order (seed.chain_order)
#define chain_length (seed.chain_length)
#define story_descs (seed.story_descs)
#endif
