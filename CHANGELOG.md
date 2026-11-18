# Changelog

## [0.1.0] - 2026-11-16
### Added
- **ROM Build Pipeline (`rom/docker`, `scripts/build-rom.ps1`):** Deterministic 2-stage Docker toolchain (`pret/agbcc` + `pret/pokefirered`) compiling `josephred.gba` in ~3s incrementally.
- **GBA Title Logo & Portrait Tooling (`rom/scripts/`):**
  - `render_title_badge.py` generating brushed-chrome `JOSEPHRED VERSION` subtitle art.
  - `convert_portrait.py` converting photos into 64×96 31-color GBA Oak Speech portraits (`BG_PLTT_ID(4)` indices `65..95`).
  - `apply_josephred.py` with automated GBA textbox line-width & charmap validation.
- **Pokémon JosephRed Core Mods & Lore:**
  - Bus-kun Isekai 3-page prologue + Dratini Oak intro + default `JOSEPH` / `GREG` names.
  - All 3 Oak's Lab Poké Balls secretly holding Lv. 5 Dratini (with Lv. 5 *Twister* & Lv. 48 Dragonite evolution).
  - Decoupled Champion C logic (`battle_message.c`, `quest_log_events.c`) for Champion **Brian**, plus **Sonny**, **Erin**, **Siva**, **Jessica**, **Erica L**, **Charles B**, and recurring menace **Stephane**.
  - Added **Hot Coffee**, **Iced Espresso**, **Ninja Creami**, **Dark Roast**, PTC Windchill HQ, DNS Snorlax (`ipconfig /flushdns`), EU `EUR/USD` Forex Desk, Commander Riker chair tributes, and Vermilion Harbor Bus-kun Lv. 30 Mew event.
  - Solo-151 QoL: Running Shoes from start + indoors, reusable TMs, level-up trade evolutions, LeafGreen exclusives, and wild Kanto starters.
- **Mobile Web GBA SP Player (`web/`):**
  - Built responsive **JosephRed SP** shell using `@thenick775/mgba-wasm` 2.6.0, React 19, TypeScript, and Vite.
  - Added thumb-slide D-Pad, haptic touch controls, `1× / 2× / 4×` Fast-Forward, `RUN` auto-sprint lock, automatic IndexedDB SRAM sync, 3 Quick Save State slots, `.sav` Export/Import, custom `.gba` loader, and production COOP/COEP Node server (`web/server.mjs`).
- **Custom Joseph Trainer Sprites (`rom/overrides/graphics/`):**
  - Updated to Sprite v3: stockier/chunkier build, fluffy forward-and-up hair, charcoal crew-neck Poké Ball graphic T-shirt (no lanyard), blue denim jeans, sneakers, coffee cup, & Poké Ball for both Oak's Intro platform (`oak_speech/red/pic.png` + `pal.pal`) and his in-game Trainer Card (`trainers/front_pics/red_front_pic.png` + `palettes/red.pal`).
- **The Flying Saucer Beer House Lore (`rom/scripts/apply_josephred.py`):**
  - Rebranded Celadon Restaurant (`COIN CASE` hub) into **The Flying Saucer** (200 draught beers, UFO plates on the ceiling, EUR/USD Forex tab jokes), plus added Flying Saucer references to Oak's intro speech, Pallet Town NPCs, Celadon City sign, and Champion Brian's post-battle celebration.
- **Railway Production Container & Healthcheck (`Dockerfile`, `web/server.mjs`):**
  - Added multi-stage Alpine `Dockerfile` at repo root, `/health` JSON healthcheck endpoint, `Content-Length` headers, and Git tracking for `web/public/roms/josephred.gba`.
- **Live Railway Deployment & Custom Domain (`joseph.beenelson.com`):**
  - Provisioned Railway project `pokemon-josephred` (`ffd68767-561b-430d-97c3-c69b095f27e8`) in workspace `nevynd's Projects`.
  - Connected public repository `nevynd/pokemon-josephred` (`main` branch) with automated CI/CD container builds.
  - Successfully built and deployed container to production (`https://pokemon-josephred-production.up.railway.app`) verified with `HTTP 200 OK` and active COOP/COEP headers.
  - Generated and bound custom domain `joseph.beenelson.com` targeting container port 8080.
