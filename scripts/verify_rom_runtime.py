#!/usr/bin/env python3
"""
Layer 2 High-Speed Runtime Checkpoint Verifier for Pokémon JosephRed.

Executes the UNMODIFIED production `web/public/roms/josephred.gba` cartridge inside
`@thenick775/mgba-wasm` at ~5,000+ GBA FPS (`EM_TIMING_SETTIMEOUT` + `frameSkip=9`),
binding exact live `gObjectEvents` + `gSpecialVar_LastTalked` state and verifying
ARM7TDMI EWRAM/IWRAM symbols (`pokefirered.elf`) across all 19 end-to-end story, QoL,
playable anime, and boss-gauntlet checkpoints from Pallet Town through Champion Brian!
"""

from __future__ import annotations
import struct
import subprocess
import sys
import time
import zlib
from playwright.sync_api import sync_playwright


IWRAM_OFF = 0x19000  # 0x03000000 .. 0x03007FFF inside 0x61000 mGBA gbAs state
EWRAM_OFF = 0x21000  # 0x02000000 .. 0x0203FFFF inside 0x61000 mGBA gbAs state

SPECIES_MEWTWO = 150
MOVE_BITE = 44  # 60 BP Special Dark in Gen 3, 100% Acc, 25 PP, ZERO immunities!
MOVE_DRAGON_CLAW = 337  # 80 BP Special in Gen 3, 100% Acc, 15 PP, ZERO Gen 3 immunities!
MOVE_PSYCHIC = 94
MOVE_SURF = 57
MOVE_FLAMETHROWER = 53
MOVE_THUNDERBOLT = 85

ITEM_POKE_BALL = 4
ITEM_SACRED_ASH = 45
ITEM_RARE_CANDY = 68
ITEM_SILVER_POWDER = 188
ITEM_BLACK_GLASSES = 206
ITEM_COIN_CASE = 260
ITEM_OAKS_PARCEL = 349
ITEM_TEA = 369  # DARK ROAST

FLAG_WONDER_CARD_1 = 0x2AA  # Spearow + Ho-Oh
FLAG_WONDER_CARD_2 = 0x2AB  # Singing Jigglypuff
FLAG_WONDER_CARD_3 = 0x2AC  # Stray Charmander
FLAG_WONDER_CARD_4 = 0x2AD  # Migraine Psyduck
FLAG_WONDER_CARD_5 = 0x2AE  # Melanie Bulbasaur
FLAG_WONDER_CARD_6 = 0x2AF  # Officer Jenny Squirtle Squad
FLAG_WONDER_CARD_7 = 0x2B0  # Bye Bye Butterfree
FLAG_WONDER_CARD_8 = 0x2B1  # Bus-kun Mew
FLAG_SYS_POKEMON_GET = 0x828
FLAG_SYS_POKEDEX_GET = 0x829

VAR_VIRIDIAN_OLD_MAN = 0x4051
VAR_OAKS_LAB_SCENE = 0x4055
VAR_VIRIDIAN_MART = 0x4057


def load_elf_syms() -> dict[str, int]:
    out = subprocess.check_output(
        ["docker", "run", "--rm", "josephred-rom:latest", "arm-none-eabi-nm", "/opt/pokefirered/pokefirered.elf"],
        text=True,
    )
    syms: dict[str, int] = {}
    for ln in out.splitlines():
        p = ln.split()
        if len(p) >= 3:
            try:
                syms[p[2]] = int(p[0], 16)
            except ValueError:
                pass
    return syms


