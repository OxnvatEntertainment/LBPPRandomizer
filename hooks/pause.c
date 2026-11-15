/* SPDX-License-Identifier: GPL-3.0-or-later. LBPP Randomizer (see README.md). */
/* Rewards, unlocks and the two pause menu items.

   - Acing a chain level (finishing it with no deaths and without a skip) gives a teleporter,
     owning every prize of its prize bubbles at the end gives a skip; each once per level.
     The prizes are the ones prizes.c saw the level load.
   - The story pause page (pause_menu_page_downloaded_level) keeps its buttons, but "Return to
     Main Menu" (text 0x1af, event 0x715d: the "return to My Pod" question, then 0x714c) is the
     teleporter and "Credits" (0xc4, event 0x7150) the skip. Their text ids are changed to
     TEXT_TELEPORTER / TEXT_SKIP, which hook_pause_button_text answers (pause_menu_button's
     ui_text call, 0x089c3a54). pause_menu_select reads each event with
     gameplay_manager_event_at (0x089622b4); hook_pause_event_at acts on ours and turns the
     ones that must not go on into event 0, which nothing handles.
   - The pause menu is built once (PauseMenu's screen 0), so the two labels are refreshed
     with Text::set_text on the buttons' Text widgets, which hook_pause_button_set_text
     (pause_menu_button's Text::set_text call, 0x089c3a70) records when they are built.
   - A skip puts Sackboy at the level's scoreboard (see hook_scoreboard_update), which then
     runs as usual: its prizes, medals and level_exit(.., 1).
   - Unlocks: the story levels up to the furthest one reached are unlocked (progress flag
     bit 8 clear), every other story level is locked (| 0xc, as level_desc_lock does), in the
     progress table and in the pod's descriptors, before the pod lays out the Earth's slots
     (pod_load_story_slots, called at 0x088d13d8 and 0x088f0638). */
#include "game.h"
#include "rando.h"
#include "seed.h"

#define TEXT_TELEPORTER 0x3f0
#define TEXT_SKIP 0x3f1
#define EVENT_NONE 0       /* no flow transition and no handler: the button does nothing */
#define EVENT_RETURN_ASK 0x715d
#define EVENT_RETURN_YES 0x714c
#define EVENT_CREDITS 0x7150
#define TYPE_SCOREBOARD 0x2b

int teleporters, skips, skip_used, teleporting;
static u8 aced[LAST_STORY + 1], full[LAST_STORY + 1];

/* ---- the game's per-type object maps (std::map<uid, LevelObject *>) ---- */

struct rb_node {
    int color;
    struct rb_node *parent, *left, *right;
    u32 key;
    void *value;
};

static struct rb_node *type_map_header(int type)
{
    u8 *gs = (u8 *)g_GameState;
    return (struct rb_node *)(gs + type * 0x18 + 0x10 + 0xc);
}

static void *first_object(int type)
{
    struct rb_node *h = type_map_header(type);
    return h->left != h ? h->left->value : 0;
}

/* Every prize the level's bubbles hold is owned (prize_bubble_collect's own check, with the
   prize's name as the resource key); 0 for a level without prize bubbles. */
static int all_prizes_owned(void)
{
    void *menu = gameplay_manager_popit_menu(g_GameplayManager);
    int i;

    for (i = 0; i < level_prize_count; i++) {
        const char *name = level_prizes[i], *p = name;
        u32 key[2];
        while (*p)
            p++;
        key[0] = (u32)name;
        key[1] = (u32)(p - name);
        if (!prize_item_owned(menu, key))
            return 0;
    }
    return level_prize_count > 0;
}

void award_level(void)
{
    int id = g_CurrentLevel.level_id;

    if (id < FIRST_STORY || id > LAST_STORY || chain_index(id) < 0)
        return;
    if (!skip_used && g_CharacterInfo && *(int *)((u8 *)g_CharacterInfo + 0x350) == 0 && !aced[id]) {
        aced[id] = 1;
        teleporters++;
    }
    if (!full[id] && all_prizes_owned()) {
        full[id] = 1;
        skips++;
    }
    refresh_labels();
}

/* ---- unlocks ---- */

static void set_locked(u32 *flags, int locked)
{
    if (locked)
        *flags |= 0xc;
    else
        *flags &= ~8u;
}

void apply_unlocks(void)
{
    int i;
    for (i = 0; i < chain_length; i++) {
        int id = chain_order[i], locked = i > furthest;
        if (g_LevelProgressTable && g_LevelProgressTable->records)
            set_locked(&g_LevelProgressTable->records[id - 1].flags, locked);
        if (g_Profile && *(u8 **)(g_Profile + 0x1bc) && *(int *)(g_Profile + 0x1c0) >= id)
            set_locked((u32 *)(*(u8 **)(g_Profile + 0x1bc) + (id - 1) * 0x1cc), locked);
    }
}