- **Cache Busting & Cartridge Refresh Fix (`web/server.mjs`, `web/src/App.tsx`):**
  - Added dynamic timestamp query parameter (`?t=${Date.now()}`) and `{ cache: 'no-store' }` to ROM fetch in `App.tsx`.
  - Configured `web/server.mjs` to serve `.gba` cartridges and `index.html` with `Cache-Control: no-cache, no-store, must-revalidate`, `Pragma: no-cache`, and `Expires: 0`.
  - Replaced legacy `gNameChoice_Ash` with `JOE$` in `new_game_intro.inc` so the name "ASH" is eliminated from the new game selection menu.
- **Intro Dialogue Pacing & Lore Rebalance (`rom/scripts/apply_josephred.py`):**
  - Removed repetitive "PTC Windchill", "DNS", and "Teamwork Makes the Dreamwork" gags from the opening 2 minutes so they don't step on each other.
  - Controls Guide now features a clean Kanto handbook orientation and sprint-to-sushi tip.
  - Prologue Page 1 introduces foreboding of Stephane messaging during EU Forex session without burning Windchill or DNS.
  - Oak's Speech highlights roaming under cherry blossoms and cold pints at The Flying Saucer, introducing "Teamwork Makes the Dreamwork" exactly once with dignity as Joseph's motto.
  - Greg's intro establishes his buffoonery via tripping on mouse cords and crying lag, preserving the DNS joke specifically for the Route 12/16 Snorlax blocker and PTC Windchill for Silph Co. 11F HQ.
- **Stephane Senior IT Admin Persona & Merger Domain Migration Lore (`rom/scripts/apply_josephred.py`):**
  - Grounded Stephane's character in his true real-world enterprise role: the senior IT administrator running a high-stakes corporate merger domain migration across forests.
  - Stripped away stereotypical Parisian clichés (*sacré bleu*, *mon dieu*, etc.) in favor of authentic French-African senior admin cadence (*"Listen to me, my friend..."*, *"It will replicate in 15 minutes, why do you worry so much?"*, scheduling cutovers at 4:58 PM on Friday, breaking SID history, and cross-forest trusts).
  - Encounters at Rocket Hideout B4F, Silph Co. 11F, and Viridian Gym now chronicle the unfolding domain cutover chaos.
- **Player Character Graphics Replacement (Ash → Joseph) Across All GBA Formats (`rom/scripts/convert_all_player_sprites.py`):**
  - Fully replaced Ash/Red across all gameplay graphics with Joseph (dark fluffy hair, no cap, friendly face with goatee shadow, charcoal crewneck T-shirt with chest Poké Ball, blue jeans, and sneakers).
  - Overworld walking, running, biking, surfing, fishing, item-holding, and VS Seeker cycles: `red_normal.png`, `red_surf_run.png`, `red_bike.png`, `red_surf.png`, `red_fish.png`, `red_item.png`, `red_vs_seeker_bike.png`.
  - Battle back sprite (`red_back_pic.png` 64×320, 5 frames 64×64 throwing animation).
  - Town Map player head icon (`player_icon_red.png` 16×16).
  - Recompiled into 16 MB production ROM (`web/public/roms/josephred.gba`) in 2.9 seconds.
- **Prologue Layout Fit & Screen Hop Fix (`rom/scripts/apply_josephred.py`):**
  - Formatted all 3 Pikachu intro pages to strictly 5–7 lines with native `\n` linebreaks, eliminating mid-page `\l` scroll escapes.
  - The static 28×15 tile window now displays all lines at once with zero clipping, ensuring pressing `A` cleanly turns pages as designed.
- **Help System & Quest Log Journal Disablement (`src/new_game.c`, `src/help_system_util.c`, `src/quest_log.c`, `web/src/App.tsx`):**
  - Switched default button mode in `new_game.c` from `OPTIONS_BUTTON_MODE_HELP` to `OPTIONS_BUTTON_MODE_LR`.
  - Patched `RunHelpSystemCallback` in `src/help_system_util.c` to immediately return `0`, permanently blocking the Help System menu from intercepting gameplay during 4× fast-forward or shoulder button contact.
  - Patched `TryStartQuestLogPlayback` in `src/quest_log.c` to skip replay and resume game state immediately.
  - Remapped desktop keyboard interaction: mapped `KeyE` to GBA `A` (natural WASD interact key) and moved GBA `R` to `KeyR`.
