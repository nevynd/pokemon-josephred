# Pokémon JosephRed — Features

> Status legend: `Built (Pending Approval)` | `In Progress` | `Planned`  
> *(Nothing is marked Complete without explicit user verification and approval.)*

## ROM Customization (`josephred.gba`)
- **Custom Title Screen (`JOSEPHRED VERSION`):** `Built (Pending Approval)` — Metallic GBA chrome badge rendered onto FireRed's flame title screen.
- **Bus-kun Isekai Opening & Dratini Oak Speech:** `Built (Pending Approval)` — 3-page EU `EUR/USD` Forex + Coffee + Ninja Creami + Isekai Bus-kun prologue; Oak releases a Dratini and defaults player to `JOSEPH` & rival to `GREG`.
- **Joseph Custom Photo Intro & Trainer Card Sprite:** `Built (Pending Approval)` — Custom GBA pixel-art sprite of Joseph (stockier build, fluffy forward-and-up hair, charcoal Poké Ball graphic T-shirt with no lanyard, blue jeans, coffee cup, & Poké Ball) compiled into both Oak's Intro (`64×96` 31-color) and his in-game Trainer Card (`64×64` 16-color).
- **Full Player Avatar Replacement (Ash → Joseph):** `Built (Pending Approval)` — Replaced Ash across all game systems with Joseph: all 7 overworld movement sheets (walking, running, bike, surf, fish, item, VS Seeker) with dynamic per-frame head detection and zero cap visors, clean 5-frame mature battle back-sprite throwing animation (`joseph_battle_back_source.jpg` + 16-color palette), and 16×16 Town Map head icon.
- **All 3 Poké Balls Secretly Dratini & Clean Oak's Lab Cutscene:** `Built (Pending Approval)` — Inspecting Ball 1, 2, or 3 in Oak's Lab reveals all three are secretly Lv. 5 Dratini (learns *Twister* at Lv. 5, evolves into Dragonite at Lv. 48); Rival starter textbox closes cleanly after button press and Greg directs the player toward the exit door for the first Rival battle.
- **Poké Ball Availability & Combat Bag QoL:** `Built (Pending Approval)` — Opening Bag in battle defaults directly to the Poké Balls pocket (`OPEN_BAG_POKEBALLS`), 10 backup Poké Balls + 5 Potions included at New Game start, 20 Poké Balls formally announced and gifted by Oak after receiving Dratini, 10 bonus Poké Balls from the Route 1 clerk, and Viridian Mart inventory unlocked immediately.
- **Rattata & Raticate "Dick Biters" Classification & Lore:** `Built (Pending Approval)` — `RATTATA` and `RATICATE` keep their canonical species names while their Pokédex classification is set to **`DICK BITER`** (`DICK BITER POKéMON`), backed by custom Pokédex entries and Kanto NPC/trainer dialogue referring to them as *"Dick Biters"*.
- **Squirtle Squad Meme Shades & SQUAD SHADES Held Item:** `Built (Pending Approval)` — Crisp jet-black (`#101010`) pointed Squirtle Squad leader shades + white/silver reflection glint rendered onto **both** Squirtle's front and back battle sprites (`front.png` & `back.png`), `ITEM_BLACK_GLASSES` rebranded to `SQUAD SHADES` (+20% Water-type move power via `HOLD_EFFECT_WATER_POWER`), and held by wild Squirtle + the Vermilion Squirtle Squad Leader.
- **8 Playable 90s Indigo League Anime Events + Classic References:** `Built (Pending Approval)` —
  1. *Ep. 1 (`Route 1`)*: Angry Spearow ambush + golden **Ho-Oh** rainbow sky sighting & `SACRED ASH` feather drop.
  2. *Ep. 45 (`Route 3`)*: Singing Marker **Jigglypuff** (`MUS_JIGGLYPUFF` lullaby, sleep blackout, marker scribble, Lv. 9 wild battle) + Youngster Ben's shorts/Dick Biter gag.
  3. *Ep. 2 & 6 (`Mt. Moon B2F` & `Silph Co. 11F`)*: **Jessie**, **James**, & **Talking Meowth** with full motto, James's head-chomping Victreebel gag, and canonical anime parties.
  4. *Ep. 11 (`Route 24` & `Cerulean Center`)*: Damian bragging at the Poké Center + rescuable **Lv. 12 Stray Charmander** (`CHARCOAL`) on the rock west of Nugget Bridge.
  5. *Ep. 27 (`Route 24`)*: **Misty's Migraine Psyduck** psychic flash + Lv. 14 wild battle (`TWISTED SPOON`).
  6. *Ep. 10 (`Route 25`)*: **Melanie's Hidden Village** sanctuary gift — **Lv. 14 Bulbasaur** (`MIRACLE SEED`).
  7. *Ep. 12 (`Vermilion City`)*: **Officer Jenny** recruiting Joseph to lead the **Lv. 16 Squirtle Squad Leader** (`SQUAD SHADES`).
  8. *Ep. 21 (`Vermilion Pier`)*: ***"Bye Bye Butterfree"*** ocean farewell gifting `SILVER POWDER` + `RARE CANDY`, alongside S.S. Anne Magikarp salesman, Misty's charred bike, and Bill's giant Dragonite.
