/* SPDX-License-Identifier: GPL-3.0-or-later. LBPP Randomizer (see README.md). */
/* Prize shuffle. A PBUB record (from word 3, as the loader passes it) holds the position
   (0-2), the template (3, -1 in every story level), two words (4, 5), and pointers to the
   prize's icon (6) and its meta biff (7). The bubble copies both strings into its own
   Strings (+0x280 icon, +0x298 prize), and collecting it awards the item by that name.
   So the hook passes the constructor a copy of the record with the two pointers replaced
   by the prize this seed puts in the original's place. */
#include "game.h"
#include "rando.h"
#include "seed.h"

/* The prizes of the current level's bubbles, as they were loaded (a collected bubble is gone
   from the game state by the time the level ends, so the 100% check uses this list). */
const char *level_prizes[MAX_LEVEL_PRIZES];
int level_prize_count;
static int level_prize_level = -1;

static void remember_prize(const char *prize)
{
    int i, id = g_CurrentLevel.level_id;
    if (id != level_prize_level) {
        level_prize_level = id;
        level_prize_count = 0;
    }
    for (i = 0; i < level_prize_count; i++)
        if (level_prizes[i] == prize)
            return;
    if (level_prize_count < MAX_LEVEL_PRIZES)
        level_prizes[level_prize_count++] = prize;
}

static u32 fnv1a(const char *s)
{
    u32 h = 0x811c9dc5;
    while (*s)
        h = (h ^ (u8)*s++) * 0x01000193;
    return h;
}

static const struct prize_swap *find_swap(const char *prize)
{
    u32 h = fnv1a(prize);
    int lo = 0, hi = prize_swap_count - 1;
    while (lo <= hi) {
        int mid = (lo + hi) >> 1;
        u32 m = prize_swaps[mid].hash;
        if (m == h)
            return &prize_swaps[mid];
        if (m < h)
            lo = mid + 1;
        else
            hi = mid - 1;
    }
    return 0;
}

/* Replaces the loader's jal PrizeBubble::PrizeBubble (0x08951efc). */
__attribute__((section(".text.hooks")))
void hook_prize_bubble_load(void *self, u32 uid, const u32 *data, int type)
{
    u32 copy[8];
    const char *prize = (const char *)data[7];
    const struct prize_swap *swap;
    int i;

    if (prize && (swap = find_swap(prize)) != 0) {
        for (i = 0; i < 8; i++)
            copy[i] = data[i];
        copy[6] = (u32)swap->icon;
        copy[7] = (u32)swap->prize;
        data = copy;
    }
    if (data[7])
        remember_prize((const char *)data[7]);
    PrizeBubble_ctor(self, uid, data, type);
}