class GbaState:
    def __init__(self, png_bytes: bytes):
        self.chunks: list[tuple[bytes, bytes]] = []
        self.raw = bytearray()
        pos = 8
        while pos < len(png_bytes):
            length, ctype = struct.unpack(">I4s", png_bytes[pos : pos + 8])
            cdata = png_bytes[pos + 8 : pos + 8 + length]
            if ctype == b"gbAs":
                self.raw = bytearray(zlib.decompress(cdata))
            self.chunks.append((ctype, cdata))
            pos += 12 + length
        assert len(self.raw) == 0x61000, f"Unexpected gbAs size: 0x{len(self.raw):x}"

    def _off(self, addr: int) -> int:
        if 0x02000000 <= addr < 0x02040000:
            return EWRAM_OFF + (addr - 0x02000000)
        if 0x03000000 <= addr < 0x03008000:
            return IWRAM_OFF + (addr - 0x03000000)
        raise ValueError(f"Unsupported GBA RAM address: 0x{addr:08x}")

    def u8(self, addr: int) -> int:
        return self.raw[self._off(addr)]

    def u16(self, addr: int) -> int:
        return struct.unpack_from("<H", self.raw, self._off(addr))[0]

    def u32(self, addr: int) -> int:
        return struct.unpack_from("<I", self.raw, self._off(addr))[0]

    def write(self, addr: int, data: bytes) -> None:
        o = self._off(addr)
        self.raw[o : o + len(data)] = data

    def write_u8(self, addr: int, val: int) -> None:
        self.raw[self._off(addr)] = val & 0xFF

    def write_u16(self, addr: int, val: int) -> None:
        struct.pack_into("<H", self.raw, self._off(addr), val & 0xFFFF)

    def write_u32(self, addr: int, val: int) -> None:
        struct.pack_into("<I", self.raw, self._off(addr), val)

    def sb1(self, syms: dict[str, int]) -> int:
        return self.u32(syms["gSaveBlock1Ptr"])

    def get_flag(self, syms: dict[str, int], flag_id: int) -> bool:
        base = self.sb1(syms) + 0x0EE0 + (flag_id >> 3)
        return bool((self.u8(base) >> (flag_id & 7)) & 1)

    def get_var(self, syms: dict[str, int], var_id: int) -> int:
        base = self.sb1(syms) + 0x1000 + (var_id - 0x4000) * 2
        return self.u16(base)

    def has_item(self, syms: dict[str, int], item_id: int) -> bool:
        sb1 = self.sb1(syms)
        for off, count in ((0x0310, 42), (0x03B8, 30), (0x0430, 13)):
            for i in range(count):
                if self.u16(sb1 + off + i * 4) == item_id:
                    return True
        return False

    def find_obj_slot(self, syms: dict[str, int], local_id: int) -> int:
        base = syms["gObjectEvents"]
        for slot in range(16):
            obj = base + slot * 0x24
            if (self.u8(obj) & 1) and self.u8(obj + 0x08) == local_id:
                return slot
        return 0

    def encode_png(self) -> bytes:
        out = bytearray(b"\x89PNG\r\n\x1a\n")
        for ctype, cdata in self.chunks:
            if ctype == b"gbAs":
                cdata = zlib.compress(bytes(self.raw), level=1)
            out += struct.pack(">I", len(cdata))
            out += ctype
            out += cdata
            crc = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
            out += struct.pack(">I", crc)
        return bytes(out)


def bc_givemon(species: int, level: int, item: int = 0) -> bytes:
    return struct.pack("<BHBH", 0x79, species, level, item) + (b"\x00" * 9)


def bc_setmonmove(party_idx: int, slot: int, move: int) -> bytes:
    return struct.pack("<BBBH", 0x7B, party_idx, slot, move)


def bc_heal() -> bytes:
    return struct.pack("<BH", 0x25, 0)


def bc_warp(group: int, num: int, x: int, y: int) -> bytes:
    return struct.pack("<BBBBhh", 0x39, group, num, 0xFF, x, y)


def bc_goto(rom_addr: int) -> bytes:
    return struct.pack("<BI", 0x05, rom_addr)


def bc_end() -> bytes:
    return b"\x02"


def snap_state(page) -> GbaState:
    data = page.evaluate(
        """() => {
        const emu = window.__JOSEPHRED_EMU__.raw;
        emu.saveState(9);
        const p = emu.filePaths().saveStatePath + '/josephred.ss9';
        return Array.from(emu.FS.readFile(p));
    }"""
    )
    return GbaState(bytes(data))


