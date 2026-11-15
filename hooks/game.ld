/* SPDX-License-Identifier: GPL-3.0-or-later. LBPP Randomizer (see README.md). */
/* Addresses in the game (the decrypted UCUS-98744 EBOOT.BIN, SHA-1 298d8195...) that the randomizer uses. */
PrizeBubble_ctor = 0x08a7c8c8;   /* PrizeBubble::PrizeBubble(this, uid, record + 3 words, type) */
catalog_parse = 0x0894d114;      /* (group entry, data base, context): one top-level RSRC group */
set_current_level = 0x088d20e4;  /* (descriptor): fills g_CurrentLevel */
level_exit = 0x088b66a4;         /* (level state, completed): records the result, saves, sets the leave flag */
app_go_to_pod = 0x089e91e8;      /* (app state): leaves the level for the pod (a LoadingState into PodState) */
start_level = 0x088b4b44;        /* (String *path): loads and enters a level (the pod's Play, Restart Level) */
level_file_path = 0x088d4244;    /* (descriptor, String *out, file type) */
resource_release = 0x08805084;
String_ctor = 0x08a986a0;        /* String::String(): empty */
String_copy = 0x08a98740;        /* String::String(const String &) */
String_dtor = 0x08a98684;
g_Profile = 0x08be898c;          /* void *: the pod's profile, NULL in a level */
g_CurrentLevel = 0x08be842c;
g_level_is_progress = 0x08be8920; /* u8 DAT_08be8920 */
g_level_in_pod = 0x08be8921;      /* u8 DAT_08be8921 */
g_level_leave = 0x08be8199;      /* u8 DAT_08be8199: leave the level once the exit is done */
scoreboard_activate = 0x08a8090c; /* (scoreboard): Sackboy reaching it */
prize_item_owned = 0x08995a10;   /* (popit menu, resource key[2]): the item is owned */
gameplay_manager_popit_menu = 0x0896dc3c;
gameplay_manager_event_at = 0x0896e378; /* (out event, gm, index) */
ui_text = 0x0896fab0;            /* (resources, id): UTF-16 text */
pod_load_story_slots = 0x088ddab8; /* (profile, relayout) */
g_GameState = 0x08bf0874;        /* GameState * */
g_GameplayManager = 0x08bea018;  /* GameplayManager * */
g_CharacterInfo = 0x08bf0d04;    /* CharacterInfo *: deaths at +0x350 */
g_LevelProgressTable = 0x08be77cc; /* LevelProgressTable *: records[LevelId - 1] */
Text_set_text = 0x089d02e0;      /* (text widget, ui string, flag) */
ui_string_init = 0x08974dc4;     /* (out, const u16 *): {s, length, shared buffer} */
shared_buffer_release = 0x088cbf40;
pause_menu_event = 0x089c0efc;   /* (out event, id, ...): a 0x10-byte event, id at +8 */
Scoreboard_update = 0x08a81940;  /* (float dt, scoreboard) */
scoreboard_spawn_player = 0x08a7fbcc; /* Scoreboard::vf61: Sackboy respawned at the podium */
grab_release = 0x08909ef4;       /* (grab block = CharacterInfo + 0x3f0, clear flag) */
pod_send_start_event = 0x088ce238; /* (pod): event 0x4e26 with the start node (pod + 0x100) */
sceKernelExitGame = 0x08ba6634; /* LoadExecForUser import stub */

seed = 0x08c20000;               /* struct seed_data: written by the randomizer after the hooks */
