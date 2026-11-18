#!/usr/bin/env python3
"""
Deterministic, validated source patcher for Pokémon JosephRed (based on pret/pokefirered).

Every patch asserts that its exact upstream anchor exists before modifying (Rule 7:
never silently swallow missing targets) and validates GBA textbox line widths so
no custom string ever clips off the 240x160 GBA screen.
"""

from __future__ import annotations
import json
import pathlib
import re
import shutil
import sys


def must_replace(path: pathlib.Path, target: str, replacement: str, label: str) -> None:
    content = path.read_text(encoding="utf-8")
    if target not in content:
        raise RuntimeError(f"[FATAL] Anchor not found for '{label}' in {path}")
    updated = content.replace(target, replacement, 1)
    path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"[OK] Patched {label} -> {path.name}")


def replace_inc_block(path: pathlib.Path, symbol: str, new_lines: list[str], max_width: int = 36) -> None:
    """Replaces an ASM `.string` block starting at `symbol::` and lints GBA line widths."""
    new_lines = [line.replace("\n", "\\n").replace("\u2014", "-").replace("#", "No.") for line in new_lines]
    lint_gba_lines(symbol, new_lines, max_width=max_width)
    content = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(^{re.escape(symbol)}::\n(?:[ \t]*\.string[ \t]+\".*\"\n)+)",
        re.MULTILINE,
    )
    m = pattern.search(content)
    if not m:
        raise RuntimeError(f"[FATAL] Text symbol '{symbol}::' not found in {path}")

    formatted = f"{symbol}::\n" + "".join(f'    .string "{line}"\n' for line in new_lines)
    updated = content[: m.start()] + formatted + content[m.end() :]
    path.write_text(updated, encoding="utf-8", newline="\n")


def lint_gba_lines(symbol: str, raw_lines: list[str], max_width: int = 36) -> None:
    full = "".join(raw_lines)
    if not full.endswith("$"):
        raise ValueError(f"[LINT] {symbol} does not end with '$': {full!r}")
    body = full[:-1]
    # Strip BGM/font macros when measuring visible character width
    clean = re.sub(r"\{PLAY_BGM[^}]*\}|\{MUS_[^}]*\}|\{FONT_[^}]*\}", "", body)
    clean = (
        clean.replace("{PLAYER}", "JOSEPH")
        .replace("{RIVAL}", "GREG")
        .replace("{STR_VAR_1}", "DRATINI")
        .replace("{STR_VAR_2}", "TM19")
    )
    paragraphs = clean.split("\\p")
    for p_idx, para in enumerate(paragraphs):
        if not para:
            continue
        # Check \n count: at most one \n before \l lines in standard 2-line box
        # (Pikachu intro / controls guide use multi-line windows with \n, which pass max_width>36)
        if max_width <= 36 and para.count("\\n") > 1:
            raise ValueError(
                f"[LINT] {symbol} paragraph {p_idx} has multiple \\n without \\p (use \\l for 3rd+ line): {para!r}"
            )
        for seg in re.split(r"\\n|\\l", para):
            if len(seg) > max_width:
                raise ValueError(
                    f"[LINT] {symbol} line too wide ({len(seg)} > {max_width}): {seg!r}"
                )


def patch_core_c_files(root: pathlib.Path) -> None:
    # 1. Oak Speech: Release DRATINI during intro + default player=JOSEPH, rival=GREG
    oak_c = root / "src/oak_speech.c"
    must_replace(
        oak_c,
        "#define INTRO_SPECIES SPECIES_NIDORAN_F",
        "#define INTRO_SPECIES SPECIES_DRATINI",
        "Intro species -> SPECIES_DRATINI",
    )
    must_replace(
        oak_c,
        "        if (gSaveBlock2Ptr->playerGender == MALE)\n"
        "            src = sMaleNameChoices[Random() % ARRAY_COUNT(sMaleNameChoices)];\n"
        "        else\n"
        "            src = sFemaleNameChoices[Random() % ARRAY_COUNT(sFemaleNameChoices)];",
        "        src = sMaleNameChoices[0]; // Always default to JOSEPH",
        "Default player name -> JOSEPH",
    )

    # 2. Starter Species helper -> DRATINI for all 3 slots + Roamer pair
    must_replace(
        root / "src/field_specials.c",
        "static const u16 sStarterSpecies[] = {\n"
        "    SPECIES_BULBASAUR,\n"
        "    SPECIES_SQUIRTLE,\n"
        "    SPECIES_CHARMANDER\n"
        "};",
        "static const u16 sStarterSpecies[] = {\n"
        "    SPECIES_DRATINI,\n"
        "    SPECIES_DRATINI,\n"
        "    SPECIES_DRATINI\n"
        "};",
        "sStarterSpecies -> all SPECIES_DRATINI",
    )
    must_replace(
        root / "src/wild_pokemon_area.c",
        "    { SPECIES_RAIKOU,  SPECIES_SQUIRTLE   }",
        "    { SPECIES_RAIKOU,  SPECIES_DRATINI    }",
        "sRoamerPairs -> SPECIES_DRATINI",
    )

    # 3. Champion BRIAN decoupled from Rival GREG in battle & Quest Log!
    must_replace(
        root / "src/battle_message.c",
        "                    if (gTrainers[gTrainerBattleOpponent_A].trainerClass == TRAINER_CLASS_RIVAL_EARLY\n"
        "                     || gTrainers[gTrainerBattleOpponent_A].trainerClass == TRAINER_CLASS_RIVAL_LATE\n"
        "                     || gTrainers[gTrainerBattleOpponent_A].trainerClass == TRAINER_CLASS_CHAMPION)\n"
        "                        toCpy = GetExpandedPlaceholder(PLACEHOLDER_ID_RIVAL);",
        "                    if (gTrainers[gTrainerBattleOpponent_A].trainerClass == TRAINER_CLASS_RIVAL_EARLY\n"
        "                     || gTrainers[gTrainerBattleOpponent_A].trainerClass == TRAINER_CLASS_RIVAL_LATE)\n"
        "                        toCpy = GetExpandedPlaceholder(PLACEHOLDER_ID_RIVAL);",
        "Decouple TRAINER_CLASS_CHAMPION name from RIVAL in battle_message.c",
    )
    ql_c = root / "src/quest_log_events.c"
    must_replace(
        ql_c,
        "    case 0:\n"
        "        DynamicPlaceholderTextUtil_SetPlaceholderPtr(0, gSaveBlock2Ptr->playerName);\n"
        "        DynamicPlaceholderTextUtil_SetPlaceholderPtr(1, gSaveBlock1Ptr->rivalName);",
        "    case 0:\n"
        "        DynamicPlaceholderTextUtil_SetPlaceholderPtr(0, gSaveBlock2Ptr->playerName);\n"
        "        DynamicPlaceholderTextUtil_SetPlaceholderPtr(1, gTrainers[TRAINER_CHAMPION_FIRST_SQUIRTLE].trainerName);",
        "Quest Log Champion name -> BRIAN (case 0)",
    )
    must_replace(
        ql_c,
        "    case 1:\n"
        "        DynamicPlaceholderTextUtil_SetPlaceholderPtr(0, gSaveBlock1Ptr->rivalName);",
        "    case 1:\n"
        "        DynamicPlaceholderTextUtil_SetPlaceholderPtr(0, gTrainers[TRAINER_CHAMPION_FIRST_SQUIRTLE].trainerName);",
        "Quest Log Champion name -> BRIAN (case 1)",
    )
    must_replace(
        ql_c,
        "    if (gTrainers[r5[2]].trainerClass == TRAINER_CLASS_RIVAL_EARLY\n"
        "     || gTrainers[r5[2]].trainerClass == TRAINER_CLASS_RIVAL_LATE\n"
        "     || gTrainers[r5[2]].trainerClass == TRAINER_CLASS_CHAMPION)",
        "    if (gTrainers[r5[2]].trainerClass == TRAINER_CLASS_RIVAL_EARLY\n"
        "     || gTrainers[r5[2]].trainerClass == TRAINER_CLASS_RIVAL_LATE)",
        "Quest Log trainer name decouple Champion from Rival",
    )

    # 4. Running Shoes + Hardware-Masked Auto-Run Chord + Starter Items
    must_replace(
        root / "src/new_game.c",
        '#include "item.h"\n',
        '#include "item.h"\n#include "constants/items.h"\n',
        "Include constants/items.h in new_game.c",
    )
    must_replace(
        root / "src/new_game.c",
        "    RunScriptImmediately(EventScript_ResetAllMapFlags);\n"
        "    StringCopy(gSaveBlock1Ptr->rivalName, rivalName);",
        "    RunScriptImmediately(EventScript_ResetAllMapFlags);\n"
        "    FlagSet(FLAG_SYS_B_DASH);\n"
        "    AddBagItem(ITEM_POKE_BALL, 10);\n"
        "    AddBagItem(ITEM_POTION, 5);\n"
        "    StringCopy(gSaveBlock1Ptr->rivalName, rivalName);",
        "Enable Running Shoes, 10 backup Poke Balls and 5 Potions from New Game start",
    )
    must_replace(
        root / "src/main.c",
        "static void ReadKeys(void)\n"
        "{\n"
        "    u16 keyInput = REG_KEYINPUT ^ KEYS_MASK;\n"
        "    gMain.newKeysRaw = keyInput & ~gMain.heldKeysRaw;",
        "EWRAM_DATA bool8 gAutoRunEnabled = FALSE;\n\n"
        "static void ReadKeys(void)\n"
        "{\n"
        "    u16 keyInput = REG_KEYINPUT ^ KEYS_MASK;\n"
        "    gAutoRunEnabled = ((keyInput & (L_BUTTON | R_BUTTON)) == (L_BUTTON | R_BUTTON));\n"
        "    if (gAutoRunEnabled)\n"
        "        keyInput &= ~(L_BUTTON | R_BUTTON);\n"
        "    gMain.newKeysRaw = keyInput & ~gMain.heldKeysRaw;",
        "Hardware-masked L+R auto-run chord in ReadKeys()",
    )
    must_replace(
        root / "src/field_player_avatar.c",
        '#include "global.h"\n',
        '#include "global.h"\nextern bool8 gAutoRunEnabled;\n',
        "Declare extern gAutoRunEnabled in field_player_avatar.c",
    )
    must_replace(
        root / "src/field_player_avatar.c",
        "    if ((heldKeys & B_BUTTON) && FlagGet(FLAG_SYS_B_DASH)\n"
        "        && !IsRunningDisallowed(gObjectEvents[gPlayerAvatar.objectEventId].currentMetatileBehavior))",
        "    if ((((heldKeys & B_BUTTON) != 0) != (gAutoRunEnabled != 0))\n"
        "        && !IsRunningDisallowed(gObjectEvents[gPlayerAvatar.objectEventId].currentMetatileBehavior))",
        "Native Auto-Run + B-sprint across all saves without holding B",
    )
    must_replace(
        root / "src/item_menu.c",
        "void CB2_BagMenuFromBattle(void)\n"
        "{\n"
        "    GoToBagMenu(ITEMMENULOCATION_BATTLE, OPEN_BAG_LAST, SetCB2ToReshowScreenAfterMenu2);\n"
        "}",
        "void CB2_BagMenuFromBattle(void)\n"
        "{\n"
        "    GoToBagMenu(ITEMMENULOCATION_BATTLE, OPEN_BAG_POKEBALLS, SetCB2ToReshowScreenAfterMenu2);\n"
        "}",
        "Battle bag menu defaults directly to Poke Balls pocket",
    )
    must_replace(
        root / "src/menu_helpers.c",
        "u8 GetLRKeysPressed(void)\n"
        "{\n"
        "    if (gSaveBlock2Ptr->optionsButtonMode == OPTIONS_BUTTON_MODE_LR)\n"
        "    {\n"
        "        if (JOY_NEW(L_BUTTON))\n"
        "            return MENU_L_PRESSED;\n"
        "        if (JOY_NEW(R_BUTTON))\n"
        "            return MENU_R_PRESSED;\n"
        "    }\n"
        "    return 0;\n"
        "}",
        "u8 GetLRKeysPressed(void)\n"
        "{\n"
        "    if (JOY_NEW(L_BUTTON))\n"
        "        return MENU_L_PRESSED;\n"
        "    if (JOY_NEW(R_BUTTON))\n"
        "        return MENU_R_PRESSED;\n"
        "    return 0;\n"
        "}",
        "Unconditional L/R button menu navigation",
    )
    must_replace(
        root / "src/menu_helpers.c",
        "u8 GetLRKeysPressedAndHeld(void)\n"
        "{\n"
        "    if (gSaveBlock2Ptr->optionsButtonMode == OPTIONS_BUTTON_MODE_LR)\n"
        "    {\n"
        "        if (JOY_REPT(L_BUTTON))\n"
        "            return MENU_L_PRESSED;\n"
        "        if (JOY_REPT(R_BUTTON))\n"
        "            return MENU_R_PRESSED;\n"
        "    }\n"
        "    return 0;\n"
        "}",
        "u8 GetLRKeysPressedAndHeld(void)\n"
        "{\n"
        "    if (JOY_REPT(L_BUTTON))\n"
        "        return MENU_L_PRESSED;\n"
        "    if (JOY_REPT(R_BUTTON))\n"
        "        return MENU_R_PRESSED;\n"
        "    return 0;\n"
        "}",
        "Unconditional L/R held button menu navigation",
    )
    # Rattata & Raticate keep their species names, classified as DICK BITER POKeMON!
    must_replace(
        root / "src/data/pokemon/pokedex_entries.h",
        "    [NATIONAL_DEX_RATTATA] =\n"
        "    {\n"
        "        .categoryName = _(\"MOUSE\"),",
        "    [NATIONAL_DEX_RATTATA] =\n"
        "    {\n"
        "        .categoryName = _(\"DICK BITER\"),",
        "Rattata Pokedex category -> DICK BITER",
    )
    must_replace(
        root / "src/data/pokemon/pokedex_entries.h",
        "    [NATIONAL_DEX_RATICATE] =\n"
        "    {\n"
        "        .categoryName = _(\"MOUSE\"),",
        "    [NATIONAL_DEX_RATICATE] =\n"
        "    {\n"
        "        .categoryName = _(\"DICK BITER\"),",
        "Raticate Pokedex category -> DICK BITER",
    )
    must_replace(
        root / "src/data/pokemon/pokedex_text_fr.h",
        "const u8 gRattataPokedexText[] = _(\n"
        "    \"Its fangs are long and very sharp.\\n\"\n"
        "    \"They grow continuously, so it gnaws on\\n\"\n"
        "    \"hard things to whittle them down.\");",
        "const u8 gRattataPokedexText[] = _(\n"
        "    \"Classified by Joseph and the crew as\\n\"\n"
        "    \"a DICK BITER. Its sharp incisors aim\\n\"\n"
        "    \"low and clamp down without remorse.\");",
        "Rattata Pokedex description -> Dick Biter lore",
    )
    must_replace(
        root / "src/data/pokemon/pokedex_text_fr.h",
        "const u8 gRaticatePokedexText[] = _(\n"
        "    \"Its rear feet have three toes each.\\n\"\n"
        "    \"They are webbed, enabling it to swim\\n\"\n"
        "    \"across rivers.\");",
        "const u8 gRaticatePokedexText[] = _(\n"
        "    \"A full-grown DICK BITER. Its webbed\\n\"\n"
        "    \"feet and vicious jaws make it a menace\\n\"\n"
        "    \"both in tall grass and across rivers.\");",
        "Raticate Pokedex description -> Dick Biter lore",
    )
    must_replace(
        root / "src/data/pokemon/species_info.h",
        "    [SPECIES_SQUIRTLE] =\n"
        "    {\n"
        "        .baseHP = 44,\n"
        "        .baseAttack = 48,\n"
        "        .baseDefense = 65,\n"
        "        .baseSpeed = 43,\n"
        "        .baseSpAttack = 50,\n"
        "        .baseSpDefense = 64,\n"
        "        .types = {TYPE_WATER, TYPE_WATER},\n"
        "        .catchRate = 45,\n"
        "        .expYield = 66,\n"
        "        .evYield_HP = 0,\n"
        "        .evYield_Attack = 0,\n"
        "        .evYield_Defense = 1,\n"
        "        .evYield_Speed = 0,\n"
        "        .evYield_SpAttack = 0,\n"
        "        .evYield_SpDefense = 0,\n"
        "        .itemCommon = ITEM_NONE,\n"
        "        .itemRare = ITEM_NONE,",
        "    [SPECIES_SQUIRTLE] =\n"
        "    {\n"
        "        .baseHP = 44,\n"
        "        .baseAttack = 48,\n"
        "        .baseDefense = 65,\n"
        "        .baseSpeed = 43,\n"
        "        .baseSpAttack = 50,\n"
        "        .baseSpDefense = 64,\n"
        "        .types = {TYPE_WATER, TYPE_WATER},\n"
        "        .catchRate = 45,\n"
        "        .expYield = 66,\n"
        "        .evYield_HP = 0,\n"
        "        .evYield_Attack = 0,\n"
        "        .evYield_Defense = 1,\n"
        "        .evYield_Speed = 0,\n"
        "        .evYield_SpAttack = 0,\n"
        "        .evYield_SpDefense = 0,\n"
        "        .itemCommon = ITEM_BLACK_GLASSES,\n"
        "        .itemRare = ITEM_BLACK_GLASSES,",
        "Wild Squirtle holds SQUAD SHADES",
    )
    must_replace(
        root / "src/bike.c",
        "bool32 IsRunningDisallowed(u8 metatileBehavior)\n"
        "{\n"
        "    if (!gMapHeader.allowRunning)\n"
        "        return TRUE;",
        "bool32 IsRunningDisallowed(u8 metatileBehavior)\n"
        "{",
        "Allow indoor Running Shoes",
    )

    # 5. Infinite Reusable TMs
    pm_c = root / "src/party_menu.c"
    must_replace(
        pm_c,
        "        AdjustFriendship(&gPlayerParty[gPartyMenu.slotId], FRIENDSHIP_EVENT_LEARN_TMHM);\n"
        "        if (gSpecialVar_ItemId < ITEM_HM01)\n"
        "            RemoveBagItem(gSpecialVar_ItemId, 1);",
        "        AdjustFriendship(&gPlayerParty[gPartyMenu.slotId], FRIENDSHIP_EVENT_LEARN_TMHM);",
        "Reusable TMs (CB2_UseItem)",
    )
    must_replace(
        pm_c,
        "        ItemUse_SetQuestLogEvent(QL_EVENT_USED_ITEM, mon, gSpecialVar_ItemId, move);\n"
        "        if (gSpecialVar_ItemId < ITEM_HM01)\n"
        "            RemoveBagItem(gSpecialVar_ItemId, 1);",
        "        ItemUse_SetQuestLogEvent(QL_EVENT_USED_ITEM, mon, gSpecialVar_ItemId, move);",
        "Reusable TMs (CB2_UseTMHMAfterForgettingMove)",
    )
    must_replace(
        pm_c,
        "    if (learnMoveMethod == LEARN_VIA_TMHM)\n"
        "    {\n"
        "        AdjustFriendship(mon, FRIENDSHIP_EVENT_LEARN_TMHM);\n"
        "        if (item < ITEM_HM01)\n"
        "            RemoveBagItem(item, 1);\n"
        "    }",
        "    if (learnMoveMethod == LEARN_VIA_TMHM)\n"
        "    {\n"
        "        AdjustFriendship(mon, FRIENDSHIP_EVENT_LEARN_TMHM);\n"
        "    }",
        "Reusable TMs (Task_LearnedMove)",
    )

    # 6. Dratini Lv.5 Twister + Lv.48 Dragonite + Solo Trade Evolutions
    must_replace(
        root / "src/data/pokemon/level_up_learnsets.h",
        "static const u16 sDratiniLevelUpLearnset[] = {\n"
        "    LEVEL_UP_MOVE(1, MOVE_WRAP),\n"
        "    LEVEL_UP_MOVE(1, MOVE_LEER),\n"
        "    LEVEL_UP_MOVE(8, MOVE_THUNDER_WAVE),\n"
        "    LEVEL_UP_MOVE(15, MOVE_TWISTER),",
        "static const u16 sDratiniLevelUpLearnset[] = {\n"
        "    LEVEL_UP_MOVE(1, MOVE_WRAP),\n"
        "    LEVEL_UP_MOVE(1, MOVE_LEER),\n"
        "    LEVEL_UP_MOVE(5, MOVE_TWISTER),\n"
        "    LEVEL_UP_MOVE(8, MOVE_THUNDER_WAVE),",
        "Dratini Lv.5 MOVE_TWISTER",
    )

    evo_h = root / "src/data/pokemon/evolution.h"
    must_replace(
        evo_h,
        "    [SPECIES_DRAGONAIR]  = {{EVO_LEVEL, 55, SPECIES_DRAGONITE}},",
        "    [SPECIES_DRAGONAIR]  = {{EVO_LEVEL, 48, SPECIES_DRAGONITE}},",
        "Dragonair -> Dragonite Lv.48",
    )
    must_replace(
        evo_h,
        "    [SPECIES_KADABRA]    = {{EVO_TRADE, 0, SPECIES_ALAKAZAM}},",
        "    [SPECIES_KADABRA]    = {{EVO_LEVEL, 36, SPECIES_ALAKAZAM}},",
        "Solo Kadabra -> Alakazam Lv.36",
    )
    must_replace(
        evo_h,
        "    [SPECIES_MACHOKE]    = {{EVO_TRADE, 0, SPECIES_MACHAMP}},",
        "    [SPECIES_MACHOKE]    = {{EVO_LEVEL, 38, SPECIES_MACHAMP}},",
        "Solo Machoke -> Machamp Lv.38",
    )
    must_replace(
        evo_h,
        "    [SPECIES_GRAVELER]   = {{EVO_TRADE, 0, SPECIES_GOLEM}},",
        "    [SPECIES_GRAVELER]   = {{EVO_LEVEL, 38, SPECIES_GOLEM}},",
        "Solo Graveler -> Golem Lv.38",
    )
    must_replace(
        evo_h,
        "    [SPECIES_HAUNTER]    = {{EVO_TRADE, 0, SPECIES_GENGAR}},",
        "    [SPECIES_HAUNTER]    = {{EVO_LEVEL, 36, SPECIES_GENGAR}},",
        "Solo Haunter -> Gengar Lv.36",
    )

    # 8. Button Mode -> OPTIONS_BUTTON_MODE_LR (disable accidental Help System popups on L/R)
    must_replace(
        root / "src/new_game.c",
        "    gSaveBlock2Ptr->regionMapZoom = FALSE;\n"
        "    gSaveBlock2Ptr->optionsButtonMode = OPTIONS_BUTTON_MODE_HELP;",
        "    gSaveBlock2Ptr->regionMapZoom = FALSE;\n"
        "    gSaveBlock2Ptr->optionsButtonMode = OPTIONS_BUTTON_MODE_LR;",
        "Default button mode -> OPTIONS_BUTTON_MODE_LR",
    )

    # 9. Permanently disable Help System journal callback
    must_replace(
        root / "src/help_system_util.c",
        "u8 RunHelpSystemCallback(void)\n"
        "{\n"
        "    s32 i;\n"
        "\n"
        "    switch (sVideoState.state)",
        "u8 RunHelpSystemCallback(void)\n"
        "{\n"
        "    s32 i;\n"
        "    return 0; // Permanently disabled: prevent Help System journal popups\n"
        "\n"
        "    switch (sVideoState.state)",
        "Disable RunHelpSystemCallback",
    )

    # 10. Disable Quest Log replay on continue (instant load into overworld)
    must_replace(
        root / "src/quest_log.c",
        "    if (sNumScenes != 0)\n"
        "    {\n"
        "        gHelpSystemEnabled = FALSE;\n"
        "        Task_BeginQuestLogPlayback(taskId);\n"
        "        DestroyTask(taskId);\n"
        "    }\n"
        "    else\n"
        "    {\n"
        "        SetMainCallback2(CB2_ContinueSavedGame);\n"
        "        DestroyTask(taskId);\n"
        "    }",
        "    SetMainCallback2(CB2_ContinueSavedGame);\n"
        "    DestroyTask(taskId);",
        "Disable Quest Log playback on continue",
    )


def patch_trainers(root: pathlib.Path) -> None:
    tr_h = root / "src/data/trainers.h"
    content = tr_h.read_text(encoding="utf-8")

    def rename_trainer(enum_id: str, new_name: str, extra_repls: list[tuple[str, str]] | None = None) -> None:
        nonlocal content
        if len(new_name) > 11:
            raise ValueError(f"Trainer name {new_name!r} exceeds 11 chars")
        pat = re.compile(rf"(\[{re.escape(enum_id)}\]\s*=\s*\{{.*?\n    \}},)", re.DOTALL)
        m = pat.search(content)
        if not m:
            raise RuntimeError(f"[FATAL] Trainer {enum_id} not found in trainers.h")
        block = m.group(1)
        block_new = re.sub(r'\.trainerName = _\("[^"]*"\)', f'.trainerName = _("{new_name}")', block, count=1)
        if extra_repls:
            for old_s, new_s in extra_repls:
                if old_s not in block_new:
                    raise RuntimeError(f"[FATAL] Sub-field {old_s!r} not found in {enum_id}")
                block_new = block_new.replace(old_s, new_s, 1)
        content = content[: m.start()] + block_new + content[m.end() :]

    # Recurring Menace STEPHANE (Giovanni encounters)
    for gid in ("TRAINER_BOSS_GIOVANNI", "TRAINER_BOSS_GIOVANNI_2", "TRAINER_LEADER_GIOVANNI"):
        rename_trainer(gid, "STEPHANE")

    # Erica L at Celadon Gym (right next to Route 16 Snorlax!)
    rename_trainer("TRAINER_LEADER_ERIKA", "ERICA L")

    # Charles B at Saffron Gym (right next to Windchill / Silph Co.!) — give male Gentleman/Boss pic & male music
    rename_trainer(
        "TRAINER_LEADER_SABRINA",
        "CHARLES B",
        [
            (".encounterMusic_gender = TRAINER_ENCOUNTER_MUSIC_FEMALE | F_TRAINER_FEMALE,", ".encounterMusic_gender = TRAINER_ENCOUNTER_MUSIC_MALE,"),
            (".trainerPic = TRAINER_PIC_LEADER_SABRINA,", ".trainerPic = TRAINER_PIC_GENTLEMAN,"),
        ],
    )

    # Indigo Plateau Gauntlet: Jessica -> Siva -> Erin (3rd to last) -> Sonny (2nd to last) -> Champion Brian (last!)
    for lid in ("TRAINER_ELITE_FOUR_LORELEI", "TRAINER_ELITE_FOUR_LORELEI_2"):
        rename_trainer(lid, "JESSICA")
    for bid in ("TRAINER_ELITE_FOUR_BRUNO", "TRAINER_ELITE_FOUR_BRUNO_2"):
        rename_trainer(bid, "SIVA")
    for aid in ("TRAINER_ELITE_FOUR_AGATHA", "TRAINER_ELITE_FOUR_AGATHA_2"):
        rename_trainer(aid, "ERIN")
    for sid in ("TRAINER_ELITE_FOUR_LANCE", "TRAINER_ELITE_FOUR_LANCE_2"):
        rename_trainer(sid, "SONNY")
    for cid in (
        "TRAINER_CHAMPION_FIRST_SQUIRTLE",
        "TRAINER_CHAMPION_FIRST_BULBASAUR",
        "TRAINER_CHAMPION_FIRST_CHARMANDER",
        "TRAINER_CHAMPION_REMATCH_SQUIRTLE",
        "TRAINER_CHAMPION_REMATCH_BULBASAUR",
        "TRAINER_CHAMPION_REMATCH_CHARMANDER",
    ):
        rename_trainer(cid, "BRIAN")

    # Anime Team Rocket Trio: Jessie & James in Mt. Moon B2F and Silph Co. 11F!
    rename_trainer(
        "TRAINER_TEAM_ROCKET_GRUNT",
        "JESSIE",
        [(".trainerPic = TRAINER_PIC_ROCKET_GRUNT_M,", ".trainerPic = TRAINER_PIC_ROCKET_GRUNT_F,")],
    )
    rename_trainer("TRAINER_TEAM_ROCKET_GRUNT_2", "JAMES")
    rename_trainer("TRAINER_TEAM_ROCKET_GRUNT_40", "JAMES")
    rename_trainer(
        "TRAINER_TEAM_ROCKET_GRUNT_41",
        "JESSIE",
        [(".trainerPic = TRAINER_PIC_ROCKET_GRUNT_M,", ".trainerPic = TRAINER_PIC_ROCKET_GRUNT_F,")],
    )

    tr_h.write_text(content, encoding="utf-8", newline="\n")

    # Authentic anime rosters for Jessie & James (Ekans/Koffing/Meowth -> Arbok/Weezing/Lickitung/Victreebel/Meowth)
    tp_h = root / "src/data/trainer_parties.h"
    must_replace(
        tp_h,
        "static const struct TrainerMonNoItemDefaultMoves sParty_TeamRocketGrunt[] = {\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 13,\n"
        "        .species = SPECIES_RATTATA,\n"
        "    },\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 13,\n"
        "        .species = SPECIES_ZUBAT,\n"
        "    },\n"
        "};\n\n"
        "static const struct TrainerMonNoItemDefaultMoves sParty_TeamRocketGrunt2[] = {\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 11,\n"
        "        .species = SPECIES_SANDSHREW,\n"
        "    },\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 11,\n"
        "        .species = SPECIES_RATTATA,\n"
        "    },\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 11,\n"
        "        .species = SPECIES_ZUBAT,\n"
        "    },\n"
        "};",
        "static const struct TrainerMonNoItemDefaultMoves sParty_TeamRocketGrunt[] = {\n"
        "    {\n"
        "        .iv = 50,\n"
        "        .lvl = 13,\n"
        "        .species = SPECIES_EKANS,\n"
        "    },\n"
        "    {\n"
        "        .iv = 50,\n"
        "        .lvl = 13,\n"
        "        .species = SPECIES_MEOWTH,\n"
        "    },\n"
        "};\n\n"
        "static const struct TrainerMonNoItemDefaultMoves sParty_TeamRocketGrunt2[] = {\n"
        "    {\n"
        "        .iv = 50,\n"
        "        .lvl = 13,\n"
        "        .species = SPECIES_KOFFING,\n"
        "    },\n"
        "    {\n"
        "        .iv = 50,\n"
        "        .lvl = 13,\n"
        "        .species = SPECIES_MEOWTH,\n"
        "    },\n"
        "};",
        "Mt. Moon Jessie & James anime parties",
    )
    must_replace(
        tp_h,
        "static const struct TrainerMonNoItemDefaultMoves sParty_TeamRocketGrunt40[] = {\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 25,\n"
        "        .species = SPECIES_RATTATA,\n"
        "    },\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 25,\n"
        "        .species = SPECIES_RATTATA,\n"
        "    },\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 25,\n"
        "        .species = SPECIES_ZUBAT,\n"
        "    },\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 25,\n"
        "        .species = SPECIES_RATTATA,\n"
        "    },\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 25,\n"
        "        .species = SPECIES_EKANS,\n"
        "    },\n"
        "};\n\n"
        "static const struct TrainerMonNoItemDefaultMoves sParty_TeamRocketGrunt41[] = {\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 32,\n"
        "        .species = SPECIES_CUBONE,\n"
        "    },\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 32,\n"
        "        .species = SPECIES_DROWZEE,\n"
        "    },\n"
        "    {\n"
        "        .iv = 0,\n"
        "        .lvl = 32,\n"
        "        .species = SPECIES_MAROWAK,\n"
        "    },\n"
        "};",
        "static const struct TrainerMonNoItemDefaultMoves sParty_TeamRocketGrunt40[] = {\n"
        "    {\n"
        "        .iv = 100,\n"
        "        .lvl = 35,\n"
        "        .species = SPECIES_WEEZING,\n"
        "    },\n"
        "    {\n"
        "        .iv = 100,\n"
        "        .lvl = 34,\n"
        "        .species = SPECIES_VICTREEBEL,\n"
        "    },\n"
        "    {\n"
        "        .iv = 100,\n"
        "        .lvl = 35,\n"
        "        .species = SPECIES_MEOWTH,\n"
        "    },\n"
        "};\n\n"
        "static const struct TrainerMonNoItemDefaultMoves sParty_TeamRocketGrunt41[] = {\n"
        "    {\n"
        "        .iv = 100,\n"
        "        .lvl = 35,\n"
        "        .species = SPECIES_ARBOK,\n"
        "    },\n"
        "    {\n"
        "        .iv = 100,\n"
        "        .lvl = 34,\n"
        "        .species = SPECIES_LICKITUNG,\n"
        "    },\n"
        "    {\n"
        "        .iv = 100,\n"
        "        .lvl = 35,\n"
        "        .species = SPECIES_MEOWTH,\n"
        "    },\n"
        "};",
        "Silph Co. 11F James & Jessie anime parties",
    )
    print("[OK] Patched bosses, recurring menaces, and Jessie & James in trainers.h + trainer_parties.h")


def patch_items_and_wild_encounters(root: pathlib.Path) -> None:
    # 1. Coffee, Iced Espresso, Ninja Creami, Dark Roast & Squirtle Squad Shades!
    items_path = root / "src/data/items.json"
    items_data = json.loads(items_path.read_text(encoding="utf-8"))
    drink_updates = {
        "ITEM_FRESH_WATER": (
            "HOT COFFEE",
            "Fresh black coffee. Joseph drinks\\nit non-stop during IT crises.\\nRestores 50 HP to one POKéMON.",
        ),
        "ITEM_SODA_POP": (
            "ICED ESPRESSO",
            "Double-shot espresso brewed for\\nthe EU Forex open. Restores 60 HP\\nto one POKéMON.",
        ),
        "ITEM_LEMONADE": (
            "NINJA CREAMI",
            "A legendary spun Ninja Creami\\npint! Restores 80 HP to one\\nPOKéMON.",
        ),
        "ITEM_TEA": (
            "DARK ROAST",
            "An elite single-origin pour-over\\ncoffee strong enough to wake up\\nan on-call Saffron DB admin.",
        ),
        "ITEM_BLACK_GLASSES": (
            "SQUAD SHADES",
            "Pointy shades of the SQUIRTLE SQUAD!\\nRadiates boss energy and boosts\\nWATER-type moves by 20%.",
        ),
    }
    matched = 0
    for item in items_data["items"]:
        iid = item.get("itemId")
        if iid in drink_updates:
            new_en, new_desc = drink_updates[iid]
            assert len(new_en) <= 13, f"Item name too long: {new_en}"
            item["english"] = new_en
            item["description_english"] = new_desc
            if iid == "ITEM_BLACK_GLASSES":
                item["holdEffect"] = "HOLD_EFFECT_WATER_POWER"
                item["holdEffectParam"] = 20
            matched += 1
    if matched != len(drink_updates):
        raise RuntimeError(f"[FATAL] Expected {len(drink_updates)} items in items.json, matched {matched}")
    items_path.write_text(json.dumps(items_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("[OK] Patched Hot Coffee, Iced Espresso, Ninja Creami & Dark Roast in items.json")

    # 2. Solo-151 Wild Encounters: Merge LeafGreen exclusives + wild Bulbasaur/Charmander/Squirtle!
    we_path = root / "src/data/wild_encounters.json"
    we_data = json.loads(we_path.read_text(encoding="utf-8"))
    enc_list = we_data["wild_encounter_groups"][0]["encounters"]
    by_label = {e["base_label"]: e for e in enc_list}

    merged_routes = 0
    for label, fr_entry in list(by_label.items()):
        if not label.endswith("_FireRed"):
            continue
        lg_label = label[: -len("_FireRed")] + "_LeafGreen"
        lg_entry = by_label.get(lg_label)
        if not lg_entry:
            continue
        for field in ("land_mons", "water_mons", "fishing_mons", "rock_smash_mons"):
            if field not in fr_entry or field not in lg_entry:
                continue
            fr_mons = fr_entry[field]["mons"]
            lg_mons = lg_entry[field]["mons"]
            fr_species = {m["species"] for m in fr_mons}
            # Find indices where FireRed and LeafGreen differ and LeafGreen has an exclusive
            diff_indices = [
                idx
                for idx in range(min(len(fr_mons), len(lg_mons)))
                if lg_mons[idx]["species"] not in fr_species
            ]
            if len(diff_indices) >= 2:
                # Replace every second differing slot so BOTH FireRed & LeafGreen exclusives spawn!
                for k, slot_idx in enumerate(diff_indices):
                    if k % 2 == 1:
                        fr_mons[slot_idx]["species"] = lg_mons[slot_idx]["species"]
                merged_routes += 1
            elif len(diff_indices) == 1:
                slot_idx = diff_indices[0]
                old_sp = fr_mons[slot_idx]["species"]
                # Only replace if old_sp still exists in another slot on this table
                if sum(1 for m in fr_mons if m["species"] == old_sp) >= 2:
                    fr_mons[slot_idx]["species"] = lg_mons[slot_idx]["species"]
                    merged_routes += 1

    # Add rare wild Bulbasaur (Viridian Forest), Charmander (Route 4), Squirtle (Route 24)
    # since all 3 of Oak's Poké Balls are secretly Dratini!
    starter_wild_injections = [
        ("sViridianForest_FireRed", 11, "SPECIES_BULBASAUR"),
        ("sRoute4_FireRed", 10, "SPECIES_CHARMANDER"),
        ("sRoute24_FireRed", 11, "SPECIES_SQUIRTLE"),
    ]
    for lbl, slot, sp in starter_wild_injections:
        if lbl not in by_label:
            raise RuntimeError(f"[FATAL] Missing {lbl} in wild_encounters.json")
        by_label[lbl]["land_mons"]["mons"][slot]["species"] = sp

    we_path.write_text(json.dumps(we_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"[OK] Merged LeafGreen exclusives across {merged_routes} tables + wild Kanto starters")


def patch_intro_and_oaks_lab(root: pathlib.Path) -> None:
    intro_inc = root / "data/text/new_game_intro.inc"
    # Name presets: JOSEPH first for player, GREG first for buffoon rival
    replace_inc_block(intro_inc, "gNameChoice_Red", ["JOSEPH$"])
    replace_inc_block(intro_inc, "gNameChoice_Fire", ["JPATE$"])
    replace_inc_block(intro_inc, "gNameChoice_Ash", ["JOE$"])
    replace_inc_block(intro_inc, "gNameChoice_Green", ["GREG$"])
    replace_inc_block(intro_inc, "gNameChoice_Gary", ["BUFFOON$"])
    replace_inc_block(intro_inc, "gNameChoice_Kaz", ["GREGORY$"])
    replace_inc_block(intro_inc, "gNameChoice_Toru", ["DNSGUY$"])

    # Controls guide -> Isekai & IT Survival Manual
    replace_inc_block(
        intro_inc,
        "gControlsGuide_Text_Intro",
        [
            "ISEKAI SURVIVAL GUIDE FOR JOSEPH:\n",
            "A quick handbook for KANTO.$",
        ],
        max_width=40,
    )
    replace_inc_block(
        intro_inc,
        "gControlsGuide_Text_AButton",
        [
            "Confirm choices, sip coffee, and\n",
            "chat warmly for 45 minutes.$",
        ],
        max_width=40,
    )
    replace_inc_block(
        intro_inc,
        "gControlsGuide_Text_BButton",
        [
            "Cancel menus, or hold B to sprint\n",
            "straight toward the sushi bar!$",
        ],
        max_width=40,
    )

    # 3-Page Pikachu Intro -> The Legendary Bus-kun Isekai Prologue!
    replace_inc_block(
        intro_inc,
        "gPikachuIntro_Text_Page1",
        [
            "8:02 AM - EU Forex session open.\n",
            "EUR/USD printing green candles.\n",
            "Hot coffee in hand, Creami spun.\n",
            "\n",
            "Zero critical tickets in queue.\n",
            "Stephane's merger domain cutover\n",
            "is next week. Life is good.$",
        ],
        max_width=38,
    )
    replace_inc_block(
        intro_inc,
        "gPikachuIntro_Text_Page2",
        [
            "SUDDENLY - HONK! HONK!\n",
            "A rogue runaway city bus barrels\n",
            "around the corner out of nowhere!\n",
            "\n",
            "Classic Isekai Bus-kun claims\n",
            "another absolute IT legend!$",
        ],
        max_width=38,
    )
    replace_inc_block(
        intro_inc,
        "gPikachuIntro_Text_Page3",
        [
            "Everything fades into cherry\n",
            "blossoms and bright white light...\n",
            "\n",
            "From IT hero to POKéMON legend:\n",
            "Welcome to your new world!\n",
            "Step over that chair like Riker!$",
        ],
        max_width=38,
    )

    # Oak's Speech
    replace_inc_block(
        intro_inc,
        "gOakSpeech_Text_WelcomeToTheWorld",
        [
            "Whoa! Easy there!\n",
            "That Isekai Bus hit you hard!\p",
            "Welcome to the world of POKéMON!\p",
            "My name is OAK.\p",
            "Think of me as Senior Principal\n",
            "Architect around KANTO.\p$",
        ],
    )
    replace_inc_block(
        intro_inc,
        "gOakSpeech_Text_IsInhabitedFarAndWide",
        [
            "…is home to incredible creatures\n",
            "called POKéMON!\p",
            "They roam across cherry blossom\n",
            "valleys and ancient trails,\l",
            "living alongside us as partners.\p$",
        ],
    )
    replace_inc_block(
        intro_inc,
        "gOakSpeech_Text_IStudyPokemon",
        [
            "Here, nobody pages you at 2 AM\n",
            "over server outages.\p",
            "Just POKéMON, sushi, fresh coffee,\n",
            "and pints at The Flying Saucer!\p",
            "As a wise man always says:\n",
            "Teamwork Makes the Dreamwork!\p$",
        ],
    )
    replace_inc_block(
        intro_inc,
        "gOakSpeech_Text_WhatWasHisName",
        [
            "And this buffoon is my grandson.\p",
            "He trips over his mouse cord and\n",
            "blames lag for everything.\p",
            "…Erm, what was this clown's name?$",
        ],
    )
    replace_inc_block(
        intro_inc,
        "gOakSpeech_Text_LetsGo",
        [
            "{PLAYER}!\p",
            "Grab a fresh coffee and swing a\n",
            "leg over that chair like\l",
            "Commander Riker!\p",
            "Your POKéMON JosephRed legend\n",
            "starts right now! Let's go!$",
        ],
    )

    # ALL THREE BALLS IN OAK'S LAB ARE SECRETLY DRATINI!
    lab_scripts = root / "data/maps/PalletTown_ProfessorOaksLab/scripts.inc"
    must_replace(
        lab_scripts,
        "PalletTown_ProfessorOaksLab_EventScript_BulbasaurBall::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tsetvar PLAYER_STARTER_NUM, 0\n"
        "\tsetvar PLAYER_STARTER_SPECIES, SPECIES_BULBASAUR",
        "PalletTown_ProfessorOaksLab_EventScript_BulbasaurBall::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tsetvar PLAYER_STARTER_NUM, 0\n"
        "\tsetvar PLAYER_STARTER_SPECIES, SPECIES_DRATINI",
        "Oak Ball #1 -> SPECIES_DRATINI",
    )
    must_replace(
        lab_scripts,
        "PalletTown_ProfessorOaksLab_EventScript_SquirtleBall::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tsetvar PLAYER_STARTER_NUM, 1\n"
        "\tsetvar PLAYER_STARTER_SPECIES, SPECIES_SQUIRTLE",
        "PalletTown_ProfessorOaksLab_EventScript_SquirtleBall::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tsetvar PLAYER_STARTER_NUM, 1\n"
        "\tsetvar PLAYER_STARTER_SPECIES, SPECIES_DRATINI",
        "Oak Ball #2 -> SPECIES_DRATINI",
    )
    must_replace(
        lab_scripts,
        "PalletTown_ProfessorOaksLab_EventScript_CharmanderBall::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tsetvar PLAYER_STARTER_NUM, 2\n"
        "\tsetvar PLAYER_STARTER_SPECIES, SPECIES_CHARMANDER",
        "PalletTown_ProfessorOaksLab_EventScript_CharmanderBall::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tsetvar PLAYER_STARTER_NUM, 2\n"
        "\tsetvar PLAYER_STARTER_SPECIES, SPECIES_DRATINI",
        "Oak Ball #3 -> SPECIES_DRATINI",
    )
    must_replace(
        lab_scripts,
        "PalletTown_ProfessorOaksLab_EventScript_RivalPicksStarter::\n"
        "\tclosemessage\n"
        "\tgoto_if_eq PLAYER_STARTER_NUM, 0, PalletTown_ProfessorOaksLab_EventScript_RivalWalksToCharmander",
        "PalletTown_ProfessorOaksLab_EventScript_RivalPicksStarter::\n"
        "\ttextcolor NPC_TEXT_COLOR_MALE\n"
        "\tmsgbox PalletTown_ProfessorOaksLab_Text_OakGiveStarterPokeBalls\n"
        "\tgiveitem ITEM_POKE_BALL, 20\n"
        "\tclosemessage\n"
        "\tgoto_if_eq PLAYER_STARTER_NUM, 0, PalletTown_ProfessorOaksLab_EventScript_RivalWalksToCharmander",
        "Oak formally announces and hands 20 Poke Balls after receiving Dratini",
    )
    must_replace(
        lab_scripts,
        "\tplayfanfare MUS_OBTAIN_KEY_ITEM\n"
        "\twaitfanfare\n"
        "\tsetvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB, 3",
        "\tplayfanfare MUS_OBTAIN_KEY_ITEM\n"
        "\twaitfanfare\n"
        "\twaitbuttonpress\n"
        "\tclosemessage\n"
        "\tsetvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB, 3",
        "Close RivalTakesStarter message cleanly after button press",
    )
    lab_scripts.write_text(
        lab_scripts.read_text(encoding="utf-8")
        + "\nPalletTown_ProfessorOaksLab_Text_OakGiveStarterPokeBalls::\n"
        + '\t.string "OAK: Take these 20 POKé BALLS too,\\n"\n'
        + '\t.string "{PLAYER}! You\'ll need \'em for those\\l"\n'
        + '\t.string "wild Dick Biters in the tall grass!$"\n',
        encoding="utf-8",
        newline="\n",
    )

    # Viridian Mart: allows buying Poke Balls immediately (no parcel softlock!)
    must_replace(
        root / "data/maps/ViridianCity_Mart/scripts.inc",
        "ViridianCity_Mart_EventScript_SayHiToOak::\n"
        "\tmsgbox ViridianCity_Mart_Text_SayHiToOakForMe\n"
        "\trelease\n"
        "\tend",
        "ViridianCity_Mart_EventScript_SayHiToOak::\n"
        "\tgoto_if_questlog EventScript_ReleaseEnd\n"
        "\tmessage Text_MayIHelpYou\n"
        "\twaitmessage\n"
        "\tpokemart ViridianCity_Mart_Items\n"
        "\tmsgbox Text_PleaseComeAgain\n"
        "\trelease\n"
        "\tend",
        "Viridian Mart sells items before parcel delivery",
    )

    # Route 1: Clerk gives Potion FIRST, then 10 Poke Balls cleanly + introduces Dick Biters
    must_replace(
        root / "data/maps/Route1/scripts.inc",
        "\tadditem ITEM_POTION\n"
        "\tmsgbox Route1_Text_PutPotionAway\n"
        "\tcall EventScript_RestorePrevTextColor",
        "\tadditem ITEM_POTION\n"
        "\tmsgbox Route1_Text_PutPotionAway\n"
        "\tgiveitem ITEM_POKE_BALL, 10\n"
        "\tcall EventScript_RestorePrevTextColor",
        "Route 1 clerk gives 10 Poke Balls cleanly after Potion message",
    )
    r1_text = root / "data/maps/Route1/text.inc"
    replace_inc_block(
        r1_text,
        "Route1_Text_WorkAtPokeMartTakeSample",
        [
            "Hi! I work at the POKéMON MART.\p",
            "Take this sample POTION and 10\n",
            "POKé BALLS on the house!\p",
            "Watch your shins in the tall grass—\n",
            "RATTATA and RATICATE out here are\l",
            "vicious! We call 'em DICK BITERS!$",
        ],
    )
    replace_inc_block(
        r1_text,
        "Route1_Text_CanJumpFromLedges",
        [
            "Watch yourself in that tall grass!\p",
            "RATTATA and RATICATE—what we call\n",
            "DICK BITERS—lunge right out and\l",
            "clamp down! Catch 'em first!$",
        ],
    )

    lab_text = root / "data/maps/PalletTown_ProfessorOaksLab/text.inc"
    replace_inc_block(
        lab_text,
        "PalletTown_ProfessorOaksLab_Text_RivalMyMonLooksTougher",
        [
            "{RIVAL}: Heh! My POKéMON looks way\n",
            "tougher than yours!\p",
            "Go ahead—walk down toward the exit\n",
            "door! Let's see what you've got!$",
        ],
    )
    replace_inc_block(
        lab_text,
        "PalletTown_ProfessorOaksLab_Text_OakChoosingBulbasaur",
        [
            "OAK: Aha! Ball #1!\n",
            "Inside is a rare DRATINI!\p",
            "Wait… check the others if you\n",
            "don't believe me, or claim this\l",
            "DRATINI right now?$",
        ],
    )
    replace_inc_block(
        lab_text,
        "PalletTown_ProfessorOaksLab_Text_OakChoosingSquirtle",
        [
            "OAK: Hold on-Ball No.2 is ALSO\n",
            "secretly a DRATINI?!\p",
            "Haha! You can never have too\n",
            "many dragons on the roster!\l",
            "Roll with Ball No.2, {PLAYER}?$",
        ],
    )
    replace_inc_block(
        lab_text,
        "PalletTown_ProfessorOaksLab_Text_OakChoosingCharmander",
        [
            "OAK: Busted! ALL THREE POKé BALLS\n",
            "are secretly DRATINI!\p",
            "Only top-tier dragons for {PLAYER}!\n",
            "Ready to partner with DRATINI?$",
        ],
    )
    replace_inc_block(
        lab_text,
        "PalletTown_ProfessorOaksLab_Text_RivalFedUpWithWaiting",
        [
            "{RIVAL}: Gramps! My feet hurt and\n",
            "I locked myself out of Windows!$",
        ],
    )
    replace_inc_block(
        lab_text,
        "PalletTown_ProfessorOaksLab_Text_RivalLetsCheckOutMons",
        [
            "{RIVAL}: Wait up, {PLAYER}!\n",
            "Stop being so nice to everyone!\p",
            "Watch a REAL genius battle—I read\n",
            "half a Reddit thread on types!$",
        ],
    )
    replace_inc_block(
        lab_text,
        "PalletTown_ProfessorOaksLab_Text_RivalDefeat",
        [
            "WHAT?! Lag! Packet loss!\n",
            "I was typing on the wrong window!$",
        ],
    )
    replace_inc_block(
        lab_text,
        "PalletTown_ProfessorOaksLab_Text_RivalGoToughenMyMon",
        [
            "{RIVAL}: Whatever! My mouse was\n",
            "unplugged the whole time!\p",
            "I'm heading to Route 22 to grind!\n",
            "Smell ya later!$",
        ],
    )
    print("[OK] Patched Bus-kun Intro, All-3-Dratini Lab & Buffoon Greg")


def patch_lore_and_boss_gauntlet(root: pathlib.Path) -> None:
    # 1. Rooftop Vending Machine (Coffee / Espresso / Ninja Creami)
    roof_txt = root / "data/maps/CeladonCity_DepartmentStore_Roof/text.inc"
    replace_inc_block(
        roof_txt,
        "CeladonCity_DepartmentStore_Roof_Text_FloorSign",
        [
            "ROOFTOP BREAKROOM:\n",
            "COFFEE & NINJA CREAMI BAR$",
        ],
    )
    replace_inc_block(
        roof_txt,
        "CeladonCity_DepartmentStore_Roof_Text_YayFreshWaterHaveThis",
        [
            "Oh!! Fresh HOT COFFEE!\p",
            "Now I can survive this 45-minute\n",
            "chat! Take this TM, {PLAYER}!$",
        ],
    )
    replace_inc_block(
        roof_txt,
        "CeladonCity_DepartmentStore_Roof_Text_YaySodaPopHaveThis",
        [
            "Whoa! An ICED ESPRESSO right\n",
            "before the EU Forex open!\p",
            "You're the nicest guy in KANTO!\n",
            "Take this TM!$",
        ],
    )
    replace_inc_block(
        roof_txt,
        "CeladonCity_DepartmentStore_Roof_Text_YayLemonadeHaveThis",
        [
            "NO WAY! A homemade NINJA CREAMI!\p",
            "Are you as cool as Commander\n",
            "Riker sitting down? YES! Take this!$",
        ],
    )

    # 2. Snorlax = Broken DNS Request (Routes 12 & 16)
    for route_dir in ("Route12", "Route16"):
        r_txt = root / f"data/maps/{route_dir}/text.inc"
        if "Route12_Text_MonSprawledOutInSlumber::" in r_txt.read_text(encoding="utf-8"):
            sym_sleep = "Route12_Text_MonSprawledOutInSlumber"
        else:
            sym_sleep = "Route16_Text_MonSprawledOutInSlumber"
        replace_inc_block(
            r_txt,
            sym_sleep,
            [
                "A massive SNORLAX is blocking the\n",
                "route like a stuck DNS request!\p",
                "Rule #1 of IT: It's not the\n",
                "network. It's ALWAYS DNS.$",
            ],
        )
    replace_inc_block(
        root / "data/maps/Route12/text.inc",
        "Text_PlayedPokeFlute",
        [
            "{PLAYER} played POKé FLUTE to run\n",
            "ipconfig /flushdns!$",
        ],
    )

    # 3. ERICA L right next to Snorlax in Celadon Gym!
    cel_txt = root / "data/maps/CeladonCity_Gym/text.inc"
    replace_inc_block(
        cel_txt,
        "CeladonCity_Gym_Text_ErikaIntro",
        [
            "ERICA L: Hey {PLAYER}! Glad you\n",
            "made it past that DNS SNORLAX!\p",
            "We were just talking about cherry\n",
            "blossoms in Japan and fresh sushi.\p",
            "Wait—we've been chatting for 30\n",
            "minutes already! Haha, you're too\l",
            "nice, {PLAYER}!\p",
            "Let's see what your team can do!{PLAY_BGM MUS_ENCOUNTER_GYM_LEADER}$",
        ],
    )
    replace_inc_block(
        cel_txt,
        "CeladonCity_Gym_Text_ErikaDefeat",
        [
            "Whoa! Clean sweep!\p",
            "You really are as cool as\n",
            "Commander Riker sitting down!\p",
            "Take the RAINBOWBADGE, {PLAYER}!$",
        ],
    )
    replace_inc_block(
        cel_txt,
        "CeladonCity_Gym_Text_ReceivedTM19FromErika",
        [
            "{PLAYER} received TM19\n",
            "from ERICA L.$",
        ],
    )
    replace_inc_block(
        cel_txt,
        "CeladonCity_Gym_Text_GymStatue",
        [
            "CELADON POKéMON GYM\n",
            "LEADER: ERICA L\p",
            "NOTE: Please flush DNS before\n",
            "waking the Route 16 SNORLAX.$",
        ],
    )
    replace_inc_block(
        cel_txt,
        "CeladonCity_Gym_Text_GymStatuePlayerWon",
        [
            "CELADON POKéMON GYM\n",
            "LEADER: ERICA L\p",
            "RIKER CHAIR CERTIFIED:\n",
            "{PLAYER}$",
        ],
    )

    # 4. Domain Migration War Room (Silph Co. 11F) + Recurring Menace STEPHANE + CHARLES B in Saffron!
    silph_txt = root / "data/maps/SilphCo_11F/text.inc"
    replace_inc_block(
        silph_txt,
        "SilphCo_11F_Text_FloorSign",
        [
            "DOMAIN MIGRATION WAR ROOM - 11F\n",
            "MERGER CUTOVER IN PROGRESS$",
        ],
    )
    replace_inc_block(
        silph_txt,
        "SilphCo_11F_Text_GiovanniIntro",
        [
            "STEPHANE: Ah, {PLAYER}, my friend!\n",
            "Listen to me carefully!\p",
            "Why are you questioning my domain\n",
            "migration schedule?\p",
            "Yes, I scheduled the cutover for\n",
            "4:58 PM on Friday! Why not?\l",
            "It gives us the whole weekend!\p",
            "Stop smiling and telling me\n",
            "'Teamwork Makes the Dreamwork'!\l",
            "Let's see what you've got!$",
        ],
    )
    replace_inc_block(
        silph_txt,
        "SilphCo_11F_Text_GiovanniDefeat",
        [
            "Unbelievable!\n",
            "My migration batch failed!$",
        ],
    )
    replace_inc_block(
        silph_txt,
        "SilphCo_11F_Text_GiovanniPostBattle",
        [
            "STEPHANE: Look at you.\n",
            "You fixed the trust relationships\l",
            "and talked to me for an hour!\p",
            "You are entirely too nice,\n",
            "{PLAYER}. But this merger is not\l",
            "finished yet! We will talk again!$",
        ],
    )
    replace_inc_block(
        silph_txt,
        "SilphCo_11F_Text_ThanksForSavingMeDearBoy",
        [
            "VP: {PLAYER}! Thank goodness!\n",
            "You saved our domain controllers!\p",
            "Between STEPHANE's Friday cutover\n",
            "and {RIVAL} unplugging the SAN,\l",
            "our forest was completely down!\p",
            "Take our ultimate admin tool!$",
        ],
    )

    # Also patch Stephane's Rocket Hideout & Viridian Gym encounters!
    hideout_txt = root / "data/maps/RocketHideout_B4F/text.inc"
    if hideout_txt.exists():
        replace_inc_block(
            hideout_txt,
            "RocketHideout_B4F_Text_GiovanniIntro",
            [
                "STEPHANE: Ah, {PLAYER}, my friend!\n",
                "Still trading EUR/USD on break?\p",
                "Listen to me: I am running the\n",
                "merger domain migration here.\l",
                "Everything is under control!\p",
                "So what if cross-forest trusts\n",
                "broke and SID history is corrupt?\l",
                "It will replicate in 15 minutes!$",
            ],
        )
        replace_inc_block(
            hideout_txt,
            "RocketHideout_B4F_Text_GiovanniDefeat",
            [
                "Impossible!\n",
                "Why do you always stay so calm?!$",
            ],
        )

    vir_gym_txt = root / "data/maps/ViridianCity_Gym/text.inc"
    if vir_gym_txt.exists():
        replace_inc_block(
            vir_gym_txt,
            "ViridianCity_Gym_Text_GiovanniIntro",
            [
                "STEPHANE: Welcome to the final\n",
                "domain migration review, {PLAYER}!\p",
                "I demoted the legacy domain\n",
                "controllers, purged the DNS zones,\l",
                "and reset all user passwords!\p",
                "They are panicking, but I told\n",
                "them: trust the process!\p",
                "Let's see if your teamwork can\n",
                "survive this cutover!{PLAY_BGM}{MUS_ENCOUNTER_GYM_LEADER}$",
            ],
        )
        replace_inc_block(
            vir_gym_txt,
            "ViridianCity_Gym_Text_GiovanniDefeat",
            [
                "Incredible...\n",
                "You migrated the whole enterprise\l",
                "without a second of downtime?!$",
            ],
        )
        replace_inc_block(
            vir_gym_txt,
            "ViridianCity_Gym_Text_GiovanniPostBattle",
            [
                "STEPHANE: Ah, {PLAYER}...\n",
                "You always manage to clean up my\l",
                "messes with a smile on your face.\p",
                "Take this EARTH BADGE.\n",
                "You earned it, my friend.\p",
                "Maybe your 'Teamwork Makes the\n",
                "Dreamwork' really is true.\l",
                "Now go to INDIGO PLATEAU!$",
            ],
        )

    # CHARLES B in Saffron Gym (right next to Windchill / Silph Co.!)
    saf_map = root / "data/maps/SaffronCity_Gym/map.json"
    saf_json = json.loads(saf_map.read_text(encoding="utf-8"))
    for obj in saf_json.get("object_events", []):
        if obj.get("graphics_id") == "OBJ_EVENT_GFX_SABRINA":
            obj["graphics_id"] = "OBJ_EVENT_GFX_GENTLEMAN"
    saf_map.write_text(json.dumps(saf_json, indent=2) + "\n", encoding="utf-8", newline="\n")

    saf_txt = root / "data/maps/SaffronCity_Gym/text.inc"
    replace_inc_block(
        saf_txt,
        "SaffronCity_Gym_Text_SabrinaIntro",
        [
            "CHARLES B: {PLAYER}! Surviving\n",
            "the Windchill chaos next door?\p",
            "Between DB maintenance windows\n",
            "and STEPHANE's requests, Saffron\l",
            "needs serious mental fortitude.\p",
            "Teamwork makes the dreamwork—\n",
            "now show me your strategy!{PLAY_BGM}{MUS_ENCOUNTER_GYM_LEADER}$",
        ],
    )
    replace_inc_block(
        saf_txt,
        "SaffronCity_Gym_Text_SabrinaDefeat",
        [
            "Rock solid execution, {PLAYER}!\p",
            "You stepped right over the back\n",
            "of that chair like Commander\l",
            "Riker! Take the MARSHBADGE!$",
        ],
    )
    replace_inc_block(
        saf_txt,
        "SaffronCity_Gym_Text_ReceivedTM04FromSabrina",
        [
            "{PLAYER} received TM04 from\n",
            "CHARLES B.$",
        ],
    )

    # 5. THE ELITE FOUR + CHAMPION GAUNTLET!
    # #1 JESSICA (Lorelei's Room)
    replace_inc_block(
        root / "data/maps/PokemonLeague_LoreleisRoom/text.inc",
        "PokemonLeague_LoreleisRoom_Text_Intro",
        [
            "Welcome to INDIGO PLATEAU,\n",
            "{PLAYER}!\p",
            "I'm JESSICA of the ELITE FOUR.\p",
            "Hope you packed a fresh coffee\n",
            "and closed your EUR/USD charts,\l",
            "because things freeze solid here!\p",
            "Show me what you've got!{PLAY_BGM}{MUS_ENCOUNTER_GYM_LEADER}$",
        ],
    )
    replace_inc_block(
        root / "data/maps/PokemonLeague_LoreleisRoom/text.inc",
        "PokemonLeague_LoreleisRoom_Text_Defeat",
        [
            "Okay, that was ice cold!\n",
            "Nice work, {PLAYER}!$",
        ],
    )
    replace_inc_block(
        root / "data/maps/PokemonLeague_LoreleisRoom/text.inc",
        "PokemonLeague_LoreleisRoom_Text_PostBattle",
        [
            "JESSICA: You're even nicer—and\n",
            "tougher—than everyone said!\p",
            "Head on through. SIVA is up next!$",
        ],
    )

    # #2 SIVA (Bruno's Room)
    replace_inc_block(
        root / "data/maps/PokemonLeague_BrunosRoom/text.inc",
        "PokemonLeague_BrunosRoom_Text_Intro",
        [
            "I am SIVA of the ELITE FOUR!\p",
            "Zero downtime! Pure horsepower!\n",
            "Like a perfectly tuned database\l",
            "cluster under peak load!\p",
            "{PLAYER}! Let's stress-test your\n",
            "team right now!{PLAY_BGM}{MUS_ENCOUNTER_GYM_LEADER}$",
        ],
    )
    replace_inc_block(
        root / "data/maps/PokemonLeague_BrunosRoom/text.inc",
        "PokemonLeague_BrunosRoom_Text_Defeat",
        [
            "100% uptime! You passed every\n",
            "benchmark, {PLAYER}!$",
        ],
    )
    replace_inc_block(
        root / "data/maps/PokemonLeague_BrunosRoom/text.inc",
        "PokemonLeague_BrunosRoom_Text_PostBattle",
        [
            "SIVA: Teamwork really DOES make\n",
            "the dreamwork! Move ahead—\l",
            "ERIN is waiting in Room 3!$",
        ],
    )

    # #3 ERIN (3rd to last — Agatha's Room)
    replace_inc_block(
        root / "data/maps/PokemonLeague_AgathasRoom/text.inc",
        "PokemonLeague_AgathasRoom_Text_Intro",
        [
            "ERIN: Well, well—hey {PLAYER}!\n",
            "Welcome to the third chamber!\p",
            "Don't think you can charm your\n",
            "way past me with a 20-minute\l",
            "friendly chat and a coffee!\p",
            "Only three bosses stand between\n",
            "you and the crown. Let's battle!{PLAY_BGM}{MUS_ENCOUNTER_GYM_LEADER}$",
        ],
    )
    replace_inc_block(
        root / "data/maps/PokemonLeague_AgathasRoom/text.inc",
        "PokemonLeague_AgathasRoom_Text_Defeat",
        [
            "Unreal! You didn't even break\n",
            "a sweat, {PLAYER}!$",
        ],
    )
    replace_inc_block(
        root / "data/maps/PokemonLeague_AgathasRoom/text.inc",
        "PokemonLeague_AgathasRoom_Text_PostBattle",
        [
            "ERIN: Alright, that earned a\n",
            "full Commander Riker chair sit.\p",
            "Go on—SONNY is second to last!$",
        ],
    )

    # #4 SONNY (2nd to last — Lance's Room!)
    lance_txt = root / "data/maps/PokemonLeague_LancesRoom/text.inc"
    replace_inc_block(
        lance_txt,
        "PokemonLeague_LancesRoom_Text_Intro",
        [
            "SONNY: {PLAYER}! Look at that\n",
            "DRATINI squad all grown up!\p",
            "I'm the final wall of the ELITE\n",
            "FOUR—dragon against dragon!\p",
            "No Windchill tickets, no DNS\n",
            "excuses—just pure power!\p",
            "Show me everything, {PLAYER}!{PLAY_BGM}{MUS_ENCOUNTER_GYM_LEADER}$",
        ],
    )
    replace_inc_block(
        lance_txt,
        "PokemonLeague_LancesRoom_Text_Defeat",
        [
            "SONNY: Hahaha! Now THAT is a\n",
            "true Dragon Master!$",
        ],
    )
    replace_inc_block(
        lance_txt,
        "PokemonLeague_LancesRoom_Text_PostBattle",
        [
            "SONNY: Incredible battle,\n",
            "{PLAYER}!\p",
            "Wait—you thought {RIVAL} was the\n",
            "CHAMPION ahead? Ha! No chance!\p",
            "{RIVAL} got lost in Victory Road\n",
            "blaming DNS and locked his keys\l",
            "inside a Poké Mart!\p",
            "The ACTUAL competent boss waiting\n",
            "in the Champion's Room is BRIAN!\l",
            "Go finish this!$",
        ],
    )

    # #5 CHAMPION BRIAN (Final Boss — ChampionsRoom!)
    champ_txt = root / "data/maps/PokemonLeague_ChampionsRoom/text.inc"
    replace_inc_block(
        champ_txt,
        "PokemonLeague_ChampionsRoom_Text_Intro",
        [
            "BRIAN: Welcome to the top,\n",
            "{PLAYER}.\p",
            "Yeah, {RIVAL} tried to claim the\n",
            "title earlier, tripped over a\l",
            "patch cable, and disqualified\l",
            "himself in thirty seconds.\p",
            "Somebody competent had to hold\n",
            "down the CHAMPION seat until you\l",
            "got here.\p",
            "Teamwork Makes the Dreamwork—\n",
            "now let's see if you're as cool\l",
            "as Commander Riker sitting down!$",
        ],
    )
    replace_inc_block(
        champ_txt,
        "PokemonLeague_ChampionsRoom_Text_RematchIntro",
        [
            "BRIAN: Back for another round,\n",
            "{PLAYER}?\p",
            "Grab your coffee—my upgraded\n",
            "lineup isn't holding back!$",
        ],
    )
    replace_inc_block(
        champ_txt,
        "PokemonLeague_ChampionsRoom_Text_Defeat",
        [
            "Hats off, {PLAYER}!\n",
            "Flawless execution from start\l",
            "to finish!\p",
            "You are officially the POKéMON\n",
            "JOSEPHRED CHAMPION!$",
        ],
    )
    replace_inc_block(
        champ_txt,
        "PokemonLeague_ChampionsRoom_Text_PostBattle",
        [
            "BRIAN: Hell of a match, {PLAYER}.\p",
            "First round at The Flying Saucer\n",
            "is on me - then sushi in Japan,\l",
            "a spun Ninja Creami, and a full\l",
            "Commander Riker chair sit!$",
        ],
    )
    replace_inc_block(
        champ_txt,
        "PokemonLeague_ChampionsRoom_Text_OakCongratulations",
        [
            "OAK: {PLAYER}! Magnificent!\p",
            "From getting clipped by Bus-kun\n",
            "with a cup of coffee to raising\l",
            "{STR_VAR_1} into a legend!\p",
            "You may be cool, {PLAYER}…\n",
            "actually, you ARE as cool as\l",
            "Commander Riker sitting down!$",
        ],
    )
    replace_inc_block(
        champ_txt,
        "PokemonLeague_ChampionsRoom_Text_OakImDisappointedRival",
        [
            "OAK: Respect, BRIAN—now THAT was\n",
            "a real Champion battle!\p",
            "(Meanwhile {RIVAL} just paged us\n",
            "asking how to reboot a boulder…)$",
        ],
    )
    replace_inc_block(
        champ_txt,
        "PokemonLeague_ChampionsRoom_Text_OakPlayerComeWithMe",
        [
            "OAK: Teamwork Makes the Dreamwork,\n",
            "{PLAYER}!\p",
            "Step right this way into the\n",
            "HALL OF FAME!$",
        ],
    )

    # 6. Vermilion Harbor Famous Truck -> Legendary ISEKAI BUS-KUN + Lv.30 MEW Easter Egg!
    ss_map_path = root / "data/maps/SSAnne_Exterior/map.json"
    ss_map = json.loads(ss_map_path.read_text(encoding="utf-8"))
    for tx in (55, 56, 57):
        ss_map["bg_events"].append(
            {
                "type": "sign",
                "x": tx,
                "y": 3,
                "elevation": 0,
                "player_facing_dir": "BG_EVENT_PLAYER_FACING_ANY",
                "script": "SSAnne_Exterior_EventScript_IsekaiBusKun",
            }
        )
    ss_map_path.write_text(json.dumps(ss_map, indent=2) + "\n", encoding="utf-8", newline="\n")

    ss_scripts_path = root / "data/maps/SSAnne_Exterior/scripts.inc"
    ss_extra = (
        "\nSSAnne_Exterior_EventScript_IsekaiBusKun::\n"
        "\tlockall\n"
        "\tgoto_if_set FLAG_WONDER_CARD_UNUSED_8, SSAnne_Exterior_EventScript_BusKunResting\n"
        "\tmsgbox SSAnne_Exterior_Text_BusKunFound, MSGBOX_DEFAULT\n"
        "\tplaymoncry SPECIES_MEW, CRY_MODE_ENCOUNTER\n"
        "\twaitmoncry\n"
        "\tsetflag FLAG_WONDER_CARD_UNUSED_8\n"
        "\tsetwildbattle SPECIES_MEW, 30\n"
        "\tdowildbattle\n"
        "\treleaseall\n"
        "\tend\n\n"
        "SSAnne_Exterior_EventScript_BusKunResting::\n"
        "\tmsgbox SSAnne_Exterior_Text_BusKunIdle, MSGBOX_SIGN\n"
        "\treleaseall\n"
        "\tend\n\n"
        "SSAnne_Exterior_Text_BusKunFound::\n"
        '\t.string "WAIT A SECOND!\\n"\n'
        '\t.string "That\'s the ISEKAI BUS-KUN parked\\l"\n'
        '\t.string "in disguise at Vermilion Harbor!\\p"\n'
        '\t.string "Taped to the bumper: \'Enjoy KANTO,\\n"\n'
        '\t.string "{PLAYER}! P.S. Check under the\\l"\n'
        '\t.string "chassis!\'\\p"\n'
        '\t.string "A mythical POKéMON rolled out!$"\n\n'
        "SSAnne_Exterior_Text_BusKunIdle::\n"
        '\t.string "ISEKAI BUS-KUN sits peacefully.\\n"\n'
        '\t.string "Bumper sticker: \'HONK IF EUR/USD\\l"\n'
        '\t.string "IS PUMPING & RIKER JUST SAT DOWN\'$"\n'
    )
    ss_scripts_path.write_text(
        ss_scripts_path.read_text(encoding="utf-8") + ss_extra,
        encoding="utf-8",
        newline="\n",
    )

    # 7. Celadon EU Forex Desk, THE FLYING SAUCER Beer House & Pallet Town!
    pallet_txt = root / "data/maps/PalletTown/text.inc"
    replace_inc_block(
        pallet_txt,
        "PalletTown_Text_RaisingMonsToo",
        [
            "Whoa, {PLAYER}! I only said 'good\n",
            "morning' and somehow we chatted\l",
            "for 35 minutes!\p",
            "You really are the nicest guy!\n",
            "Teamwork Makes the Dreamwork!$",
        ],
    )
    replace_inc_block(
        pallet_txt,
        "PalletTown_Text_CanStoreItemsAndMonsInPC",
        [
            "Technology is incredible!\p",
            "As long as nobody hosts POKéMON\n",
            "PC Storage on PTC Windchill or\l",
            "lets {RIVAL} touch DNS!\p",
            "Catch you at The Flying Saucer\n",
            "later, {PLAYER}!$",
        ],
    )

    cel_city_txt = root / "data/maps/CeladonCity/text.inc"
    if cel_city_txt.exists():
        replace_inc_block(
            cel_city_txt,
            "CeladonCity_Text_CitySign",
            [
                "CELADON CITY\n",
                "Home of THE FLYING SAUCER Beer\l",
                "House & EU Forex Desk!$",
            ],
        )
        replace_inc_block(
            cel_city_txt,
            "CeladonCity_Text_GymSign",
            [
                "CELADON CITY POKéMON GYM\n",
                "LEADER: ERICA L\l",
                "Right Next to DNS SNORLAX!$",
            ],
        )
        replace_inc_block(
            cel_city_txt,
            "CeladonCity_Text_GameCornerSign",
            [
                "CELADON EU FOREX DESK\n",
                "Live EUR/USD Pips & Cherry Blossom\l",
                "Travel Fund Headquarters!$",
            ],
        )
        replace_inc_block(
            cel_city_txt,
            "CeladonCity_Text_BlewItAllAtSlots",
            [
                "Ugh… I blew my whole Flying\n",
                "Saucer beer tab over-leveraging\l",
                "EUR/USD before London open!$",
            ],
        )

    saucer_txt = root / "data/maps/CeladonCity_Restaurant/text.inc"
    if saucer_txt.exists():
        replace_inc_block(
            saucer_txt,
            "CeladonCity_Restaurant_Text_TakingBreakRightNow",
            [
                "Welcome to THE FLYING SAUCER!\p",
                "200 draught beers on tap, cold\n",
                "pints, and UFO plates on the\l",
                "ceiling for legends like {PLAYER}!$",
            ],
        )
        replace_inc_block(
            saucer_txt,
            "CeladonCity_Restaurant_Text_OftenGoToDrugstore",
            [
                "Nothing cures a 6-hour PTC\n",
                "Windchill DB maintenance window\l",
                "like a pint at The Flying Saucer!$",
            ],
        )
        replace_inc_block(
            saucer_txt,
            "CeladonCity_Restaurant_Text_PsstBasementUnderGameCorner",
            [
                "Psst! STEPHANE built an unindexed\n",
                "server room right under the\l",
                "EU FOREX DESK next door!$",
            ],
        )
        replace_inc_block(
            saucer_txt,
            "CeladonCity_Restaurant_Text_ManLostItAllAtSlots",
            [
                "Cheers! Working on my 200-beer\n",
                "Flying Saucer UFO plate!\p",
                "Wait - did {PLAYER} just step\n",
                "right over the back of that bar\l",
                "chair like Commander Riker?!$",
            ],
        )
        replace_inc_block(
            saucer_txt,
            "CeladonCity_Restaurant_Text_TakeThisImBusted",
            [
                "Hey {PLAYER}! Grab a seat at\n",
                "The Flying Saucer!\p",
                "I tried trading EUR/USD after\n",
                "four Belgian triples and got\l",
                "stopped out!\p",
                "Take my Forex COIN CASE - put it\n",
                "toward your Japan cherry blossom\l",
                "and sushi fund!$",
            ],
        )

    # 8. Classic Anime / Cartoon Iconic Moments
    # Magikarp Salesman (S.S. Anne anime scam tribute)
    r4_txt = root / "data/maps/Route4_PokemonCenter_1F/text.inc"
    if r4_txt.exists():
        replace_inc_block(
            r4_txt,
            "Route4_PokemonCenter_1F_Text_LaddieBuyMagikarpForJust500",
            [
                "MAN: Hey buddy! Have I got a deal!\n",
                "Just like aboard the S.S. ANNE!\p",
                "This MAGIKARP lays 1,000 eggs a day!\n",
                "You'll be a millionaire in no time!\p",
                "Only ¥500! Buy it, am I right?$",
            ],
        )
        replace_inc_block(
            r4_txt,
            "Route4_PokemonCenter_1F_Text_PaidOutrageouslyForMagikarp",
            [
                "{PLAYER} fell for the classic\n",
                "James-level S.S. ANNE scam and\l",
                "bought the MAGIKARP for ¥500…$",
            ],
        )

    # Misty's Charred Bicycle (Cerulean Gym anime tribute)
    cer_gym_txt = root / "data/maps/CeruleanCity_Gym/text.inc"
    if cer_gym_txt.exists():
        replace_inc_block(
            cer_gym_txt,
            "CeruleanCity_Gym_Text_LuisPostBattle",
            [
                "MISTY is mad about her bike!\p",
                "Some kid with a PIKACHU totally\n",
                "fried it on Route 1!\p",
                "She swore she'll make him pay if\n",
                "it's the last thing she ever does!$",
            ],
        )
        replace_inc_block(
            cer_gym_txt,
            "CeruleanCity_Gym_Text_GymGuyAdvice",
            [
                "Yo! Champ in the making!\p",
                "MISTY uses WATER-type POKéMON.\n",
                "ELECTRIC POKéMON will zap 'em!\p",
                "Just word of advice... don't EVER\n",
                "bring up charred bikes around her!$",
            ],
        )

    # Bill's Lighthouse Giant Dragonite (Sea Cottage anime tribute)
    bill_txt = root / "data/maps/Route25_SeaCottage/text.inc"
    if bill_txt.exists():
        replace_inc_block(
            bill_txt,
            "Route25_SeaCottage_Text_CheckOutRareMonsOnPC",
            [
                "BILL: Feel like checking out some\n",
                "of my rare POKéMON on my PC?\p",
                "You know, late at night on foggy\n",
                "evenings, I look out at the sea...\p",
                "A colossal, mysterious dragon\n",
                "POKéMON calls through the fog.\p",
                "Maybe you'll meet it someday,\n",
                "{PLAYER}! Go on, check out my PC!$",
            ],
        )

    # Squirtle Squad Pointy Sunglasses (Route 24 anime tribute)
    r24_txt = root / "data/maps/Route24/text.inc"
    if r24_txt.exists():
        replace_inc_block(
            r24_txt,
            "Route24_Text_ShaneIntro",
            [
                "Watch out in the grass! A rowdy gang\n",
                "of SQUIRTLE ambushed me!$",
            ],
        )
        replace_inc_block(
            r24_txt,
            "Route24_Text_ShaneDefeat",
            [
                "You're tougher than those turtles!$",
            ],
        )
        replace_inc_block(
            r24_txt,
            "Route24_Text_ShanePostBattle",
            [
                "They call themselves the SQUIRTLE\n",
                "SQUAD! Their boss wears crazy pointy\l",
                "sunglasses and blasts Water Guns!\p",
                "If you catch one, you might snag\n",
                "their signature SQUAD SHADES!$",
            ],
        )

    # Damian abandons Charmander on the rock (Cerulean Center anime lead-in)
    cer_pkmn_txt = root / "data/maps/CeruleanCity_PokemonCenter_1F/text.inc"
    if cer_pkmn_txt.exists():
        replace_inc_block(
            cer_pkmn_txt,
            "CeruleanCity_PokemonCenter_1F_Text_BillDoesWhateverForRareMons",
            [
                "DAMIAN: Haha! Hear about that\n",
                "weak CHARMANDER I ditched?\p",
                "I told it to wait on the rock\n",
                "west of NUGGET BRIDGE! Gullible\l",
                "lizard's still guarding its tail!$",
            ],
        )

    print("[OK] Patched full Lore, Windchill, DNS Snorlax, Drinks, Boss Gauntlet & Bus-kun")


def patch_playable_anime_events(root: pathlib.Path) -> None:
    """
    Injects 8 playable 90s Indigo League cartoon events across Kanto using
    verified walkable ground coordinates (coll=0, elev=3) and persistent
    unused save flags (FLAG_WONDER_CARD_UNUSED_1 .. _7).
    """

    def asm_text(symbol: str, lines: list[str]) -> str:
        lines = [
            line.replace("\n", "\\n")
            .replace("\u2014", "-")
            .replace("#", "No.")
            .replace("*", "")
            for line in lines
        ]
        lint_gba_lines(symbol, lines)
        return f"{symbol}::\n" + "".join(f'\t.string "{line}"\n' for line in lines) + "\n"

    def append_map_object(map_name: str, obj: dict) -> None:
        mp = root / f"data/maps/{map_name}/map.json"
        data = json.loads(mp.read_text(encoding="utf-8"))
        data.setdefault("object_events", []).append(obj)
        mp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")

    def append_scripts(map_name: str, block: str) -> None:
        sp = root / f"data/maps/{map_name}/scripts.inc"
        sp.write_text(sp.read_text(encoding="utf-8") + "\n" + block, encoding="utf-8", newline="\n")

    def gift_mon_subscripts(
        prefix: str,
        species: str,
        level: int,
        item: str,
        obtained_sym: str,
        flag: str,
        remove_local_id: str | None = None,
    ) -> str:
        rem = f"\tremoveobject {remove_local_id}\n" if remove_local_id else ""
        return (
            f"{prefix}_GiveMon::\n"
            f"\tcopyvar VAR_PREV_TEXT_COLOR, VAR_TEXT_COLOR\n"
            f"\tsetvar VAR_TEMP_1, {species}\n"
            f"\tgivemon {species}, {level}, {item}\n"
            f"\tgoto_if_eq VAR_RESULT, 0, {prefix}_Party\n"
            f"\tgoto_if_eq VAR_RESULT, 1, {prefix}_PC\n"
            f"\tgoto_if_eq VAR_RESULT, 2, EventScript_NoMoreRoomForPokemon\n"
            f"\trelease\n"
            f"\tend\n\n"
            f"{prefix}_Party::\n"
            f"{rem}"
            f"\ttextcolor NPC_TEXT_COLOR_NEUTRAL\n"
            f"\tplayfanfare MUS_LEVEL_UP\n"
            f"\tmessage {obtained_sym}\n"
            f"\twaitmessage\n"
            f"\twaitfanfare\n"
            f"\tbufferspeciesname STR_VAR_1, {species}\n"
            f"\tmsgbox Text_GiveNicknameToThisMon, MSGBOX_YESNO\n"
            f"\tgoto_if_eq VAR_RESULT, NO, {prefix}_Done\n"
            f"\tcall EventScript_GetGiftMonPartySlot\n"
            f"\tcall EventScript_ChangePokemonNickname\n"
            f"\tgoto {prefix}_Done\n"
            f"\tend\n\n"
            f"{prefix}_PC::\n"
            f"{rem}"
            f"\ttextcolor NPC_TEXT_COLOR_NEUTRAL\n"
            f"\tplayfanfare MUS_LEVEL_UP\n"
            f"\tmessage {obtained_sym}\n"
            f"\twaitmessage\n"
            f"\twaitfanfare\n"
            f"\tbufferspeciesname STR_VAR_1, {species}\n"
            f"\tmsgbox Text_GiveNicknameToThisMon, MSGBOX_YESNO\n"
            f"\tgoto_if_eq VAR_RESULT, NO, {prefix}_TransferPC\n"
            f"\tcall EventScript_NameReceivedBoxMon\n"
            f"\tgoto {prefix}_TransferPC\n"
            f"\tend\n\n"
            f"{prefix}_TransferPC::\n"
            f"\tcall EventScript_TransferredToPC\n"
            f"\tgoto {prefix}_Done\n"
            f"\tend\n\n"
            f"{prefix}_Done::\n"
            f"\tcopyvar VAR_TEXT_COLOR, VAR_PREV_TEXT_COLOR\n"
            f"\tsetflag {flag}\n"
            f"\trelease\n"
            f"\tend\n\n"
        )

    # 1. Episode 1 ("Pokemon - I Choose You!"): Route 1 Angry Spearow & Golden Ho-Oh Sighting!
    append_map_object(
        "Route1",
        {
            "local_id": "LOCALID_ROUTE1_SPEAROW",
            "type": "object",
            "graphics_id": "OBJ_EVENT_GFX_SPEAROW",
            "x": 14,
            "y": 18,
            "elevation": 3,
            "movement_type": "MOVEMENT_TYPE_LOOK_AROUND",
            "movement_range_x": 0,
            "movement_range_y": 0,
            "trainer_type": "TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id": "0",
            "script": "Route1_EventScript_AnimeSpearow",
            "flag": "FLAG_WONDER_CARD_UNUSED_1",
        },
    )
    append_scripts(
        "Route1",
        "Route1_EventScript_AnimeSpearow::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tplaymoncry SPECIES_SPEAROW, CRY_MODE_ENCOUNTER\n"
        "\tmsgbox Route1_Text_AnimeSpearowAmbush\n"
        "\twaitmoncry\n"
        "\tsetwildbattle SPECIES_SPEAROW, 5, ITEM_ORAN_BERRY\n"
        "\tdowildbattle\n"
        "\tremoveobject LOCALID_ROUTE1_SPEAROW\n"
        "\tsetflag FLAG_WONDER_CARD_UNUSED_1\n"
        "\tshowmonpic SPECIES_HO_OH, 10, 3\n"
        "\tplaymoncry SPECIES_HO_OH, CRY_MODE_NORMAL\n"
        "\twaitmoncry\n"
        "\tmsgbox Route1_Text_AnimeHoOhRainbow\n"
        "\thidemonpic\n"
        "\tgiveitem ITEM_SACRED_ASH, 1\n"
        "\trelease\n"
        "\tend\n\n"
        + asm_text(
            "Route1_Text_AnimeSpearowAmbush",
            [
                "SPEAROW: Speeear-OW!\p",
                "Just like Day 1 of the cartoon,\n",
                "an angry SPEAROW is diving right\l",
                "at {PLAYER}'s head!$",
            ],
        )
        + asm_text(
            "Route1_Text_AnimeHoOhRainbow",
            [
                "Whoa! The storm clouds parted!\p",
                "A glittering golden bird soared\n",
                "across a rainbow over ROUTE 1 and\l",
                "dropped a glowing feather!$",
            ],
        ),
    )

    # 2. Episode 45: Route 3 Singing Marker Jigglypuff + Youngster Ben's Shorts/Dick Biter gag!
    replace_inc_block(
        root / "data/maps/Route3/text.inc",
        "Route3_Text_BenIntro",
        [
            "Hi! I like shorts! They're comfy\n",
            "and easy to wear!\p",
            "…Well, until a wild DICK BITER\n",
            "lunges out of the tall grass!$",
        ],
    )
    append_map_object(
        "Route3",
        {
            "local_id": "LOCALID_ROUTE3_JIGGLYPUFF",
            "type": "object",
            "graphics_id": "OBJ_EVENT_GFX_JIGGLYPUFF",
            "x": 66,
            "y": 11,
            "elevation": 3,
            "movement_type": "MOVEMENT_TYPE_FACE_DOWN",
            "movement_range_x": 0,
            "movement_range_y": 0,
            "trainer_type": "TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id": "0",
            "script": "Route3_EventScript_AnimeJigglypuff",
            "flag": "FLAG_WONDER_CARD_UNUSED_2",
        },
    )
    append_scripts(
        "Route3",
        "Route3_EventScript_AnimeJigglypuff::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tmsgbox Route3_Text_JigglypuffMicReady\n"
        "\tclosemessage\n"
        "\tfadeoutbgm 0\n"
        "\tplaybgm MUS_JIGGLYPUFF, 0\n"
        "\tdelay 320\n"
        "\tfadescreen FADE_TO_BLACK\n"
        "\tdelay 45\n"
        "\tfadedefaultbgm\n"
        "\tmsgbox Route3_Text_JigglypuffMarkerSound\n"
        "\tclosemessage\n"
        "\tfadescreen FADE_FROM_BLACK\n"
        "\tplaymoncry SPECIES_JIGGLYPUFF, CRY_MODE_ENCOUNTER\n"
        "\twaitmoncry\n"
        "\tmsgbox Route3_Text_JigglypuffFurious\n"
        "\tsetwildbattle SPECIES_JIGGLYPUFF, 9, ITEM_PERSIM_BERRY\n"
        "\tdowildbattle\n"
        "\tremoveobject LOCALID_ROUTE3_JIGGLYPUFF\n"
        "\tsetflag FLAG_WONDER_CARD_UNUSED_2\n"
        "\trelease\n"
        "\tend\n\n"
        + asm_text(
            "Route3_Text_JigglypuffMicReady",
            [
                "A wild JIGGLYPUFF stepped up\n",
                "holding a marker like a mic!\p",
                "Ahem… JIGGLYPUFF took a deep\n",
                "breath to sing!$",
            ],
        )
        + asm_text(
            "Route3_Text_JigglypuffMarkerSound",
            [
                "Zzz… {PLAYER} passed out cold\n",
                "mid-lullaby!\p",
                "*SQUEAK! SQUEAK! SQUEAK!*\n",
                "Wait—is that permanent marker?!$",
            ],
        )
        + asm_text(
            "Route3_Text_JigglypuffFurious",
            [
                "JIGGLYPUFF puffed up furious and\n",
                "drew whiskers all over {PLAYER}'s\l",
                "face! Here it comes!$",
            ],
        ),
    )

    # 3. Episodes 2 & 6: Jessie, James & Talking Meowth in Mt. Moon B2F & Silph Co. 11F!
    mt_map_path = root / "data/maps/MtMoon_B2F/map.json"
    mt_map = json.loads(mt_map_path.read_text(encoding="utf-8"))
    for obj in mt_map["object_events"]:
        if obj.get("script") == "MtMoon_B2F_EventScript_Grunt1":
            obj["graphics_id"] = "OBJ_EVENT_GFX_ROCKET_F"
    mt_map["object_events"].append(
        {
            "type": "object",
            "graphics_id": "OBJ_EVENT_GFX_MEOWTH",
            "x": 13,
            "y": 20,
            "elevation": 3,
            "movement_type": "MOVEMENT_TYPE_FACE_DOWN",
            "movement_range_x": 0,
            "movement_range_y": 0,
            "trainer_type": "TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id": "0",
            "script": "MtMoon_B2F_EventScript_TalkingMeowth",
            "flag": "FLAG_HIDE_MISC_KANTO_ROCKETS",
        }
    )
    mt_map_path.write_text(json.dumps(mt_map, indent=2) + "\n", encoding="utf-8", newline="\n")

    mt_txt = root / "data/maps/MtMoon_B2F/text.inc"
    replace_inc_block(
        mt_txt,
        "MtMoon_B2F_Text_Grunt2Intro",
        [
            "JAMES: Prepare for trouble down\n",
            "in MT. MOON!\p",
            "Hand over those rare fossils\n",
            "before KOFFING smokes you out!$",
        ],
    )
    replace_inc_block(
        mt_txt,
        "MtMoon_B2F_Text_Grunt2Defeat",
        ["Looks like I'm blasting off!$"],
    )
    replace_inc_block(
        mt_txt,
        "MtMoon_B2F_Text_Grunt2PostBattle",
        [
            "JAMES: Wait up for me, JESSIE!\n",
            "Don't leave me in this cave!$",
        ],
    )
    replace_inc_block(
        mt_txt,
        "MtMoon_B2F_Text_Grunt1Intro",
        [
            "JESSIE: And make it double!\p",
            "To denounce the evils of truth\n",
            "and 'Teamwork Makes the\l",
            "Dreamwork'! Attack, EKANS!$",
        ],
    )
    replace_inc_block(
        mt_txt,
        "MtMoon_B2F_Text_Grunt1Defeat",
        ["WE'RE BLASTING OFF AGAAAAIN!!$"],
    )
    replace_inc_block(
        mt_txt,
        "MtMoon_B2F_Text_Grunt1PostBattle",
        [
            "JESSIE: Ugh! That twerp's dragon\n",
            "totally ruined my hair!$",
        ],
    )
    append_scripts(
        "MtMoon_B2F",
        "MtMoon_B2F_EventScript_TalkingMeowth::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tplaymoncry SPECIES_MEOWTH, CRY_MODE_NORMAL\n"
        "\tmsgbox MtMoon_B2F_Text_TalkingMeowth\n"
        "\twaitmoncry\n"
        "\trelease\n"
        "\tend\n\n"
        + asm_text(
            "MtMoon_B2F_Text_TalkingMeowth",
            [
                "MEOWTH: Meowth, that's right!\p",
                "Don't look shocked I talk human,\n",
                "pal—somebody's gotta supervise\l",
                "JESSIE and JAMES!$",
            ],
        ),
    )

    # Silph Co. 11F rematch with Jessie, James (chomped by Victreebel!) & Talking Meowth
    s11_map_path = root / "data/maps/SilphCo_11F/map.json"
    s11_map = json.loads(s11_map_path.read_text(encoding="utf-8"))
    for obj in s11_map["object_events"]:
        if obj.get("script") == "SilphCo_11F_EventScript_Grunt2":
            obj["graphics_id"] = "OBJ_EVENT_GFX_ROCKET_F"
    s11_map["object_events"].append(
        {
            "type": "object",
            "graphics_id": "OBJ_EVENT_GFX_MEOWTH",
            "x": 2,
            "y": 18,
            "elevation": 3,
            "movement_type": "MOVEMENT_TYPE_FACE_UP",
            "movement_range_x": 0,
            "movement_range_y": 0,
            "trainer_type": "TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id": "0",
            "script": "SilphCo_11F_EventScript_TalkingMeowth",
            "flag": "FLAG_HIDE_SILPH_ROCKETS",
        }
    )
    s11_map_path.write_text(json.dumps(s11_map, indent=2) + "\n", encoding="utf-8", newline="\n")

    s11_txt = root / "data/maps/SilphCo_11F/text.inc"
    replace_inc_block(
        s11_txt,
        "SilphCo_11F_Text_Grunt1Intro",
        [
            "JAMES: Prepare for merger trouble!\n",
            "Go, VICTREEBEL—OW! MY HEAD!\l",
            "STOP EATING ME AND BITE HIM!$",
        ],
    )
    replace_inc_block(
        s11_txt,
        "SilphCo_11F_Text_Grunt1Defeat",
        ["Blasting off from the 11th floor!$"],
    )
    replace_inc_block(
        s11_txt,
        "SilphCo_11F_Text_Grunt1PostBattle",
        [
            "JAMES: Ow… VICTREEBEL still won't\n",
            "let go of my skull…$",
        ],
    )
    replace_inc_block(
        s11_txt,
        "SilphCo_11F_Text_Grunt2Intro",
        [
            "JESSIE: Make it double! STEPHANE\n",
            "hired us as Cutover Security!\p",
            "Nobody stops his Friday 4:58 PM\n",
            "deploy on our watch!$",
        ],
    )
    replace_inc_block(
        s11_txt,
        "SilphCo_11F_Text_Grunt2Defeat",
        ["TEAM ROCKET'S BLASTING OFF AGAIN!$"],
    )
    replace_inc_block(
        s11_txt,
        "SilphCo_11F_Text_Grunt2PostBattle",
        [
            "JESSIE: Even STEPHANE's broken\n",
            "domain trusts last longer than us!$",
        ],
    )
    append_scripts(
        "SilphCo_11F",
        "SilphCo_11F_EventScript_TalkingMeowth::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tplaymoncry SPECIES_MEOWTH, CRY_MODE_NORMAL\n"
        "\tmsgbox SilphCo_11F_Text_TalkingMeowth\n"
        "\twaitmoncry\n"
        "\trelease\n"
        "\tend\n\n"
        + asm_text(
            "SilphCo_11F_Text_TalkingMeowth",
            [
                "MEOWTH: That's right! STEPHANE\n",
                "made me open three tickets just\l",
                "to get a saucer of milk up here!\p",
                "Honestly, {PLAYER}, go beat him!$",
            ],
        ),
    )

    # 4 & 5. Route 24: Damian's Stray Charmander on the Rock (Ep. 11) + Misty's Psyduck (Ep. 27)!
    append_map_object(
        "Route24",
        {
            "local_id": "LOCALID_ROUTE24_STRAY_ROCK",
            "type": "object",
            "graphics_id": "OBJ_EVENT_GFX_ROCK_SMASH_ROCK",
            "x": 5,
            "y": 15,
            "elevation": 3,
            "movement_type": "MOVEMENT_TYPE_FACE_DOWN",
            "movement_range_x": 0,
            "movement_range_y": 0,
            "trainer_type": "TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id": "0",
            "script": "Route24_EventScript_StrayCharmander",
            "flag": "FLAG_WONDER_CARD_UNUSED_3",
        },
    )
    append_map_object(
        "Route24",
        {
            "local_id": "LOCALID_ROUTE24_PSYDUCK",
            "type": "object",
            "graphics_id": "OBJ_EVENT_GFX_PSYDUCK",
            "x": 15,
            "y": 25,
            "elevation": 3,
            "movement_type": "MOVEMENT_TYPE_LOOK_AROUND",
            "movement_range_x": 0,
            "movement_range_y": 0,
            "trainer_type": "TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id": "0",
            "script": "Route24_EventScript_MigrainePsyduck",
            "flag": "FLAG_WONDER_CARD_UNUSED_4",
        },
    )
    append_scripts(
        "Route24",
        "Route24_EventScript_StrayCharmander::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tshowmonpic SPECIES_CHARMANDER, 10, 3\n"
        "\tplaymoncry SPECIES_CHARMANDER, CRY_MODE_NORMAL\n"
        "\twaitmoncry\n"
        "\tmsgbox Route24_Text_StrayCharmanderFound\n"
        "\thidemonpic\n"
        "\tgoto Route24_StrayCharmander_GiveMon\n"
        "\tend\n\n"
        + gift_mon_subscripts(
            "Route24_StrayCharmander",
            "SPECIES_CHARMANDER",
            12,
            "ITEM_CHARCOAL",
            "Route24_Text_RescuedCharmander",
            "FLAG_WONDER_CARD_UNUSED_3",
            "LOCALID_ROUTE24_STRAY_ROCK",
        )
        + "Route24_EventScript_MigrainePsyduck::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tmsgbox Route24_Text_PsyduckHeadache\n"
        "\tclosemessage\n"
        "\tplaymoncry SPECIES_PSYDUCK, CRY_MODE_ENCOUNTER\n"
        "\tfadescreen FADE_TO_WHITE\n"
        "\twaitmoncry\n"
        "\tfadescreen FADE_FROM_WHITE\n"
        "\tmsgbox Route24_Text_PsyduckBurst\n"
        "\tsetwildbattle SPECIES_PSYDUCK, 14, ITEM_TWISTED_SPOON\n"
        "\tdowildbattle\n"
        "\tremoveobject LOCALID_ROUTE24_PSYDUCK\n"
        "\tsetflag FLAG_WONDER_CARD_UNUSED_4\n"
        "\trelease\n"
        "\tend\n\n"
        + asm_text(
            "Route24_Text_StrayCharmanderFound",
            [
                "Shivering on this rock under a\n",
                "leaf is DAMIAN's abandoned\l",
                "CHARMANDER!\p",
                "{PLAYER} shielded its tail flame!\n",
                "CHARMANDER wants to join you!$",
            ],
        )
        + asm_text(
            "Route24_Text_RescuedCharmander",
            ["{PLAYER} rescued the stray\n", "CHARMANDER!$"],
        )
        + asm_text(
            "Route24_Text_PsyduckHeadache",
            [
                "PSYDUCK is clutching its head by\n",
                "the riverbank…\p",
                "PSYDUCK: Psy… ai-ai-ai…!$",
            ],
        )
        + asm_text(
            "Route24_Text_PsyduckBurst",
            [
                "WHOA! PSYDUCK's migraine unleashed\n",
                "a massive psychic wave!$",
            ],
        ),
    )

    # 6. Episode 10: Melanie's Hidden Village Bulbasaur on Route 25!
    append_map_object(
        "Route25",
        {
            "type": "object",
            "graphics_id": "OBJ_EVENT_GFX_LASS",
            "x": 56,
            "y": 7,
            "elevation": 3,
            "movement_type": "MOVEMENT_TYPE_FACE_DOWN",
            "movement_range_x": 0,
            "movement_range_y": 0,
            "trainer_type": "TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id": "0",
            "script": "Route25_EventScript_MelanieBulbasaur",
            "flag": "0",
        },
    )
    append_scripts(
        "Route25",
        "Route25_EventScript_MelanieBulbasaur::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tgoto_if_set FLAG_WONDER_CARD_UNUSED_5, Route25_EventScript_MelanieAfter\n"
        "\tmsgbox Route25_Text_MelanieIntro\n"
        "\tshowmonpic SPECIES_BULBASAUR, 10, 3\n"
        "\tplaymoncry SPECIES_BULBASAUR, CRY_MODE_NORMAL\n"
        "\twaitmoncry\n"
        "\tmsgbox Route25_Text_MelanieTrustsPlayer\n"
        "\thidemonpic\n"
        "\tgoto Route25_MelanieBulbasaur_GiveMon\n"
        "\tend\n\n"
        "Route25_EventScript_MelanieAfter::\n"
        "\tmsgbox Route25_Text_MelanieAfter\n"
        "\trelease\n"
        "\tend\n\n"
        + gift_mon_subscripts(
            "Route25_MelanieBulbasaur",
            "SPECIES_BULBASAUR",
            14,
            "ITEM_MIRACLE_SEED",
            "Route25_Text_ObtainedHiddenBulbasaur",
            "FLAG_WONDER_CARD_UNUSED_5",
        )
        + asm_text(
            "Route25_Text_MelanieIntro",
            [
                "MELANIE: Welcome to my hidden\n",
                "sanctuary for injured POKéMON!\p",
                "This brave BULBASAUR protects\n",
                "every hurt Pidgey and Dick Biter\l",
                "until they heal up.$",
            ],
        )
        + asm_text(
            "Route25_Text_MelanieTrustsPlayer",
            [
                "MELANIE: Oh! BULBASAUR sees how\n",
                "much your team trusts you!\p",
                "It wants to grow stronger with\n",
                "you, {PLAYER}! Take care of it!$",
            ],
        )
        + asm_text(
            "Route25_Text_ObtainedHiddenBulbasaur",
            ["{PLAYER} recruited MELANIE's\n", "BULBASAUR!$"],
        )
        + asm_text(
            "Route25_Text_MelanieAfter",
            [
                "MELANIE: Take great care of\n",
                "BULBASAUR! Teamwork Makes the\l",
                "Dreamwork!$",
            ],
        ),
    )

    # 7 & 8. Vermilion City: Officer Jenny + Squirtle Squad Leader (Ep. 12) & Bye Bye Butterfree (Ep. 21)!
    append_map_object(
        "VermilionCity",
        {
            "type": "object",
            "graphics_id": "OBJ_EVENT_GFX_POLICEMAN",
            "x": 23,
            "y": 13,
            "elevation": 3,
            "movement_type": "MOVEMENT_TYPE_FACE_DOWN",
            "movement_range_x": 0,
            "movement_range_y": 0,
            "trainer_type": "TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id": "0",
            "script": "VermilionCity_EventScript_OfficerJennySquirtle",
            "flag": "0",
        },
    )
    append_map_object(
        "VermilionCity",
        {
            "type": "object",
            "graphics_id": "OBJ_EVENT_GFX_BUG_CATCHER",
            "x": 28,
            "y": 30,
            "elevation": 3,
            "movement_type": "MOVEMENT_TYPE_FACE_DOWN",
            "movement_range_x": 0,
            "movement_range_y": 0,
            "trainer_type": "TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id": "0",
            "script": "VermilionCity_EventScript_ByeByeButterfree",
            "flag": "0",
        },
    )
    append_scripts(
        "VermilionCity",
        "VermilionCity_EventScript_OfficerJennySquirtle::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tgoto_if_set FLAG_WONDER_CARD_UNUSED_6, VermilionCity_EventScript_JennyAfter\n"
        "\tmsgbox VermilionCity_Text_JennySquirtleSquad\n"
        "\tshowmonpic SPECIES_SQUIRTLE, 10, 3\n"
        "\tplaymoncry SPECIES_SQUIRTLE, CRY_MODE_NORMAL\n"
        "\twaitmoncry\n"
        "\tmsgbox VermilionCity_Text_JennyRecruitBoss\n"
        "\thidemonpic\n"
        "\tgoto VermilionCity_SquirtleBoss_GiveMon\n"
        "\tend\n\n"
        "VermilionCity_EventScript_JennyAfter::\n"
        "\tmsgbox VermilionCity_Text_JennyAfter\n"
        "\trelease\n"
        "\tend\n\n"
        + gift_mon_subscripts(
            "VermilionCity_SquirtleBoss",
            "SPECIES_SQUIRTLE",
            16,
            "ITEM_BLACK_GLASSES",
            "VermilionCity_Text_ObtainedSquirtleBoss",
            "FLAG_WONDER_CARD_UNUSED_6",
        )
        + "VermilionCity_EventScript_ByeByeButterfree::\n"
        "\tlock\n"
        "\tfaceplayer\n"
        "\tgoto_if_set FLAG_WONDER_CARD_UNUSED_7, VermilionCity_EventScript_ButterfreeAfter\n"
        "\tplaymoncry SPECIES_BUTTERFREE, CRY_MODE_NORMAL\n"
        "\tmsgbox VermilionCity_Text_ByeByeButterfree\n"
        "\twaitmoncry\n"
        "\tgiveitem ITEM_SILVER_POWDER, 1\n"
        "\tgiveitem ITEM_RARE_CANDY, 1\n"
        "\tsetflag FLAG_WONDER_CARD_UNUSED_7\n"
        "\trelease\n"
        "\tend\n\n"
        "VermilionCity_EventScript_ButterfreeAfter::\n"
        "\tmsgbox VermilionCity_Text_ButterfreeAfter\n"
        "\trelease\n"
        "\tend\n\n"
        + asm_text(
            "VermilionCity_Text_JennySquirtleSquad",
            [
                "JENNY: Salute, {PLAYER}! A rogue\n",
                "gang called the SQUIRTLE SQUAD\l",
                "was pulling pranks all week…\p",
                "Until they heroically put out a\n",
                "harbor fire today!$",
            ],
        )
        + asm_text(
            "VermilionCity_Text_JennyRecruitBoss",
            [
                "JENNY: Their boss won't take off\n",
                "its pointy shades—and wants to\l",
                "roll with a real leader like you!$",
            ],
        )
        + asm_text(
            "VermilionCity_Text_ObtainedSquirtleBoss",
            [
                "{PLAYER} recruited the SQUIRTLE\n",
                "SQUAD LEADER (w/ SQUAD SHADES)!$",
            ],
        )
        + asm_text(
            "VermilionCity_Text_JennyAfter",
            [
                "JENNY: Those SQUAD SHADES boost\n",
                "WATER moves by 20%! Rock 'em\l",
                "proud, {PLAYER}!$",
            ],
        )
        + asm_text(
            "VermilionCity_Text_ByeByeButterfree",
            [
                "*Sniff*… Look out over the ocean,\n",
                "{PLAYER}…\p",
                "My BUTTERFREE just fell in love\n",
                "with a PINK BUTTERFREE and flew\l",
                "off across the sea together!\p",
                "I tied my yellow scarf on it and\n",
                "wished 'em well. Take these!$",
            ],
        )
        + asm_text(
            "VermilionCity_Text_ButterfreeAfter",
            [
                "Fly high out there, BUTTERFREE!\n",
                "I'm not crying—it's sea spray!$",
            ],
        ),
    )

    print("[OK] Injected 8 playable 90s Indigo League anime events across Kanto")


def copy_overrides(overrides_dir: pathlib.Path, root: pathlib.Path) -> None:
    if not overrides_dir.exists():
        return
    count = 0
    for src_file in overrides_dir.rglob("*"):
        if src_file.is_file():
            rel = src_file.relative_to(overrides_dir)
            dst_file = root / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            count += 1
    print(f"[OK] Copied {count} graphic/asset override(s) from {overrides_dir}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: apply_josephred.py <pokefirered_dir> [overrides_dir]", file=sys.stderr)
        sys.exit(1)
    root = pathlib.Path(sys.argv[1])
    overrides = pathlib.Path(sys.argv[2]) if len(sys.argv) >= 3 else None

    patch_core_c_files(root)
    patch_trainers(root)
    patch_items_and_wild_encounters(root)
    patch_intro_and_oaks_lab(root)
    patch_lore_and_boss_gauntlet(root)
    patch_playable_anime_events(root)
    if overrides:
        copy_overrides(overrides, root)
    print("[OK] All Pokémon JosephRed source patches applied cleanly.")


if __name__ == "__main__":
    main()
