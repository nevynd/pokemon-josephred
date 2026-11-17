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



