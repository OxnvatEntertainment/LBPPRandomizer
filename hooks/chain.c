/* SPDX-License-Identifier: GPL-3.0-or-later. LBPP Randomizer (see README.md). */
/* The level chain: finishing a story level goes on to the next level of the seed's order
   instead of the pod. The Introduction is first and The Procession last.

   - The levels are started like the pod's Play does (level_mark_played): set_current_level
     with the level's descriptor, DAT_08be8920 = 1, level_file_path, start_level. The
     descriptors come from the seed block (story_descs: the default profile's story.dlv,
     .slv and .sco records put together the way profile_load does), so the pod is not needed.
   - level_exit(level state, completed) (0x088b66a4) records the result and saves; the
     scoreboard and the level key pass 1, the pause menu's Return to My Pod 0. Its callers
     go through hook_level_exit, which notes the flag.
   - level_state_finish (0x088b5804) then either restarts the level (+0x2e0 set) or goes
     to the pod (app_go_to_pod, 0x089e91e8, at 0x088b582c). That call goes through
     hook_level_leave, which starts the next level instead.
   - level_exit's story save (story.dlv) ends in a callback (0x088b5760, loaded at
     0x088b6408/c) that sets the level's leave flag (DAT_08be8199). A level can call
     level_exit twice (The Introduction: its scoreboard and its level key), and the second
     save can finish after the next level has started, which would end that level at once.
     hook_save_done only sets the flag while an exit is waiting.
   - Completing the last level (The Procession) ends the run: sceKernelExitGame.
   Nothing here is saved: a new boot starts a new run. */
#include "game.h"
#include "rando.h"
#include "seed.h"

#define DESC_SIZE 0x1cc

static int exit_completed; /* the last level_exit's flag */
static int exit_armed;     /* a level_exit is waiting for its save to finish */
int run_started;
int furthest;

int chain_index(int level_id)
{
    int i;
    for (i = 0; i < chain_length; i++)
        if (chain_order[i] == level_id)
            return i;
    return -1;
}

/* Replaces jal set_current_level at 0x088d0714 (the pod starting a level). */
void hook_pod_set_current_level(void *desc)
{
    set_current_level(desc);
    skip_used = 0;
    teleporting = 0;
    refresh_labels();
    if (!run_started && g_CurrentLevel.level_id == chain_order[0]) {
        run_started = 1;
        furthest = 0;
    }
}

/* Replaces the three jal level_exit (0x08962450 pause menu, 0x08a6132c level key,
   0x08a7fe50 scoreboard). */
void hook_level_exit(void *state, int completed)
{
    exit_completed = completed & 0xff;
    exit_armed = 1;
    if (exit_completed)
        award_level();
    level_exit(state, completed);
}

/* Replaces the save callback (FUN_088b5760) that level_exit's story save ends with. */
void hook_save_done(void)
{
    if (exit_armed)
        g_level_leave = 1;
}

static void start_story_level(int level_id)
{
    u8 *desc = story_descs[level_id - FIRST_STORY];  /* the seed block: the default profile's descriptor */
    struct String path, copy;
    void *icon = g_CurrentLevel.icon;

    if (icon) {  /* what app_go_to_pod would have released */
        g_CurrentLevel.icon = 0;
        resource_release(icon);
    }
    set_current_level(desc);
    skip_used = 0;
    teleporting = 0;
    refresh_labels();
    g_level_is_progress = 1;     /* DAT_08be8920: the pod sets it for game levels */
    String_ctor(&path);
    level_file_path(desc, &path, 0);
    g_level_in_pod = 0;          /* DAT_08be8921: not the pod's dressing-up level */
    String_copy(&copy, &path);
    start_level(&copy);
    String_dtor(&copy);
    String_dtor(&path);
}

/* Replaces IntroMovieState::update's jal intro_start_first_level (0x088c4318): on a new profile
   (tutorial video 4 not watched, which is every boot here) the game loads The Introduction
   straight after the intro movies, without a level descriptor. The run starts it through the
   chain instead, so its end leads on to the next level. */
void hook_first_boot_start(void)
{
    run_started = 1;
    furthest = 0;
    apply_unlocks();
    start_story_level(chain_order[0]);
}

/* Replaces jal app_go_to_pod at 0x088b582c (level_state_finish leaving the level). */
void hook_level_leave(void *app)
{
    int completed = exit_completed;
    int index;

    exit_completed = 0;
    exit_armed = 0;
    g_level_leave = 0;
    if (run_started && completed) {
        index = chain_index(g_CurrentLevel.level_id);
        if (index >= 0) {
            if (index == furthest)
                furthest++;
            /* an older level (a teleporter trip) also goes back to the furthest one */
            if (furthest < chain_length) {
                start_story_level(chain_order[furthest]);
                return;
            }
            /* The Procession, the last level, is done: the run is over. */
            sceKernelExitGame();
            return;
        }
    }
    apply_unlocks();
    app_go_to_pod(app);
}
