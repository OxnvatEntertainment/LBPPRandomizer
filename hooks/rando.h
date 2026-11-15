/* SPDX-License-Identifier: GPL-3.0-or-later. LBPP Randomizer (see README.md). */
/* State shared by the randomizer's parts. All of it lives in RAM only: a new boot is a new run. */
#ifndef RANDO_H
#define RANDO_H
#include "game.h"

#define FIRST_STORY 8
#define LAST_STORY 45

extern int run_started;
extern int furthest;          /* index in chain_order of the furthest level reached */
extern int teleporters;       /* earned by acing a level */
extern int skips;             /* earned by collecting all of a level's prize bubbles */
extern int skip_used;         /* a skip was used in the current level */
extern int teleporting;       /* the pause menu's teleporter is taking us to the pod */

#define MAX_LEVEL_PRIZES 64
extern const char *level_prizes[MAX_LEVEL_PRIZES];
extern int level_prize_count;

int chain_index(int level_id);
void apply_unlocks(void);
void award_level(void);       /* level_exit(.., completed): the ace and 100% rewards */
void refresh_labels(void);    /* the pause menu's Teleporter / Skip Level counts */
void pod_lock_areas(void *profile);  /* pod.c: only the Earth */
#endif