- **Authentic Joseph Battle Back-Sprite & 16-Color Palette (`rom/overrides/graphics/trainers/back_pics/red_back_pic.png`, `red_back_pic.pal`, `rom/scripts/convert_battle_back.py`):**
  - Replaced the placeholder Ash recolor ("ash but bluish with crosshatching") with a custom 5-frame GBA battle animation sprite designed for Joseph.
  - Features Joseph's mature, stockier silhouette with broad shoulders, fluffy textured dark hair (no cap), clean goatee stubble visible in profile, solid charcoal crewneck T-shirt, and blue denim jeans.
  - 5-frame animation cycle: Frame 0 (Stance / Slide-in), Frame 1 (Wind-up), Frame 2 (High Cocked Stance), Frame 3 (Full Extension Throw), Frame 4 (Follow-through / Ready).
  - Created dedicated 16-color GBA palette `red_back_pic.pal` matching Joseph's front trainer card palette.
- **Auto-Run & Web Shell Lifecycle Isolation (`web/src/App.tsx`, `src/field_player_avatar.c`, `src/new_game.c`):**
  - Resolved emulator reboot bug when clicking `RUN`: decoupled `runLock` and `muted` state updates into mutable refs (`runLockRef`, `mutedRef`) and locked `boot()` `useEffect` dependencies strictly to `[]`.
  - Patched `field_player_avatar.c` to remove the `FlagGet(FLAG_SYS_B_DASH)` prerequisite on `heldKeys & B_BUTTON`, guaranteeing holding B sprints in overworld across all save files.
  - Updated `new_game.c` to set `FLAG_SYS_B_DASH` and grant 20 starting Poké Balls and 5 Potions at new game initialization.
- **Battle Bag Poké Ball Pocket & Inventory Availability (`src/item_menu.c`, `src/menu_helpers.c`, `PalletTown_ProfessorOaksLab/scripts.inc`, `ViridianCity_Mart/scripts.inc`, `Route1/scripts.inc`):**
  - Patched `CB2_BagMenuFromBattle` in `src/item_menu.c` to pass `OPEN_BAG_POKEBALLS` instead of `OPEN_BAG_LAST`, making the Bag menu open directly to Poké Balls when accessed during combat.
  - Patched `menu_helpers.c` so `GetLRKeysPressed` and `GetLRKeysPressedAndHeld` return L/R unconditionally, enabling seamless pocket switching regardless of option button mode.
  - Oak now grants 20 Poké Balls immediately with starter Dratini.
  - Route 1 Mart clerk gives 10 Poké Balls with the sample Potion.
  - Viridian City Mart unlocked so the clerk sells items immediately without requiring the parcel chore.
- **Rattata & Raticate "Dick Biters" Inside Joke (`src/data/text/species_names.h`, `src/data/pokemon/pokedex_entries.h`, `pokedex_text_fr.h`, `Route1/text.inc`):**
  - Renamed both Rattata and Raticate to **DICK BITER** in species names and Pokédex categories.
  - Authored custom Pokédex descriptions detailing their fangs and notorious reputation among Joseph and IT staff.
  - Added Route 1 dialogue from the clerk and boy NPC warning about wild Dick Biters jumping out of the tall grass.
- **Squirtle Squad Meme Shades & SQUAD SHADES Held Item (`rom/overrides/graphics/pokemon/squirtle/front.png`, `src/data/items.json`, `src/data/pokemon/species_info.h`):**
  - Rendered sharp, pointed anime sunglasses (Kamina / Squirtle Squad leader meme shades) directly onto Squirtle's 64×64 16-color GBA battle front sprite with white reflection glint.
  - Rebranded `ITEM_BLACK_GLASSES` in `items.json` to `"SQUAD SHADES"` (*"Pointy shades of the SQUIRTLE SQUAD! Radiates unmatched boss energy and boosts DARK-type move damage."*).
  - Configured wild Squirtle in `species_info.h` to hold `SQUAD SHADES`.
