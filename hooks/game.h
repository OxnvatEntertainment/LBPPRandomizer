/* SPDX-License-Identifier: GPL-3.0-or-later. LBPP Randomizer (see README.md). */
/* Declarations of the game functions and globals in game.ld. */
#ifndef GAME_H
#define GAME_H
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;

struct String { u32 words[6]; };  /* {char *data, ?, vector<char> begin/end/capacity}; callers reserve 24 bytes */
struct CurrentLevel {
    u8 progress[0x24];
    int level_id;   /* +0x24 */
    int kind;       /* +0x28: 3-5 levels from the game files */
    u8 pad[0x64 - 0x2c];
    void *icon;     /* +0x64: the level's icon resource (level_icon_resource) */
    u8 rest[0x3ac - 0x68];
};

void PrizeBubble_ctor(void *self, u32 uid, const u32 *data, int type);
int catalog_parse(void *entry, u32 base, void *ctx);
void set_current_level(void *desc);
void level_exit(void *state, int completed);
void app_go_to_pod(void *app);
void start_level(struct String *path);
void level_file_path(void *desc, struct String *out, int type);
void resource_release(void *object);
void String_ctor(struct String *s);
void String_copy(struct String *s, const struct String *other);
void String_dtor(struct String *s);

struct LevelProgress { u32 flags; int level_id; int high_score; int last_played; u8 rest[0xc]; };
struct LevelProgressTable { void *story; struct LevelProgress *records; int count; };

struct UiString { const u16 *text; int length; u32 buffer[2]; };
u32 **pause_menu_event(u32 **out, int id, void *flag);
void Text_set_text(void *text, void *string, int flag);
void ui_string_init(struct UiString *out, const u16 *text);
void shared_buffer_release(void *buffer);
void scoreboard_activate(void *board);
void Scoreboard_update(float dt, void *board);
void scoreboard_spawn_player(void *board);
void grab_release(void *grab, int clear);
int prize_item_owned(void *menu, u32 *key);
void *gameplay_manager_popit_menu(void *gm);
void gameplay_manager_event_at(u32 **out, void *gm, int index);
void *ui_text(void *resources, int id);
void pod_load_story_slots(void *profile, int relayout);
void pod_send_start_event(u8 *pod);
void sceKernelExitGame(void);

extern void *g_GameState;
extern void *g_GameplayManager;
extern void *g_CharacterInfo;
extern struct LevelProgressTable *g_LevelProgressTable;
extern u8 *g_Profile;
extern struct CurrentLevel g_CurrentLevel;
extern u8 g_level_is_progress;
extern u8 g_level_in_pod;
extern u8 g_level_leave;
#endif
