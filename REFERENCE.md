# Pokémon JosephRed — System Reference

## 1. Architecture Overview

**Pokémon JosephRed** is a custom-built GBA ROM hack of *Pokémon FireRed* (`pret/pokefirered` C/ASM disassembly) paired with a custom mobile-first WebAssembly GBA SP player (`@thenick775/mgba-wasm` + React 19 + TypeScript + Vite).

```
h:\JPate
├── Dockerfile                        # Root multi-stage Node 22 Alpine container for Railway
├── REFERENCE.md                      # Architecture, ROM mod registry, & cast reference
├── FEATURES.md                       # Feature tracking matrix (Rule 2 compliant)
├── CHANGELOG.md                      # Chronological build & lore change log
├── scripts/
│   └── build-rom.ps1                 # Deterministic Docker ROM build & extraction script
├── rom/
│   ├── docker/
│   │   ├── Dockerfile.base           # Cached Ubuntu 22.04 + agbcc + baseline pokefirered objects
│   │   └── Dockerfile                # Incremental mod layer (~3s rebuilds)
│   ├── overrides/
│   │   └── graphics/
│   │       ├── title_screen/firered/game_title_logo.png
│   │       └── oak_speech/red/       # Optional custom 64x96 portrait (pic.png + pal.pal)
│   ├── scripts/
│   │   ├── apply_josephred.py        # Validated C/JSON/ASM patcher + GBA textbox width linter
│   │   ├── render_title_badge.py     # Chrome 'JOSEPHRED VERSION' title logo generator
│   │   └── convert_portrait.py       # Photo -> GBA 31-color 8bpp Oak Speech portrait converter
│   └── upstream-pokefirered/         # Local read-only upstream reference (gitignored)
└── web/
    ├── server.mjs                    # Production HTTP server with COOP/COEP headers for WASM threads
    ├── vite.config.ts                # Dev/preview server with COOP/COEP headers
    ├── public/roms/josephred.gba     # Compiled 16 MB GBA ROM (GAME_CODE=BPRE for 128KB Flash1M SRAM)
    └── src/                          # Mobile-first 'JosephRed SP' touch web shell
```

---

## 2. ROM Build & Asset Pipelines