- **Classic Anime / Cartoon Iconic Moments (`Route4_PokemonCenter_1F/text.inc`, `CeruleanCity_Gym/text.inc`, `Route25_SeaCottage/text.inc`, `Route24/text.inc`, `CeruleanCity_PokemonCenter_1F/text.inc`):**
  - *S.S. Anne Magikarp Salesman (Ep. 15)*: Salesman in Route 4 Center pitches the golden egg-laying Magikarp scam.
  - *Misty's Charred Bicycle (Ep. 1 & 2)*: Swimmer Luis and Gym Guy in Cerulean Gym reveal Misty is still furious about a kid with a Pikachu frying her bike.
  - *Giant Dragonite at the Sea Cottage (Ep. 13)*: Bill describes the colossal dragon calling in the foggy mist at night.
  - *Squirtle Squad Ambush (Ep. 12)*: Camper Shane on Route 24 describes the sunglasses-wearing gang and their signature Squad Shades.
  - *Damian & Abandoned Charmander (Ep. 11)*: Damian brags at the Cerulean Pokémon Center counter about leaving his Charmander on a rock waiting in the rain.

### Fixed & Expanded (2026-11-17 Audit & Playable Anime Update)
- **Oak's Lab Starter & Rival Cutscene Fix (`PalletTown_ProfessorOaksLab/scripts.inc`, `text.inc`, `Route1/scripts.inc`):**
  - Fixed `PalletTown_ProfessorOaksLab_EventScript_RivalTakesStarter` leaving `"GREG received the ... from PROF. OAK!"` frozen on screen by adding `waitbuttonpress` and `closemessage` before setting `VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB = 3`.
  - Updated `PalletTown_ProfessorOaksLab_Text_RivalMyMonLooksTougher` so talking to Greg at the table directs the player to walk down toward the exit door (`y = 8`) to start the rival battle instead of feeling stuck.
  - Moved Oak's 20 Poké Ball gift *after* receiving Dratini with dedicated dialogue (`PalletTown_ProfessorOaksLab_Text_OakGiveStarterPokeBalls`), kept 10 backup Poké Balls + 5 Potions at New Game start, and fixed the Route 1 Mart Clerk's Potion + 10 Poké Balls message order.
- **Hardware-Masked `L+R` Auto-Run Engine (`src/main.c`, `src/field_player_avatar.c`, `web/src/App.tsx`):**
  - Replaced the broken `emu.buttonPress('B')` auto-run implementation (which broke `B` in menus and auto-cancelled evolutions in `evolution_scene.c`) with a stateless hardware-masked `L+R` chord (`gAutoRunEnabled`) stripped from `keyInput` inside `ReadKeys()`.
  - When `RUN` is toggled ON, Joseph sprints automatically without holding `B` (holding `B` walks cleanly for tight indoor corners), `B` works 100% normally in menus/evolutions, and `syncAutoRunChord` temporarily unpresses the opposite shoulder button during manual `L`/`R` pocket taps.
- **Rattata & Raticate "Dick Biters" Classification Fix (`pokedex_entries.h`, `pokedex_text_fr.h`, `Route1/text.inc`, `Route3/text.inc`):**
  - Restored `RATTATA` and `RATICATE` as their canonical species names while keeping their Pokédex classification set to **`DICK BITER`** (`DICK BITER POKéMON`) and referring to them as *"Dick Biters"* across Pokédex entries and Kanto NPC/trainer dialogue.
- **Sprite Quality Overhaul — Squirtle Squad Shades, Overworld Joseph & Battle Back (`rom/scripts/render_squirtle_shades.py`, `convert_all_player_sprites.py`, `convert_battle_back.py`, `rom/assets/joseph_battle_back_source.jpg`):**
  - Replaced murky green oversized polygon sunglasses on Squirtle with crisp jet-black (`#101010`) pointed Squirtle Squad leader shades + white/silver reflection glint on **both** `front.png` and `back.png`, and upgraded `SQUAD SHADES` (`ITEM_BLACK_GLASSES`) to `HOLD_EFFECT_WATER_POWER` (+20% Water-type move damage).
  - Rewrote `convert_all_player_sprites.py` with dynamic per-frame head-top detection (`find_head_bounds`) and exact per-sheet facing arrays across all 7 overworld sprite sheets (`red_normal.png`, `red_surf_run.png`, `red_bike.png`, `red_surf.png`, `red_fish.png`, `red_item.png`, `red_vs_seeker_bike.png`) + `player_icon_red.png`, eliminating all leftover cap visors and red hat tops.
  - Fixed `convert_battle_back.py` so `cleaned = Image.fromarray(crop_arr)` preserves artifact cleanup and removes the duplicate Poké Ball in Frame 0's left hand, backed by repo-tracked `rom/assets/joseph_battle_back_source.jpg`.
