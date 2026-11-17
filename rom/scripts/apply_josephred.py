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

    # 4. Running Shoes from Step 1 + Indoor Running
    must_replace(
        root / "src/new_game.c",
        "    RunScriptImmediately(EventScript_ResetAllMapFlags);\n"
        "    StringCopy(gSaveBlock1Ptr->rivalName, rivalName);",
        "    RunScriptImmediately(EventScript_ResetAllMapFlags);\n"
        "    FlagSet(FLAG_SYS_B_DASH);\n"
        "    StringCopy(gSaveBlock1Ptr->rivalName, rivalName);",
        "Enable Running Shoes from New Game start",
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

    tr_h.write_text(content, encoding="utf-8", newline="\n")
    print("[OK] Patched bosses & recurring menaces in src/data/trainers.h")


def patch_items_and_wild_encounters(root: pathlib.Path) -> None:
    # 1. Coffee, Iced Espresso, Ninja Creami & Pour-Over Coffee!
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
    }
    matched = 0
    for item in items_data["items"]:
        iid = item.get("itemId")
        if iid in drink_updates:
            new_en, new_desc = drink_updates[iid]
            assert len(new_en) <= 13, f"Item name too long: {new_en}"
            item["english"] = new_en
            item["description_english"] = new_desc
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
            "8:02 AM - EU Forex Session Open.\n",
            "EUR/USD is printing green candles.\n",
            "Hot coffee in your left hand, a\n",
            "spun Ninja Creami in your right.\n",
            "\n",
            "Zero critical tickets in queue,\n",
            "and Stephane's merger domain\l",
            "migration cutover is next week!\n",
            "Life is good.$",
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
            "another absolute legend before\n",
            "you can even close your EUR/USD\n",
            "position!$",
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
            "From IT hero to POKéMON legend.\n",
            "Welcome to your new world.\n",
            "\n",
            "Press the A Button, and step over\n",
            "that chair like Commander Riker!$",
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

    lab_text = root / "data/maps/PalletTown_ProfessorOaksLab/text.inc"
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
        "\tgoto_if_set FLAG_TEMP_A, SSAnne_Exterior_EventScript_BusKunResting\n"
        "\tmsgbox SSAnne_Exterior_Text_BusKunFound, MSGBOX_DEFAULT\n"
        "\tplaymoncry SPECIES_MEW, CRY_MODE_ENCOUNTER\n"
        "\twaitmoncry\n"
        "\tsetflag FLAG_TEMP_A\n"
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

    print("[OK] Patched full Lore, Windchill, DNS Snorlax, Drinks, Boss Gauntlet & Bus-kun")


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
    if overrides:
        copy_overrides(overrides, root)
    print("[OK] All Pokémon JosephRed source patches applied cleanly.")


if __name__ == "__main__":
    main()