/* Replaces the two jal pod_load_story_slots. */
void hook_pod_load_story_slots(void *profile, int relayout)
{
    apply_unlocks();
    pod_lock_areas(profile);
    pod_load_story_slots(profile, relayout);
}

/* ---- the pause menu ---- */

static u16 text_buffers[2][32];

static u16 *utf16_label(u16 *out, const char *text, int count)
{
    u16 *p = out;
    char digits[12];
    int n = 0;

    while (*text)
        *p++ = (u8)*text++;
    *p++ = ' ';
    *p++ = '(';
    do {
        digits[n++] = '0' + count % 10;
        count /= 10;
    } while (count && n < 11);
    while (n)
        *p++ = digits[--n];
    *p++ = ')';
    *p = 0;
    return out;
}

static void *label_widgets[2];
static u32 *button_events[2];  /* the Teleporter and Skip Level buttons' events */
static const u32 button_event_ids[2] = {EVENT_RETURN_ASK, EVENT_CREDITS};

/* Replaces the story page's jal pause_menu_event for "Return to Main Menu" (0x089c3c14) and
   "Credits" (0x089c3dc8): keeps the event object the button will send, so that
   refresh_labels can switch it off (id 0) while there is nothing to use. The menu's flow
   table acts on 0x715d (opening the "return to My Pod" question) before pause_menu_select
   sees it, so the event itself has to change. */
u32 **hook_pause_button_event(u32 **out, int id, void *flag)
{
    pause_menu_event(out, id, flag);
    if (id == EVENT_RETURN_ASK)
        button_events[0] = *out;
    else if (id == EVENT_CREDITS)
        button_events[1] = *out;
    return out;
}
static int pending_label = -1;

static u16 *label_text(int which)
{
    return which == 0 ? utf16_label(text_buffers[0], "Teleporter", teleporters)
                      : utf16_label(text_buffers[1], "Skip Level", skips);
}

/* Replaces pause_menu_button's jal ui_text (0x089c3a54). */
void *hook_pause_button_text(void *resources, int id)
{
    if (id == TEXT_TELEPORTER || id == TEXT_SKIP) {
        pending_label = id - TEXT_TELEPORTER;
        return label_text(pending_label);
    }
    pending_label = -1;
    return ui_text(resources, id);
}

/* Replaces pause_menu_button's jal Text::set_text (0x089c3a70). */
void hook_pause_button_set_text(void *text, void *string, int flag)
{
    Text_set_text(text, string, flag);
    if (pending_label >= 0)
        label_widgets[pending_label] = text;
    pending_label = -1;
}

void refresh_labels(void)
{
    int i;
    for (i = 0; i < 2; i++) {
        struct UiString s;
        if (button_events[i])
            button_events[i][2] = (i == 0 ? teleporters : skips) > 0 ? button_event_ids[i] : EVENT_NONE;
        if (!label_widgets[i])
            continue;
        ui_string_init(&s, label_text(i));
        Text_set_text(label_widgets[i], &s, 0);
        shared_buffer_release(&s.buffer);
    }
}

static void *skip_board;  /* the scoreboard a skip is waiting to put Sackboy at */

static int start_skip(void)
{
    void *board = first_object(TYPE_SCOREBOARD);
    if (!board || skips <= 0 || skip_board || *(float *)((u8 *)board + 0x9c) > 0.0f)
        return 0;
    skips--;
    skip_used = 1;
    skip_board = board;
    refresh_labels();
    return 1;
}

/* Replaces Scoreboard::update in the Scoreboard vtable (slot 8, 0x08bc2928). A pending skip
   puts Sackboy at the scoreboard with the scoreboard's own respawn (Scoreboard::vf61, the
   checkpoint listener's spawn: the podium's position on the middle layer, the collision layer
   change, character_respawn), after letting go of anything he holds. The update that follows
   finds him there and runs the scoreboard as if he had walked up to it. */
void hook_scoreboard_update(float dt, void *board)
{
    if (skip_board == board) {
        skip_board = 0;
        if (g_CharacterInfo) {
            grab_release((u8 *)g_CharacterInfo + 0x3f0, 1);
            scoreboard_spawn_player(board);
        }
    }
    Scoreboard_update(dt, board);
}

/* Replaces pause_menu_select's jal gameplay_manager_event_at (0x089622b4). */
void hook_pause_event_at(u32 **out, void *gm, int index)
{
    u32 *event;
    int in_chain = chain_index(g_CurrentLevel.level_id) >= 0;

    gameplay_manager_event_at(out, gm, index);
    event = *out;
    if (!event || !in_chain)
        return;
    switch (event[2]) {
    case EVENT_RETURN_ASK:
        if (teleporters <= 0)
            event[2] = EVENT_NONE;
        break;
    case EVENT_RETURN_YES:
        if (teleporters <= 0) {
            event[2] = EVENT_NONE;
        } else {
            teleporters--;
            teleporting = 1;
            refresh_labels();
        }
        break;
    case EVENT_CREDITS:
        start_skip();
        event[2] = EVENT_NONE;
        break;
    }
}