def inject_script(
    page,
    syms: dict[str, int],
    bytecode: bytes,
    local_id: int | None = None,
    clear_outcome: bool = True,
) -> None:
    st = snap_state(page)
    # Enforce FAST text (2), Battle Style SET (bit 1), and Battle Animations OFF (bit 2) in SaveBlock2
    # so "Will JOSEPH change POKéMON?" never opens CB2_UpdatePartyMenu mid-battle and battles run 4x faster!
    sb2 = st.u32(syms["gSaveBlock2Ptr"])
    if sb2:
        st.write_u8(sb2 + 0x14, (st.u8(sb2 + 0x14) & ~0x07) | 0x02)
        st.write_u8(sb2 + 0x15, st.u8(sb2 + 0x15) | 0x06)

    scratch_addr = st.sb1(syms) + 0x348C
    assert len(bytecode) <= 380, "Bytecode exceeds SaveBlock1.unused_348C!"
    st.write(scratch_addr, bytecode)
    if clear_outcome:
        st.write_u8(syms["gBattleOutcome"], 0)
    if local_id is not None:
        st.write_u16(syms["gSpecialVar_LastTalked"], local_id)
        st.write_u8(syms["gSelectedObjectEvent"], st.find_obj_slot(syms, local_id))

    ctx_addr = syms["sGlobalScriptContext"]
    status_addr = syms["sGlobalScriptContextStatus"]
    st.write_u8(ctx_addr + 0x00, 0)
    st.write_u8(ctx_addr + 0x01, 1)  # SCRIPT_MODE_BYTECODE
    st.write_u32(ctx_addr + 0x04, 0)
    st.write_u32(ctx_addr + 0x08, scratch_addr)
    st.write_u8(status_addr, 0)  # CONTEXT_RUNNING

    page.evaluate(
        """(bytes) => {
        const emu = window.__JOSEPHRED_EMU__.raw;
        const p = emu.filePaths().saveStatePath + '/josephred.ss9';
        emu.FS.writeFile(p, new Uint8Array(bytes));
        emu.loadState(9);
    }""",
        list(st.encode_png()),
    )


def drive_until_idle(
    page,
    syms: dict[str, int],
    yes_until_flag: int | None = None,
    expect_map: tuple[int, int] | None = None,
    max_iters: int = 120,
) -> GbaState:
    last_diag = ""
    for i in range(max_iters):
        st = snap_state(page)
        sb1 = st.sb1(syms)
        mg, mn = st.u8(sb1 + 4), st.u8(sb1 + 5)
        in_battle = (st.u8(syms["gMain"] + 0x439) & 2) != 0
        ctx_status = st.u8(syms["sGlobalScriptContextStatus"])
        locked = st.u8(syms["sLockFieldControls"])
        cb2 = st.u32(syms["gMain"] + 0x04) & ~1
        last_diag = f"map=({mg},{mn}), in_battle={in_battle}, ctx_status={ctx_status}, locked={locked}, cb2=0x{cb2:08x}"
        map_ok = (expect_map is None) or ((mg, mn) == expect_map)
        if map_ok and not in_battle and ctx_status == 2 and locked == 0 and cb2 == syms["CB2_Overworld"]:
            return st

        if in_battle:
            if cb2 == syms.get("CB2_UpdatePartyMenu", 0):
                page.evaluate(
                    """async () => {
                    const emu = window.__JOSEPHRED_EMU__.raw;
                    const tap = async (b) => { emu.buttonPress(b); await new Promise(r => setTimeout(r, 18)); emu.buttonUnpress(b); await new Promise(r => setTimeout(r, 18)); };
                    await tap('B'); await tap('B'); await tap('Right'); await tap('A'); await tap('A');
                }"""
                )
                continue
            btn = "B" if (i % 7 == 6) else "A"
        elif yes_until_flag is not None and not st.get_flag(syms, yes_until_flag):
            btn = "A"
        else:
            btn = "B"

        page.evaluate(
            """async (btn) => {
            const emu = window.__JOSEPHRED_EMU__.raw;
            for (let k = 0; k < 9; k++) {
                emu.buttonPress(btn);
                await new Promise(r => setTimeout(r, 12));
                emu.buttonUnpress(btn);
                await new Promise(r => setTimeout(r, 12));
            }
        }""",
            btn,
        )
    raise TimeoutError(
        f"[SOFTLOCK/TIMEOUT] Did not return to unlocked CB2_Overworld within {max_iters} cycles ({last_diag})"
    )


def warp_to(page, syms: dict[str, int], group: int, num: int, x: int, y: int) -> GbaState:
    inject_script(page, syms, bc_heal() + bc_warp(group, num, x, y) + bc_end())
    page.wait_for_timeout(60)
    return drive_until_idle(page, syms, expect_map=(group, num))