- **8 Playable 90s Indigo League Anime Events (`rom/scripts/apply_josephred.py`):**
  - **Ep. 1 (`Route1` at `14,18`):** Angry Spearow ambush (`OBJ_EVENT_GFX_SPEAROW`) followed by golden **Ho-Oh** rainbow sky sighting + `ITEM_SACRED_ASH` drop (`FLAG_WONDER_CARD_UNUSED_1`).
  - **Ep. 45 (`Route3` at `66,11`):** Singing Marker **Jigglypuff** (`MUS_JIGGLYPUFF` lullaby, sleep blackout, permanent marker scribble, Lv. 9 wild battle, `FLAG_WONDER_CARD_UNUSED_2`) + Youngster Ben's shorts/Dick Biter gag.
  - **Ep. 2 & 6 (`MtMoon_B2F` & `SilphCo_11F`):** **Jessie**, **James**, and **Talking Meowth** (`OBJ_EVENT_GFX_MEOWTH`) with female Rocket sprite/pic, full motto, James's head-chomping Victreebel gag, and canonical anime teams (Ekans/Koffing/Meowth → Arbok/Lickitung/Weezing/Victreebel/Meowth).
  - **Ep. 11 (`Route24` at `5,15`):** Rescuable **Lv. 12 Stray Charmander** holding `ITEM_CHARCOAL` on the rock west of Nugget Bridge (`FLAG_WONDER_CARD_UNUSED_3`).
  - **Ep. 27 (`Route24` at `15,25`):** **Misty's Migraine Psyduck** psychic flash + Lv. 14 wild battle holding `ITEM_TWISTED_SPOON` (`FLAG_WONDER_CARD_UNUSED_4`).
  - **Ep. 10 (`Route25` at `56,7`):** **Melanie's Hidden Village Bulbasaur** sanctuary gift — **Lv. 14 Bulbasaur** holding `ITEM_MIRACLE_SEED` (`FLAG_WONDER_CARD_UNUSED_5`).
  - **Ep. 12 (`VermilionCity` at `23,13`):** **Officer Jenny** recruiting Joseph to lead the **Lv. 16 Squirtle Squad Leader** holding `ITEM_BLACK_GLASSES` (`SQUAD SHADES`) (`FLAG_WONDER_CARD_UNUSED_6`).
  - **Ep. 21 (`VermilionCity` pier at `28,30`):** ***"Bye Bye Butterfree"*** overlook gifting `ITEM_SILVER_POWDER` + `ITEM_RARE_CANDY` (`FLAG_WONDER_CARD_UNUSED_7`), plus persistent `FLAG_WONDER_CARD_UNUSED_8` on Vermilion Harbor Bus-kun Mew.

### Automated Full-Game ROM Verification Suite & Sightline Fixes (2026-11-18)
- **Layer 1 Static ROM & ELF Verifier (`rom/scripts/verify_rom_static.py`, `rom/docker/Dockerfile`):**
  - Integrated automated static verification directly into the Docker ROM build pipeline across all 54,303 compiled ELF symbols, 425 maps (`SaveBlock1` 64-object limit, tile bounds, `collision == 0`, warp overlap), 29 trainer sightlines, 7 2D BFS corridor reachability proofs, and 566 ASM `EventScript` blocks (checking script termination and unclosed raw `message` leaks).
- **Trainer Sightline Walk-Collision Fixes & Viridian Mart Parcel Reminder (`rom/scripts/apply_josephred.py`):**
  - Fixed two potential `waitmovement` trainer walk-up collisions caught by `verify_rom_static.py`: moved **Talking Meowth** out of Jessie's pre-battle sightline on `MtMoon_B2F` (`(13,20)` → `(11,21)`) and `SilphCo_11F` (`(2,18)` → `(1,19)`).
  - Added `ViridianCity_Mart_Text_ParcelReminderShop` so the Viridian Mart clerk reminds players carrying `OAK'S PARCEL` to deliver it back to Pallet Town while still opening the shop immediately.
- **Layer 2 High-Speed Runtime Checkpoint Suite (`scripts/verify_rom_runtime.py`, `web/src/App.tsx`):**
  - Built an automated ~5,000-FPS headless `@thenick775/mgba-wasm` checkpoint runner inspecting live ARM7TDMI EWRAM/IWRAM state (`gbAs` serialization + `pokefirered.elf` symbol table) across all 19 end-to-end Kanto checkpoints from the Bus-kun prologue through Champion Brian.