### Rebuilding the ROM
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-rom.ps1
```
- Uses `josephred-rom-base:latest` (cached `pret/agbcc` + precompiled `pokefirered` `.o` tree).
- Runs `rom/scripts/apply_josephred.py` which asserts every upstream C/ASM anchor and lints all custom GBA strings against the 36-char textbox limit before invoking `make -j$(nproc)`.
- Keeps GBA binary header `GAME_CODE = BPRE` intact so `mGBA` automatically provisions **128KB Flash 1M** save memory (`SAVE_FLASH1M`) without *"1M sub-circuit board is not installed"* warnings.

### Converting a Photo of Joseph for Intro & Trainer Card Graphics
```powershell
python .\rom\scripts\convert_portrait.py --input .\rom\assets\joseph_trainer_source.jpg --overrides-root .\rom\overrides
powershell -ExecutionPolicy Bypass -File .\scripts\build-rom.ps1
```
- `src/oak_speech.c` loads `sOakSpeech_Red_Pal` into `BG_PLTT_ID(4)` (VRAM palette indices `64..95`).
- `convert_portrait.py` keys out background/fringe pixels, grounds the full-body sprite to `64×96`, quantizes foreground pixels into 31 15-bit GBA colors at indices `65..95` (`0` = transparent) for `rom/overrides/graphics/oak_speech/red/`, AND simultaneously builds a 16-color `64×64` 4bpp sprite in `rom/overrides/graphics/trainers/` for Joseph's in-game Trainer Card.

---

## 3. Core Gameplay & Solo-151 Modifications

| Area | Upstream File(s) | Modification |
|---|---|---|
| Title Screen | `graphics/title_screen/firered/game_title_logo.png` | Custom brushed-chrome **JOSEPHRED VERSION** badge in non-overlapping tile box `(176, 8, 256, 40)` |
| Intro Species | `src/oak_speech.c` | `INTRO_SPECIES` changed to `SPECIES_DRATINI` |
| Player Graphics (Full Replacement) | `graphics/oak_speech/red/`, `graphics/trainers/front_pics/`, `graphics/object_events/pics/people/red_*.png`, `graphics/trainers/back_pics/red_back_pic.png`, `graphics/region_map/player_icon_red.png` | Ash completely replaced by **Joseph** across all modes: 64×96 Oak intro platform, 64×64 Trainer Card, overworld walking/running/cycling/surfing/fishing sheets, 5-frame battle back-sprite, and 16×16 Town Map head icon |
| Default Names | `src/oak_speech.c`, `data/text/new_game_intro.inc` | Player defaults to **JOSEPH** (`JPATE` alt); Rival defaults to **GREG** (`BUFFOON` alt) |
| All 3 Balls = Dratini | `PalletTown_ProfessorOaksLab/scripts.inc`, `src/field_specials.c`, `src/wild_pokemon_area.c` | All 3 Poké Balls on Oak's table secretly yield Lv. 5 **Dratini** with escalating inspection gags |
| Dratini Balance | `src/data/pokemon/level_up_learnsets.h`, `evolution.h` | Learns **Twister** (40 BP Dragon) at Lv. 5; Dragonair evolves into **Dragonite** at Lv. 48 (down from 55) |
| Champion Decoupling | `src/battle_message.c`, `src/quest_log_events.c` | Decouples `TRAINER_CLASS_CHAMPION` from `PLACEHOLDER_ID_RIVAL` so Champion displays **BRIAN** while Rival stays **GREG** |
| Running Shoes | `src/new_game.c`, `src/bike.c` | `FLAG_SYS_B_DASH` enabled from New Game init; indoor running restriction removed |
| Reusable TMs | `src/party_menu.c` | TMs (`< ITEM_HM01`) are never consumed upon teaching a move |
| Solo Trade Evos | `src/data/pokemon/evolution.h` | Kadabra (Lv. 36), Haunter (Lv. 36), Machoke (Lv. 38), Graveler (Lv. 38) evolve by level-up |
| Solo 151 Wild Mons | `src/data/wild_encounters.json` | Merges *LeafGreen* exclusives onto canonical FireRed routes + adds wild Bulbasaur (Viridian Forest), Charmander (Route 4), Squirtle (Route 24) |
| Bus-kun Mew | `data/maps/SSAnne_Exterior/map.json`, `scripts.inc` | Inspecting the Vermilion Harbor truck (`x=55..57, y=3`) triggers the **Isekai Bus-kun** gag + wild Lv. 30 **Mew** |

---

## 4. Cast, Lore & Inside-Joke Registry

| In-Game Role | Cast / Reference | Location / Trigger |
|---|---|---|
| Hero | **JOSEPH** (*"Teamwork Makes the Dreamwork!"*) | Playable protagonist across all modes: Oak intro, Trainer Card, all overworld movements, battle back-sprite, and Town Map icon |
| Opening Scene | **Bus-kun Isekai** + **EU `EUR/USD` Forex** | 3-page prologue + Prof. Oak's intro speech |
| Buffoon Rival | **GREG** | All Rival encounters (blames lag, unplugged mice, & DNS; disqualifies himself before Champion) |
| Recurring Menace | **STEPHANE** (male, French/African-inflected cadence) | Senior IT Admin running the enterprise merger domain migration; cross-forest trusts, 4:58 PM Friday cutovers, 15-minute replication. Encounters at Rocket Hideout B4F, PTC Windchill HQ (Silph Co. 11F), & Viridian Gym |
| Snorlax Neighbor Boss | **ERICA L** | Celadon City Gym Leader (right next to Route 16 DNS Snorlax) |
| Windchill Area Boss | **CHARLES B** | Saffron City Gym Leader (next door to PTC Windchill / Silph Co. 11F) |
| Elite Four #1 | **JESSICA** | Indigo Plateau — Room 1 (Lorelei slot) |
| Elite Four #2 | **SIVA** | Indigo Plateau — Room 2 (Bruno slot) |
| Elite Four #3 (3rd to last) | **ERIN** | Indigo Plateau — Room 3 (Agatha slot) |
| Elite Four #4 (2nd to last) | **SONNY** | Indigo Plateau — Room 4 (Lance slot — reveals Greg failed Victory Road & Brian is Champion) |
| League Champion (Final Boss) | **BRIAN** | Indigo Plateau — Champion's Room (competent powerhouse boss) |
| Beverages / Healing | **HOT COFFEE** (50 HP), **ICED ESPRESSO** (60 HP), **NINJA CREAMI** (80 HP), **DARK ROAST** (Key Item) | Celadon Rooftop Breakroom Vending Machines & Saffron Outage Guards |
| Local Hangout | **THE FLYING SAUCER** (Beer House — 200 draught taps & UFO plates on the ceiling) | Oak's Intro, Pallet Town, Celadon City Sign, full Celadon Restaurant (`COIN CASE` hangout), & Champion Brian's victory celebration |
| IT / Infra Gags | **PTC Windchill**, **DB Maintenance**, **DNS (`ipconfig /flushdns`)**, **Commander Riker Chair Maneuver**, **Sushi & Japan Cherry Blossoms** | Silph Co. 11F, Routes 12 & 16 Snorlax, Celadon EU Forex Desk, Gym Statues, & Hall of Fame |

---

## 5. Web GBA SP Player (`/web`)

- **Emulator Core:** `@thenick775/mgba-wasm` running inside WebAssembly with `SharedArrayBuffer` support (`Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Embedder-Policy: require-corp`).
- **Mobile Controls:** Responsive portrait **JosephRed GBA SP** shell + landscape layout, multi-touch D-Pad + A/B + L/R + Start/Select, haptic feedback (`navigator.vibrate`), and keyboard bindings on desktop.
- **Speed & Persistence:** One-tap **1× / 2× / 4× Fast-Forward** toggle, automatic `FS.syncfs` IndexedDB persistence after saves + periodic intervals, 3 quick save-state slots, and `.sav` file Export/Import backup.

---

## 6. Railway Production Deployment

- **Railway Project:** `pokemon-josephred` (`ffd68767-561b-430d-97c3-c69b095f27e8`)
- **Railway Service:** `pokemon-josephred` (`a40063ca-19d2-416a-8a9c-c22ce442c827`)
- **Environment:** `production` (`e1b3fbd2-c075-4d29-8ab9-47d3556c942e`)
- **GitHub Repository:** `nevynd/pokemon-josephred` (`main` branch, auto-deploy enabled)
- **Deployment Status:** `SUCCESS` (Container listening on `0.0.0.0:8080`)
- **Default Live URL:** `https://pokemon-josephred-production.up.railway.app`
- **Custom Domain:** `https://joseph.beenelson.com` (routes to container port `8080`)
- **DNS Records to Configure:**
  - `CNAME joseph.beenelson.com` → `mweew3gn.up.railway.app`
  - `TXT _railway-verify.joseph.beenelson.com` → `railway-verify=fa1ac64a5c3ab03e5d563e290f6b6132a774a9371548bbf0c6e3172fb5a590d9`

