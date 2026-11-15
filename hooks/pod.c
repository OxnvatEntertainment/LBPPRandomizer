/* SPDX-License-Identifier: GPL-3.0-or-later. LBPP Randomizer (see README.md). */
/* The pod (main menu) during a run: only the Earth ("LittleBigPlanet", the story levels).
   - Its navigation nodes (g_Profile + 0x148, 24 bytes each, *(g_Profile + 0x14c) of them; see
     tools/scripts/lbp_pod.py) include the four area roots (Earth 0, pod 67, My Moon 72,
     Community Moon 167), whose +0x8 / +0xa name the previous / next area's root for turning the
     mobile. Every root is pointed at the Earth's, so turning never leaves it.
   - PodState::enter sends its screen the start node (pod + 0x100, pod_send_start_event, called
     at 0x088f04fc); that is set to the Earth's root.
   The node patch runs from hook_pod_load_story_slots (PodState::enter, after profile_load). */
#include "game.h"
#include "rando.h"

#define EARTH_ROOT 0
#define NODE_SIZE 0x18

void pod_lock_areas(void *profile)
{
    u8 *nodes = *(u8 **)((u8 *)profile + 0x148);
    int count = *(int *)((u8 *)profile + 0x14c), i;

    if (!nodes)
        return;
    for (i = 0; i < count; i++) {
        u8 *node = nodes + i * NODE_SIZE;
        if (*(u16 *)node == 1) {         /* an area root */
            *(u16 *)(node + 0x8) = EARTH_ROOT;
            *(u16 *)(node + 0xa) = EARTH_ROOT;
        }
    }
}

/* Replaces PodState::enter's jal pod_send_start_event (0x088f04fc). */
void hook_pod_send_start_event(u8 *pod)
{
    *(u32 *)(pod + 0x100) = EARTH_ROOT;
    pod_send_start_event(pod);
}
