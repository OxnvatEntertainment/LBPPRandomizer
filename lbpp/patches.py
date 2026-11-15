# SPDX-License-Identifier: GPL-3.0-or-later
# LBPP Randomizer (see README.md)
"""What the randomizer changes in the executable, and the story it works on.

Every patch states the word it expects to find, so a different executable is refused instead of
being broken. Addresses are in the decrypted UCUS-98744 executable (SHA-1 below).
"""

ELF_SHA1 = "298d81958f207abf4b7c60adb0b11bf32693a863"  # the decrypted EBOOT.BIN of UCUS-98744
GAME_ID = "UCUS98744"

# The story: LevelId 8 (The Introduction) to 45, by file in lbp_archive.arc.
STORY = {
    8: "Credits/CreditsLevel01", 9: "Australia/AustraliaLevel01", 10: "Australia/AustraliaLevel02",
    11: "Australia/AustraliaLevel03a", 12: "Australia/AustraliaLevel03b",
    13: "Australia/AustraliaMinigame02", 14: "Australia/AustraliaMinigame01",
    15: "China/ChinaLevel01", 16: "China/ChinaLevel02", 17: "China/ChinaLevel03",
    18: "China/ChinaMinigame01", 19: "China/ChinaMinigame02",
    20: "Persia/PersiaLevel01", 21: "Persia/PersiaLevel02", 22: "Persia/PersiaLevel03",
    23: "Persia/PersiaMinigame01", 24: "Persia/PersiaMinigame02",
    25: "Desert/DesertLevel01", 26: "Desert/DesertLevel02", 27: "Desert/DesertLevel03",
    28: "Desert/DesertMinigame01", 29: "Desert/DesertMinigame02",
    30: "Alps/AlpsLevel01", 31: "Alps/AlpsLevel02", 32: "Alps/AlpsLevel03",
    33: "Alps/AlpsMinigame01", 34: "Alps/AlpsMinigame02",
    35: "Hollywood/HollywoodLevel01A", 36: "Hollywood/HollywoodLevel01B",
    37: "Hollywood/HollywoodLevel02", 38: "Hollywood/HollywoodLevel03a",
    39: "Hollywood/HollywoodMinigame01", 40: "Hollywood/HollywoodMinigame02",
    41: "Brazil/BrazilLevel01", 42: "Brazil/BrazilLevel02", 43: "Brazil/BrazilLevel03",
    44: "Brazil/BrazilMinigame01", 45: "Brazil/BrazilMinigame02",
}
FIRST_LEVEL, LAST_LEVEL = 8, 43  # The Introduction, The Procession

LEVEL_NAMES = {
    8: "The Introduction", 9: "Walkabout", 10: "Gift of the Grab", 11: "Didgeridoo Didgeridon't",
    12: "Dreamtime", 13: "Wave Goodbye (bonus)", 14: "Shear Madness (bonus)", 15: "Mortar Do",
    16: "Dragon on a Bite", 17: "Eggstraction", 18: "Double Dragons (bonus)",
    19: "Stamp Collector (bonus)", 20: "Cheeky Monkey", 21: "Thieves' Den", 22: "Rugs and Kisses",
    23: "Ladderal Thinking (bonus)", 24: "Monkey Puzzle Tree (bonus)", 25: "Get the Hump",
    26: "Sand Ahoy", 27: "Fun Pharaoh", 28: "Out Foxed (bonus)", 29: "Sackar Rally (bonus)",
    30: "Mountin' Excitement", 31: "Peak Performance", 32: "Dogged Determination",
    33: "Roque 'n' Roller (bonus)", 34: "Off Piste (bonus)", 35: "Stitch Gordon",
    36: "Frying Saucers", 37: "The Sewn Identity", 38: "Opening Fright",
    39: "I Race Dead People (bonus)", 40: "Leap of Faith (bonus)", 41: "Crashing the Party",
    42: "Road to Joy", 43: "The Procession", 44: "Feeling Hot (bonus)", 45: "Golissimo (bonus)",
}


def jal(target):
    return 0x0c000000 | ((target >> 2) & 0x03ffffff)


PRIZE_BUBBLE_CTOR = 0x08a7c8c8
SET_CURRENT_LEVEL, LEVEL_EXIT, APP_GO_TO_POD = 0x088d20e4, 0x088b66a4, 0x089e91e8
POD_LOAD_STORY_SLOTS = 0x088ddab8
PAUSE_MENU_EVENT = 0x089c0efc

