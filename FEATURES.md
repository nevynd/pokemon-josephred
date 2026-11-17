# Pokémon JosephRed — Features

> Status legend: `Built (Pending Approval)` | `In Progress` | `Planned`  
> *(Nothing is marked Complete without explicit user verification and approval.)*

## ROM Customization (`josephred.gba`)
- **Custom Title Screen (`JOSEPHRED VERSION`):** `Built (Pending Approval)` — Metallic GBA chrome badge rendered onto FireRed's flame title screen.
- **Bus-kun Isekai Opening & Dratini Oak Speech:** `Built (Pending Approval)` — 3-page EU `EUR/USD` Forex + Coffee + Ninja Creami + Isekai Bus-kun prologue; Oak releases a Dratini and defaults player to `JOSEPH` & rival to `GREG`.
- **Joseph Custom Photo Intro & Trainer Card Sprite:** `Built (Pending Approval)` — Custom GBA pixel-art sprite of Joseph (stockier build, fluffy forward-and-up hair, charcoal Poké Ball graphic T-shirt with no lanyard, blue jeans, coffee cup, & Poké Ball) compiled into both Oak's Intro (`64×96` 31-color) and his in-game Trainer Card (`64×64` 16-color).
- **All 3 Poké Balls Secretly Dratini:** `Built (Pending Approval)` — Inspecting Ball 1, 2, or 3 in Oak's Lab reveals all three are secretly Lv. 5 Dratini (learns *Twister* at Lv. 5, evolves into Dragonite at Lv. 48).
- **Buffoon Rival Greg vs. Competent Champion Brian:** `Built (Pending Approval)` — Greg stays the bumbling recurring rival throughout Kanto while `TRAINER_CLASS_CHAMPION` is decoupled in C source so **Brian** reigns as final Champion.
- **Custom Boss Lineup:** `Built (Pending Approval)` — **Erica L** (Celadon / Snorlax sector), **Charles B** (Saffron / Windchill sector), **Stephane** (recurring French/African-accented menace at Hideout, Windchill Silph Co., & Viridian), and Indigo Plateau Gauntlet: **Jessica → Siva → Erin (3rd to last) → Sonny (2nd to last) → Champion Brian (last)**.
- **Inside Jokes & World Flavor:** `Built (Pending Approval)` — *"Teamwork Makes the Dreamwork!"*, **The Flying Saucer** beer house (Celadon taproom, 200-beer UFO ceiling plates, Pallet Town & Champion Brian pints), **Commander Riker** chair-sit tributes, **PTC Windchill & DB Maintenance** Silph Co. takeover, **DNS Snorlax (`ipconfig /flushdns`)**, **Hot Coffee / Iced Espresso / Ninja Creami** rooftop bar, EU Forex Desk, sushi/Japan cherry blossoms, and **Vermilion Harbor Bus-kun Lv. 30 Mew** Easter egg.
- **Solo-151 & Modern QoL:** `Built (Pending Approval)` — Running Shoes from step 1 (indoors + outdoors), infinite reusable TMs, level-up trade evolutions, LeafGreen exclusives merged onto Kanto routes, and wild Bulbasaur/Charmander/Squirtle.

## Mobile Web GBA SP Shell (`/web`)
- **JosephRed GBA SP Touch UI:** `Built (Pending Approval)` — Portrait & landscape responsive shell (`App.tsx`) with smooth thumb-slide D-Pad, A/B, L/R, Start/Select, haptics, and desktop keyboard controls.
- **1× / 2× / 4× Fast-Forward & Run Lock:** `Built (Pending Approval)` — Instant speed multiplier (`1× / 2× / 4×`) + one-tap `RUN` toggle holding `B` for effortless one-handed sprinting.
- **Persistent Auto-Save & Backup:** `Built (Pending Approval)` — Automatic IndexedDB SRAM sync on in-game save & tab hide, 3 quick save-state slots, `.sav` file Export/Import, and custom `.gba` loader.
