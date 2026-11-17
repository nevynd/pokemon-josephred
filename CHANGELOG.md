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