# (call site, hook, original target): jal patches
CALL_HOOKS = [
    (0x08951efc, "hook_prize_bubble_load", PRIZE_BUBBLE_CTOR),  # level_load_record, PBUB
    (0x088d0714, "hook_pod_set_current_level", SET_CURRENT_LEVEL),  # the pod's Play
    (0x08962450, "hook_level_exit", LEVEL_EXIT),  # pause menu: Return to My Pod
    (0x08a6132c, "hook_level_exit", LEVEL_EXIT),  # level key
    (0x08a7fe50, "hook_level_exit", LEVEL_EXIT),  # scoreboard
    (0x088b582c, "hook_level_leave", APP_GO_TO_POD),  # level_state_finish: leaving for the pod
    (0x088c4308, "hook_level_leave", APP_GO_TO_POD),  # IntroMovieState::update: after the pod movie
    (0x088c4318, "hook_first_boot_start", 0x088c40e0),  # IntroMovieState::update: The Introduction
    (0x088d13d8, "hook_pod_load_story_slots", POD_LOAD_STORY_SLOTS),  # unlocks, pod areas
    (0x088f0638, "hook_pod_load_story_slots", POD_LOAD_STORY_SLOTS),
    (0x088f04fc, "hook_pod_send_start_event", 0x088ce238),  # the pod starts on the Earth
    (0x089c3a54, "hook_pause_button_text", 0x0896fab0),  # pause_menu_button's ui_text
    (0x089c3a70, "hook_pause_button_set_text", 0x089d02e0),  # and its Text::set_text
    (0x089c3c14, "hook_pause_button_event", PAUSE_MENU_EVENT),  # Return to Main Menu's event
    (0x089c3dc8, "hook_pause_button_event", PAUSE_MENU_EVENT),  # Credits' event
    (0x089622b4, "hook_pause_event_at", 0x0896e378),  # pause_menu_select's gameplay_manager_event_at
]

# (lui address, register, hook, original function): lui/addiu pairs loading a function address
ADDRESS_LOADS = [
    (0x0894c940, 5, "hook_catalog_parse", 0x0894d114),  # the catalog walk's callback, in $a1
    (0x088b6408, 2, "hook_save_done", 0x088b5760),  # level_exit's save callback, in $v0
]

# (vtable slot, hook, original method)
VTABLE_HOOKS = [
    (0x08bc2928, "hook_scoreboard_update", 0x08a81940),  # Scoreboard::update (slot 8)
]

# (address, new word, original word)
WORD_PATCHES = [
    # No saving, a fresh run every boot: the Memory Stick is never "ready" (SavedataManager
    # +0x6f4), so profile files come from the defaults in the game files and nothing is written.
    (0x08945398, 0x24020000, 0x24020001),  # save manager reset: li $v0, 0
    (0x089474e8, 0xa20006f4, 0xa21106f4),  # SavedataManager::SavedataManager: sb $zero
    (0x08947504, 0xa20006f4, 0xa21106f4),  # the same, after its memset
    (0x088cacac, 0xa20006f4, 0xa20206f4),  # StartupState state 8: sb $zero
    # The story pause page: "Return to Main Menu" and "Credits" become Teleporter and Skip Level
    (0x089c3c1c, 0x240403f0, 0x240401af),  # li $a0, TEXT_TELEPORTER
    (0x089c3dd4, 0x240403f1, 0x240400c4),  # li $a0, TEXT_SKIP
    # Show "Return to Main Menu" even though tutorial video 4 was never watched
    (0x08962b94, 0x24030600, 0x24030400),  # li $v1, 0x600
]


def apply(elf, hooks):
    """Applies every patch to an lbpp.elf.Elf; `hooks` maps hook names to addresses."""
    for site, new, original in WORD_PATCHES:
        elf.write32(site, new, expect=original)
    for site, name, original in CALL_HOOKS:
        elf.write32(site, jal(hooks[name]), expect=jal(original))
    for slot, name, original in VTABLE_HOOKS:
        elf.write32(slot, hooks[name], expect=original)
    for site, reg, name, original in ADDRESS_LOADS:
        def pair(value):
            hi, lo = (value + 0x8000) >> 16, value & 0xffff
            return 0x3c000000 | reg << 16 | hi, 0x24000000 | reg << 21 | reg << 16 | lo
        old, new = pair(original), pair(hooks[name])
        elf.write32(site, new[0], expect=old[0])
        elf.write32(site + 4, new[1], expect=old[1])