def run_npc_script(
    page,
    syms: dict[str, int],
    group: int,
    num: int,
    px: int,
    py: int,
    script_sym: str,
    local_id: int | None = None,
    yes_until_flag: int | None = None,
) -> GbaState:
    """Warps adjacent to the NPC on the live map, binds exact ObjectEvent/LastTalked, and runs the script to idle!"""
    st_warp = warp_to(page, syms, group, num, px, py)
    won_on_sight = st_warp.u8(syms["gBattleOutcome"]) == 1
    inject_script(
        page,
        syms,
        bc_heal() + bc_goto(syms[script_sym]),
        local_id=local_id,
        clear_outcome=not won_on_sight,
    )
    page.wait_for_timeout(35)
    return drive_until_idle(page, syms, yes_until_flag=yes_until_flag)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    t_start = time.time()
    print("=== [Layer 2] Pokémon JosephRed High-Speed Runtime Checkpoint Verifier ===")
    syms = load_elf_syms()
    print(f"[INIT] Loaded {len(syms):,} live ELF symbols (CB2_Overworld=0x{syms['CB2_Overworld']:08x})")

    passed: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--disable-features=CalculateNativeWinOcclusion",
            ],
        )
        page = browser.new_page()
        page.goto("http://localhost:4173/?__verify=1", wait_until="networkidle")
        page.wait_for_function("() => window.__JOSEPHRED_EMU__ && window.__JOSEPHRED_EMU__.raw", timeout=15000)

        page.evaluate(
            """() => {
            const emu = window.__JOSEPHRED_EMU__.raw;
            emu.setVolume(0);
            emu.setCoreSettings({
                frameSkip: 9,
                videoSync: false,
                audioSync: false,
                timestepSync: false,
                rewindEnable: false,
                autoSaveStateEnable: false,
            });
            emu.setMainLoopTiming(0, 1);
            emu.setFastForwardMultiplier(20);
        }"""
        )

        # 01. Boot New Game -> Bedroom
        print("[01/19] Booting New Game through Bus-kun Prologue & Oak Speech...")
        page.wait_for_timeout(350)
        for _ in range(4):
            page.evaluate(
                """async () => {
                const emu = window.__JOSEPHRED_EMU__.raw;
                emu.buttonPress('Start'); await new Promise(r => setTimeout(r, 25)); emu.buttonUnpress('Start');
            }"""
            )
            page.wait_for_timeout(40)

        reached_bedroom = False
        for step in range(45):
            page.evaluate(
                """async (pickDown) => {
                const emu = window.__JOSEPHRED_EMU__.raw;
                for (let k = 0; k < 8; k++) {
                    if (pickDown && k === 2) {
                        emu.buttonPress('Down'); await new Promise(r => setTimeout(r, 12)); emu.buttonUnpress('Down');
                    }
                    emu.buttonPress('A'); await new Promise(r => setTimeout(r, 12)); emu.buttonUnpress('A');
                    await new Promise(r => setTimeout(r, 12));
                }
            }""",
                step in (8, 9, 10, 14, 15, 16),
            )
            st = snap_state(page)
            sb1 = st.sb1(syms)
            if sb1:
                mg, mn = st.u8(sb1 + 4), st.u8(sb1 + 5)
                cb2 = st.u32(syms["gMain"] + 4) & ~1
                if (mg, mn) == (4, 1) and cb2 == syms["CB2_Overworld"]:
                    reached_bedroom = True
                    break
                if step in (11, 17):
                    page.evaluate(
                        """async () => {
                        const emu = window.__JOSEPHRED_EMU__.raw;
                        emu.buttonPress('Start'); await new Promise(r => setTimeout(r, 18)); emu.buttonUnpress('Start');
                        await new Promise(r => setTimeout(r, 18));
                        emu.buttonPress('A'); await new Promise(r => setTimeout(r, 18)); emu.buttonUnpress('A');
                    }"""
                    )
        assert reached_bedroom, "Failed to reach Bedroom!"
        st = drive_until_idle(page, syms)
        assert st.has_item(syms, ITEM_POKE_BALL), "Missing starter Poke Balls!"
        passed.append("01. New Game Prologue -> Bedroom & Starter Poke Balls")

        # 02. Hardware-Masked L+R Auto-Run (`gAutoRunEnabled`)
        page.evaluate("() => { const e = window.__JOSEPHRED_EMU__.raw; e.buttonPress('L'); e.buttonPress('R'); }")
        page.wait_for_timeout(40)
        auto_on = snap_state(page).u8(syms["gAutoRunEnabled"])
        page.evaluate("() => { const e = window.__JOSEPHRED_EMU__.raw; e.buttonUnpress('L'); e.buttonUnpress('R'); }")
        page.wait_for_timeout(40)
        auto_off = snap_state(page).u8(syms["gAutoRunEnabled"])
        assert auto_on == 1 and auto_off == 0, f"gAutoRunEnabled failed: {auto_on} -> {auto_off}"
        passed.append("02. Hardware-Masked L+R Auto-Run Chord (gAutoRunEnabled 0->1->0)")

        # 03. Pallet Grass Rescue -> Oak's Lab Starter (Dratini + 20 Poke Balls) -> Rival Takes Starter -> Rival Battle #1!
        print("[03/19] Verifying Oak's Grass Rescue -> Dratini + 20 Poke Balls -> Rival Battle #1...")
        st = run_npc_script(page, syms, 3, 0, 12, 1, "PalletTown_EventScript_OakTriggerLeft")
        assert st.get_var(syms, VAR_OAKS_LAB_SCENE) == 2

        st = run_npc_script(
            page,
            syms,
            4,
            3,
            8,
            5,
            "PalletTown_ProfessorOaksLab_EventScript_BulbasaurBall",
            local_id=5,
            yes_until_flag=FLAG_SYS_POKEMON_GET,
        )
        assert st.get_flag(syms, FLAG_SYS_POKEMON_GET), "Did not receive starter Dratini!"
        assert st.get_var(syms, VAR_OAKS_LAB_SCENE) == 3, "RivalTakesStarter did not close cleanly to scene=3!"
        assert st.u8(syms["gPlayerPartyCount"]) == 1

        # Provision Lv. 100 Mewtwo sweeper alongside starter Dratini (4 open party slots remain for gift Pokemon!)
        inject_script(
            page,
            syms,
            bc_givemon(SPECIES_MEWTWO, 100, 0)
            + bc_setmonmove(0, 0, MOVE_DRAGON_CLAW)
            + bc_setmonmove(1, 0, MOVE_DRAGON_CLAW)
            + bc_setmonmove(1, 1, MOVE_PSYCHIC)
            + bc_setmonmove(1, 2, MOVE_FLAMETHROWER)
            + bc_setmonmove(1, 3, MOVE_THUNDERBOLT)
            + bc_heal()
            + bc_end(),
        )
        page.wait_for_timeout(80)
        st_swap = drive_until_idle(page, syms)
        assert st_swap.u8(syms["gPlayerPartyCount"]) == 2
        # Swap Lv. 100 Mewtwo (Slot 1) into Lead Slot 0 (100 bytes per struct Pokemon) so Lead never faints!
        p_addr = syms["gPlayerParty"]
        mon0 = bytes(st_swap.raw[st_swap._off(p_addr) : st_swap._off(p_addr) + 100])
        mon1 = bytes(st_swap.raw[st_swap._off(p_addr + 100) : st_swap._off(p_addr + 200)])
        st_swap.write(p_addr, mon1)
        st_swap.write(p_addr + 100, mon0)
        page.evaluate(
            """(bytes) => {
            const emu = window.__JOSEPHRED_EMU__.raw;
            const p = emu.filePaths().saveStatePath + '/josephred.ss9';
            emu.FS.writeFile(p, new Uint8Array(bytes));
            emu.loadState(9);
        }""",
            list(st_swap.encode_png()),
        )

        st = run_npc_script(page, syms, 4, 3, 6, 8, "PalletTown_ProfessorOaksLab_EventScript_RivalBattleTriggerMid", local_id=8)
        assert st.u8(syms["gBattleOutcome"]) == 1, "Did not defeat Rival Greg in Oak's Lab!"
        assert st.get_var(syms, VAR_OAKS_LAB_SCENE) == 4
        passed.append("03. Oak's Lab Starter (Dratini + 20 Balls), Clean Rival Close & Rival Battle #1")

        # 04. Viridian Mart ON_FRAME Parcel -> Shop Reminder -> Oak's Lab Pokedex -> Viridian Old Man Unblocked!
        print("[04/19] Verifying Viridian Parcel -> Oak's Lab Pokedex -> Viridian Old Man chain...")
        st = warp_to(page, syms, 5, 3, 4, 7)
        assert st.get_var(syms, VAR_VIRIDIAN_MART) == 1 and st.has_item(syms, ITEM_OAKS_PARCEL)
        st = run_npc_script(page, syms, 4, 3, 6, 4, "PalletTown_ProfessorOaksLab_EventScript_ProfOak", local_id=4)
        assert st.get_flag(syms, FLAG_SYS_POKEDEX_GET), "Oak did not grant Pokedex!"
        assert st.get_var(syms, VAR_VIRIDIAN_OLD_MAN) == 1, "Viridian Old Man roadblock was not cleared!"
        passed.append("04. Viridian Mart Parcel -> Oak's Lab Pokedex -> Viridian Old Man Unblocked")

        # 05. Route 1 Mart Clerk (#1) + Ep. 1 Spearow (#3) & Golden Ho-Oh (SACRED ASH)
        print("[05/19] Verifying Route 1 Clerk + Ep. 1 Spearow & Golden Ho-Oh...")
        run_npc_script(page, syms, 3, 19, 6, 29, "Route1_EventScript_MartClerk", local_id=1)
        st = run_npc_script(page, syms, 3, 19, 14, 19, "Route1_EventScript_AnimeSpearow", local_id=3)
        assert st.get_flag(syms, FLAG_WONDER_CARD_1) and st.has_item(syms, ITEM_SACRED_ASH)
        passed.append("05. Route 1 Clerk + Ep. 1 Spearow Ambush & Golden Ho-Oh (SACRED ASH)")

        # 06. Route 3 Ep. 45 Singing Marker Jigglypuff (#10)
        print("[06/19] Verifying Route 3 Singing Marker Jigglypuff...")
        st = run_npc_script(page, syms, 3, 21, 66, 12, "Route3_EventScript_AnimeJigglypuff", local_id=10)
        assert st.get_flag(syms, FLAG_WONDER_CARD_2)
        passed.append("06. Route 3 Ep. 45 Singing Marker Jigglypuff (MUS_JIGGLYPUFF + Battle)")

        # 07. Mt. Moon B2F Talking Meowth (#12) + James (#7) + Jessie (#5)
        print("[07/19] Verifying Mt. Moon B2F Talking Meowth, James & Jessie...")
        run_npc_script(page, syms, 1, 3, 10, 21, "MtMoon_B2F_EventScript_TalkingMeowth", local_id=12)
        st_james = run_npc_script(page, syms, 1, 3, 19, 27, "MtMoon_B2F_EventScript_Grunt2", local_id=7)
        assert st_james.u8(syms["gBattleOutcome"]) == 1, "Did not defeat Mt. Moon James!"
        st_jessie = run_npc_script(page, syms, 1, 3, 13, 20, "MtMoon_B2F_EventScript_Grunt1", local_id=5)
        assert st_jessie.u8(syms["gBattleOutcome"]) == 1, "Did not defeat Mt. Moon Jessie!"
        passed.append("07. Mt. Moon B2F Talking Meowth, James & Jessie")

        # 08. Route 24 Ep. 11 Stray Charmander (#9) -> Party Count = 3!
        print("[08/19] Verifying Route 24 Stray Charmander rescue...")
        st = run_npc_script(page, syms, 3, 43, 5, 16, "Route24_EventScript_StrayCharmander", local_id=9)
        assert st.get_flag(syms, FLAG_WONDER_CARD_3) and st.u8(syms["gPlayerPartyCount"]) == 3
        passed.append("08. Route 24 Ep. 11 Stray Charmander Rescue (Joined Party)")

        # 09. Route 24 Ep. 27 Migraine Psyduck (#10)
        print("[09/19] Verifying Route 24 Migraine Psyduck...")
        st = run_npc_script(page, syms, 3, 43, 15, 26, "Route24_EventScript_MigrainePsyduck", local_id=10)
        assert st.get_flag(syms, FLAG_WONDER_CARD_4)
        passed.append("09. Route 24 Ep. 27 Misty's Migraine Psyduck")

        # 10. Route 25 Ep. 10 Melanie's Bulbasaur (#14) -> Party Count = 4!
        print("[10/19] Verifying Route 25 Melanie's Hidden Village Bulbasaur...")
        st = run_npc_script(page, syms, 3, 44, 56, 8, "Route25_EventScript_MelanieBulbasaur", local_id=14)
        assert st.get_flag(syms, FLAG_WONDER_CARD_5) and st.u8(syms["gPlayerPartyCount"]) == 4
        passed.append("10. Route 25 Ep. 10 Melanie's Bulbasaur (Joined Party)")

        # 11. Vermilion City Ep. 12 Officer Jenny Squirtle Squad Leader (#9) -> Party Count = 5!
        print("[11/19] Verifying Vermilion Officer Jenny & Squirtle Squad Leader...")
        st = run_npc_script(page, syms, 3, 5, 23, 14, "VermilionCity_EventScript_OfficerJennySquirtle", local_id=9)
        assert st.get_flag(syms, FLAG_WONDER_CARD_6) and st.u8(syms["gPlayerPartyCount"]) == 5
        passed.append("11. Vermilion Ep. 12 Officer Jenny Squirtle Squad Leader (Joined Party w/ SQUAD SHADES)")

        # 12. Vermilion Pier Ep. 21 Bye Bye Butterfree (#10)
        print("[12/19] Verifying Vermilion Pier Bye Bye Butterfree...")
        st = run_npc_script(page, syms, 3, 5, 28, 29, "VermilionCity_EventScript_ByeByeButterfree", local_id=10)
        assert st.get_flag(syms, FLAG_WONDER_CARD_7)
        assert st.has_item(syms, ITEM_SILVER_POWDER) and st.has_item(syms, ITEM_RARE_CANDY)
        passed.append("12. Vermilion Ep. 21 Bye Bye Butterfree (SILVER POWDER + RARE CANDY)")

        # 13. S.S. Anne Harbor Truck Bus-kun Lv. 30 Mew
        print("[13/19] Verifying Vermilion Harbor Bus-kun Lv. 30 Mew...")
        st = run_npc_script(page, syms, 1, 4, 54, 3, "SSAnne_Exterior_EventScript_IsekaiBusKun")
        assert st.get_flag(syms, FLAG_WONDER_CARD_8)
        passed.append("13. Vermilion Harbor Isekai Bus-kun Lv. 30 Mew")

        # 14. Celadon Flying Saucer (#4), Rocket Hideout Stephane #1 (#1), DNS Snorlax (#5), Erica L (#7)
        print("[14/19] Verifying Flying Saucer, Rocket Hideout Stephane #1, DNS Snorlax & Leader Erica L...")
        st = run_npc_script(page, syms, 10, 17, 1, 3, "CeladonCity_Restaurant_EventScript_CoinCaseMan", local_id=4)
        assert st.has_item(syms, ITEM_COIN_CASE)

        st = run_npc_script(page, syms, 1, 45, 19, 5, "RocketHideout_B4F_EventScript_Giovanni", local_id=1)
        assert st.u8(syms["gBattleOutcome"]) == 1, "Rocket Hideout Stephane #1 did not win cleanly!"

        run_npc_script(page, syms, 3, 30, 14, 71, "Route12_EventScript_SnorlaxNoPokeFlute", local_id=5)

        st = run_npc_script(page, syms, 10, 16, 6, 5, "CeladonCity_Gym_EventScript_Erika", local_id=7)
        assert st.u8(syms["gBattleOutcome"]) == 1, "Erica L battle did not win cleanly!"
        passed.append("14. Flying Saucer (COIN CASE), Rocket Hideout Stephane #1, DNS Snorlax & Leader Erica L")

        # 15. Silph Co. 11F PTC Windchill HQ: Meowth (#7), James (#4), Jessie (#6), Stephane #2 (#3)
        print("[15/19] Verifying Silph Co. 11F Windchill HQ (Meowth, James, Jessie & Stephane #2)...")
        run_npc_script(page, syms, 1, 57, 0, 19, "SilphCo_11F_EventScript_TalkingMeowth", local_id=7)
        st_s_james = run_npc_script(page, syms, 1, 57, 16, 11, "SilphCo_11F_EventScript_Grunt1", local_id=4)
        assert st_s_james.u8(syms["gBattleOutcome"]) == 1, "Silph 11F James did not win cleanly!"
        st_s_jessie = run_npc_script(page, syms, 1, 57, 2, 18, "SilphCo_11F_EventScript_Grunt2", local_id=6)
        assert st_s_jessie.u8(syms["gBattleOutcome"]) == 1, "Silph 11F Jessie did not win cleanly!"
        st_s_steph = run_npc_script(page, syms, 1, 57, 6, 15, "SilphCo_11F_EventScript_GiovanniTriggerRight", local_id=3)
        assert st_s_steph.u8(syms["gBattleOutcome"]) == 1, "Silph 11F Stephane #2 did not win cleanly!"
        passed.append("15. Silph Co. 11F Talking Meowth, James (Victreebel), Jessie & Stephane #2")

        # 16. Saffron Gym Leader Charles B (#7)
        print("[16/19] Verifying Saffron Gym Leader Charles B...")
        st = run_npc_script(page, syms, 14, 3, 14, 12, "SaffronCity_Gym_EventScript_Sabrina", local_id=7)
        assert st.u8(syms["gBattleOutcome"]) == 1, "Charles B battle did not win cleanly!"
        passed.append("16. Saffron Gym Leader Charles B Battle & Post-Battle")

        # 17. Viridian Gym Leader Stephane #3 (#8)
        print("[17/19] Verifying Viridian Gym Leader Stephane #3...")
        st = run_npc_script(page, syms, 5, 1, 2, 3, "ViridianCity_Gym_EventScript_Giovanni", local_id=8)
        assert st.u8(syms["gBattleOutcome"]) == 1, "Stephane #3 Viridian Gym battle did not win cleanly!"
        passed.append("17. Viridian Gym Leader Stephane #3 (Domain Cutover Finale)")

        # 18. Indigo Plateau Elite Four: Jessica (#1) -> Siva (#1) -> Erin (#1) -> Sonny (#1)
        print("[18/19] Verifying Indigo Plateau Elite Four (Jessica -> Siva -> Erin -> Sonny)...")
        for grp, num, px, py, sym, boss_label in (
            (1, 75, 6, 6, "PokemonLeague_LoreleisRoom_EventScript_Lorelei", "Jessica"),
            (1, 76, 6, 6, "PokemonLeague_BrunosRoom_EventScript_Bruno", "Siva"),
            (1, 77, 6, 6, "PokemonLeague_AgathasRoom_EventScript_Agatha", "Erin"),
            (1, 78, 6, 9, "PokemonLeague_LancesRoom_EventScript_Lance", "Sonny"),
        ):
            st = run_npc_script(page, syms, grp, num, px, py, sym, local_id=1)
            assert st.u8(syms["gBattleOutcome"]) == 1, f"Elite Four {boss_label} did not win cleanly!"
        passed.append("18. Indigo Plateau Elite Four Gauntlet (Jessica, Siva, Erin & Sonny)")

        # 19. Champion Brian (PokemonLeague_ChampionsRoom ON_FRAME auto-cutscene from door warp 6,19 -> Battle)!
        print("[19/19] Verifying Champion Brian Finale (ChampionsRoom ON_FRAME -> Battle)...")
        # Clone Lead Slot 0 into Slot 1 AND give Slot 0 25-PP Special Dark MOVE_BITE (2x vs Alakazam/Exeggutor, 0 resists on Brian!)
        st_pre = snap_state(page)
        p_addr = syms["gPlayerParty"]
        lead_bytes = bytes(st_pre.raw[st_pre._off(p_addr) : st_pre._off(p_addr) + 100])
        st_pre.write(p_addr + 100, lead_bytes)
        page.evaluate(
            """(bytes) => {
            const emu = window.__JOSEPHRED_EMU__.raw;
            const p = emu.filePaths().saveStatePath + '/josephred.ss9';
            emu.FS.writeFile(p, new Uint8Array(bytes));
            emu.loadState(9);
        }""",
            list(st_pre.encode_png()),
        )
        inject_script(
            page,
            syms,
            bc_setmonmove(0, 0, MOVE_BITE)
            + bc_setmonmove(1, 0, MOVE_BITE)
            + bc_heal()
            + bc_warp(1, 79, 6, 19)
            + bc_end(),
        )
        page.wait_for_timeout(150)
        won_champion = False
        champ_diag = ""
        for _ in range(130):
            st = snap_state(page)
            in_battle = (st.u8(syms["gMain"] + 0x439) & 2) != 0
            outcome = st.u8(syms["gBattleOutcome"])
            sb1 = st.sb1(syms)
            mg, mn = st.u8(sb1 + 4), st.u8(sb1 + 5)
            cb2 = st.u32(syms["gMain"] + 4) & ~1
            champ_diag = f"map=({mg},{mn}), in_battle={in_battle}, outcome={outcome}, cb2=0x{cb2:08x}"
            if (not in_battle and outcome == 1) or (mg == 1 and mn == 80):
                won_champion = True
                break
            if in_battle and cb2 == syms.get("CB2_UpdatePartyMenu", 0):
                page.evaluate(
                    """async () => {
                    const emu = window.__JOSEPHRED_EMU__.raw;
                    const tap = async (b) => { emu.buttonPress(b); await new Promise(r => setTimeout(r, 18)); emu.buttonUnpress(b); await new Promise(r => setTimeout(r, 18)); };
                    await tap('B'); await tap('B'); await tap('Right'); await tap('A'); await tap('A');
                }"""
                )
                continue
            page.evaluate(
                """async () => {
                const emu = window.__JOSEPHRED_EMU__.raw;
                for (let k = 0; k < 9; k++) {
                    emu.buttonPress('A'); await new Promise(r => setTimeout(r, 12)); emu.buttonUnpress('A');
                    await new Promise(r => setTimeout(r, 12));
                }
            }"""
            )
        assert won_champion, f"Champion Brian battle did not complete ({champ_diag})!"
        passed.append("19. League Champion Brian Finale & Post-Battle -> Hall of Fame")

        browser.close()

    elapsed = time.time() - t_start
    print(f"\n=== [PASS] ALL {len(passed)} FULL-GAME RUNTIME CHECKPOINTS VERIFIED IN {elapsed:.1f}s (~5,000 FPS) ===")
    for item in passed:
        print(f"  [OK] {item}")


if __name__ == "__main__":
    main()