- **Buffoon Rival Greg vs. Competent Champion Brian:** `Built (Pending Approval)` — Greg stays the bumbling recurring rival throughout Kanto while `TRAINER_CLASS_CHAMPION` is decoupled in C source so **Brian** reigns as final Champion.
- **Custom Boss Lineup & Stephane Merger Lore:** `Built (Pending Approval)` — **Erica L** (Celadon / Snorlax sector), **Charles B** (Saffron / Windchill sector), **Stephane** (senior IT admin running merger domain migration with French-African cadence at Hideout, Windchill Silph Co., & Viridian), and Indigo Plateau Gauntlet: **Jessica → Siva → Erin (3rd to last) → Sonny (2nd to last) → Champion Brian (last)**.
- **Inside Jokes & World Flavor:** `Built (Pending Approval)` — *"Teamwork Makes the Dreamwork!"*, **The Flying Saucer** beer house (Celadon taproom, 200-beer UFO ceiling plates, Pallet Town & Champion Brian pints), **Commander Riker** chair-sit tributes, **PTC Windchill & DB Maintenance** Silph Co. takeover, **DNS Snorlax (`ipconfig /flushdns`)**, **Hot Coffee / Iced Espresso / Ninja Creami** rooftop bar, EU Forex Desk, sushi/Japan cherry blossoms, and **Vermilion Harbor Bus-kun Lv. 30 Mew** Easter egg.
- **Solo-151 & Modern QoL:** `Built (Pending Approval)` — Running Shoes from step 1 (indoors + outdoors), infinite reusable TMs, level-up trade evolutions, LeafGreen exclusives merged onto Kanto routes, and wild Bulbasaur/Charmander/Squirtle.
- **Help System Journal & Quest Log Suppression:** `Built (Pending Approval)` — Help System journal popup completely disabled in C source (`OPTIONS_BUTTON_MODE_LR`, `RunHelpSystemCallback` stub), preventing accidental interruptions during 4× play or shoulder button touch; Quest Log playback bypassed on resume.
- **Prologue Page Flow & Text Fit:** `Built (Pending Approval)` — Formatted 3-page prologue to 5–7 lines with native newlines so all text is immediately visible without clipping, allowing `A` button to cleanly turn pages.

## Mobile Web GBA SP Shell (`/web`)
- **JosephRed GBA SP Touch UI:** `Built (Pending Approval)` — Portrait & landscape responsive shell (`App.tsx`) with smooth thumb-slide D-Pad, A/B, L/R, Start/Select, haptics, and desktop keyboard controls (`E` to interact).
- **1× / 2× / 4× Fast-Forward & Hardware-Masked Auto-Run:** `Built (Pending Approval)` — Instant speed multiplier (`1× / 2× / 4×`) + one-tap `RUN` toggle asserting a hardware-masked `L+R` chord (`gAutoRunEnabled`) so Joseph sprints automatically (hold `B` to walk) without breaking `B` in menus or cancelling evolutions; React lifecycle isolated so toggling `RUN` never resets the emulator.
- **Persistent Auto-Save & Backup:** `Built (Pending Approval)` — Automatic IndexedDB SRAM sync on in-game save & tab hide, 3 quick save-state slots, `.sav` file Export/Import, and custom `.gba` loader.

## Production Hosting & Infrastructure (Railway)
- **Production Container Build & Healthcheck:** `Built (Pending Approval)` — Multi-stage Alpine container listening on Railway edge `0.0.0.0:8080` with COOP/COEP isolation and `/health` endpoint.
- **Continuous Deployment:** `Built (Pending Approval)` — Linked to `nevynd/pokemon-josephred@main` on Railway project `pokemon-josephred`.
- **Live Railway Service Domain:** `Built (Pending Approval)` — Verified live at `https://pokemon-josephred-production.up.railway.app`.
- **Custom Domain (`joseph.beenelson.com`):** `Built (Pending Approval)` — Attached to service on port 8080, awaiting user DNS CNAME & TXT records.

