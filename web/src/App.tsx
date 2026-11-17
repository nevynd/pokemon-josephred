import React, { useCallback, useEffect, useRef, useState } from 'react';
import mGBA from '@thenick775/mgba-wasm';
import {
  Coffee,
  Download,
  FastForward,
  FolderUp,
  RotateCcw,
  Save,
  Settings,
  Volume2,
  VolumeX,
  X,
} from 'lucide-react';

type EmulatorInstance = Awaited<ReturnType<typeof mGBA>>;
type GBAButton = 'A' | 'B' | 'L' | 'R' | 'Start' | 'Select' | 'Up' | 'Down' | 'Left' | 'Right';

const ROM_URL = '/roms/josephred.gba';
const ROM_FILENAME = 'josephred.gba';
const SPEEDS = [1, 2, 4] as const;

const KEY_TO_GBA: Record<string, GBAButton> = {
  ArrowUp: 'Up',
  KeyW: 'Up',
  ArrowDown: 'Down',
  KeyS: 'Down',
  ArrowLeft: 'Left',
  KeyA: 'Left',
  ArrowRight: 'Right',
  KeyD: 'Right',
  KeyZ: 'A',
  KeyJ: 'A',
  KeyE: 'A', // Familiar WASD interact key
  KeyX: 'B',
  KeyK: 'B',
  KeyC: 'B',
  KeyQ: 'L',
  KeyU: 'L',
  KeyR: 'R',
  KeyI: 'R',
  Enter: 'Start',
  Backspace: 'Select',
  ShiftRight: 'Select',
};

function triggerHaptic(ms = 12): void {
  try {
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      navigator.vibrate(ms);
    }
  } catch (err) {
    console.warn('[JosephRed] Haptic vibration unavailable:', err);
  }
}

export function App() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const emuRef = useRef<EmulatorInstance | null>(null);
  const dpadRef = useRef<HTMLDivElement | null>(null);
  const activeDpadDirsRef = useRef<Set<GBAButton>>(new Set());
  const pressedSetRef = useRef<Set<GBAButton>>(new Set());
  const saveImportInputRef = useRef<HTMLInputElement | null>(null);
  const romImportInputRef = useRef<HTMLInputElement | null>(null);

  const [bootState, setBootState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [bootMessage, setBootMessage] = useState<string>('Booting Pokémon JosephRed...');
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [muted, setMuted] = useState<boolean>(false);
  const [runLock, setRunLock] = useState<boolean>(false);
  const [pressedUI, setPressedUI] = useState<Record<string, boolean>>({});
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [lastSavedLabel, setLastSavedLabel] = useState<string>('SRAM Ready');
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => {
      setToast((curr) => (curr === msg ? null : curr));
    }, 2400);
  }, []);

  const unlockAudioIfNeeded = useCallback(() => {
    const emu = emuRef.current;
    if (!emu || muted) return;
    try {
      const ctx = emu.SDL2?.audioContext;
      if (ctx && ctx.state === 'suspended') {
        void ctx.resume().catch((err: unknown) => {
          console.error('[JosephRed] AudioContext resume error:', err);
        });
      }
      emu.resumeAudio();
    } catch (err) {
      console.error('[JosephRed] Audio unlock error:', err);
    }
  }, [muted]);

  const syncSaveToIndexedDB = useCallback(async (reason: string) => {
    const emu = emuRef.current;
    if (!emu) return;
    try {
      setIsSaving(true);
      await emu.FSSync();
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, '0');
      const mm = String(now.getMinutes()).padStart(2, '0');
      setLastSavedLabel(`Saved ${hh}:${mm}`);
    } catch (err) {
      console.error(`[JosephRed] FSSync failed (${reason}):`, err);
    } finally {
      window.setTimeout(() => setIsSaving(false), 350);
    }
  }, []);

  const pressButton = useCallback(
    (btn: GBAButton, haptic = false) => {
      unlockAudioIfNeeded();
      const emu = emuRef.current;
      if (!emu) return;
      if (!pressedSetRef.current.has(btn)) {
        pressedSetRef.current.add(btn);
        emu.buttonPress(btn);
        setPressedUI((prev) => ({ ...prev, [btn]: true }));
        if (haptic) triggerHaptic(10);
      }
    },
    [unlockAudioIfNeeded],
  );

  const releaseButton = useCallback(
    (btn: GBAButton) => {
      const emu = emuRef.current;
      if (!emu) return;
      if (btn === 'B' && runLock) return;
      if (pressedSetRef.current.has(btn)) {
        pressedSetRef.current.delete(btn);
        emu.buttonUnpress(btn);
        setPressedUI((prev) => ({ ...prev, [btn]: false }));
      }
    },
    [runLock],
  );

  // Initialize mGBA WASM + load josephred.gba
  useEffect(() => {
    let cancelled = false;

    async function boot() {
      if (!canvasRef.current) return;
      try {
        if (!window.crossOriginIsolated) {
          throw new Error(
            'Cross-Origin Isolation (SharedArrayBuffer) is not active. Serve via Vite or node server.mjs.',
          );
        }

        setBootMessage('Initializing GBA SP Core...');
        const emu = await mGBA({ canvas: canvasRef.current });
        if (cancelled) return;

        await emu.FSInit();
        emu.toggleInput(false); // Managed cleanly via React touch & keyboard dispatcher
        emu.setCoreSettings({
          audioSync: false,
          videoSync: true,
          timestepSync: true,
          rewindEnable: false,
          autoSaveStateEnable: false,
          restoreAutoSaveStateOnLoad: false,
          allowOpposingDirections: false,
        });

        emu.addCoreCallbacks({
          saveDataUpdatedCallback: () => {
            void syncSaveToIndexedDB('in-game-sram');
          },
          coreCrashedCallback: () => {
            console.error('[JosephRed] mGBA core reported a crash.');
            setBootState('error');
            setBootMessage('Emulator core crashed. Reload page to resume from SRAM.');
          },
        });

        setBootMessage('Loading Pokémon JosephRed Cartridge...');
        const resp = await fetch(`${ROM_URL}?t=${Date.now()}`, { cache: 'no-store' });
        if (!resp.ok) {
          throw new Error(`Failed to fetch ROM (${resp.status} ${resp.statusText})`);
        }
        const romBytes = new Uint8Array(await resp.arrayBuffer());
        const paths = emu.filePaths();
        const romDest = `${paths.gamePath}/${ROM_FILENAME}`;
        emu.FS.writeFile(romDest, romBytes);

        const loaded = emu.loadGame(romDest);
        if (!loaded) {
          throw new Error('mGBA failed to boot josephred.gba');
        }

        emu.setVolume(1.0);
        emuRef.current = emu;

        // Expose minimal debug hook on window for automated Playwright verification
        (window as unknown as Record<string, unknown>).__JOSEPHRED_EMU__ = {
          press: (b: GBAButton) => pressButton(b, false),
          release: (b: GBAButton) => releaseButton(b),
          setSpeed: (mult: number) => emu.setFastForwardMultiplier(mult),
        };

        setBootState('ready');
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error('[JosephRed] Boot failure:', msg);
        if (!cancelled) {
          setBootState('error');
          setBootMessage(msg);
        }
      }
    }

    void boot();

    return () => {
      cancelled = true;
    };
  }, [pressButton, releaseButton, syncSaveToIndexedDB]);

  // Persist SRAM whenever tab hides or closes
  useEffect(() => {
    const onHide = () => {
      if (document.visibilityState === 'hidden') {
        void syncSaveToIndexedDB('visibility-hidden');
      }
    };
    const onPageHide = () => {
      void syncSaveToIndexedDB('pagehide');
    };
    document.addEventListener('visibilitychange', onHide);
    window.addEventListener('pagehide', onPageHide);
    return () => {
      document.removeEventListener('visibilitychange', onHide);
      window.removeEventListener('pagehide', onPageHide);
    };
  }, [syncSaveToIndexedDB]);

  // Desktop keyboard support
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (drawerOpen) return;
      if (e.code === 'Space') {
        e.preventDefault();
        if (!e.repeat && emuRef.current) {
          emuRef.current.setFastForwardMultiplier(4);
        }
        return;
      }
      const mapped = KEY_TO_GBA[e.code];
      if (mapped) {
        e.preventDefault();
        pressButton(mapped, false);
      }
    };

    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        e.preventDefault();
        if (emuRef.current) {
          emuRef.current.setFastForwardMultiplier(speed);
        }
        return;
      }
      const mapped = KEY_TO_GBA[e.code];
      if (mapped) {
        e.preventDefault();
        releaseButton(mapped);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
    };
  }, [drawerOpen, pressButton, releaseButton, speed]);

  // Cycle 1x -> 2x -> 4x Turbo
  const cycleSpeed = () => {
    unlockAudioIfNeeded();
    const nextIdx = (SPEEDS.indexOf(speed) + 1) % SPEEDS.length;
    const nextSpeed = SPEEDS[nextIdx];
    setSpeed(nextSpeed);
    if (emuRef.current) {
      emuRef.current.setFastForwardMultiplier(nextSpeed);
    }
    triggerHaptic(15);
    showToast(`Speed: ${nextSpeed}×`);
  };

  // Toggle Run Lock (holds B automatically for effortless one-handed sprinting)
  const toggleRunLock = () => {
    unlockAudioIfNeeded();
    const next = !runLock;
    setRunLock(next);
    const emu = emuRef.current;
    if (emu) {
      if (next) {
        pressedSetRef.current.add('B');
        emu.buttonPress('B');
        setPressedUI((prev) => ({ ...prev, B: true }));
      } else {
        pressedSetRef.current.delete('B');
        emu.buttonUnpress('B');
        setPressedUI((prev) => ({ ...prev, B: false }));
      }
    }
    triggerHaptic(15);
    showToast(next ? 'Auto-Run ON (Holding B)' : 'Auto-Run OFF');
  };

  // Toggle Audio Mute
  const toggleMute = () => {
    const emu = emuRef.current;
    const next = !muted;
    setMuted(next);
    if (emu) {
      if (next) {
        emu.setVolume(0);
        emu.pauseAudio();
      } else {
        const ctx = emu.SDL2?.audioContext;
        if (ctx && ctx.state === 'suspended') {
          void ctx.resume().catch((err: unknown) => {
            console.error('[JosephRed] Audio resume failed:', err);
          });
        }
        emu.resumeAudio();
        emu.setVolume(1.0);
      }
    }
    triggerHaptic(12);
  };

  // Smooth thumb-slide D-Pad pointer handler
  const updateDpadFromPointer = (clientX: number, clientY: number) => {
    const el = dpadRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = clientX - cx;
    const dy = clientY - cy;
    const dist = Math.hypot(dx, dy);

    const nextDirs = new Set<GBAButton>();
    if (dist > 12) {
      const angle = Math.atan2(dy, dx) * (180 / Math.PI); // -180..180
      // Allow crisp 4-way + gentle 8-way diagonal cornering
      if (angle >= -150 && angle <= -30) nextDirs.add('Up');
      if (angle >= 30 && angle <= 150) nextDirs.add('Down');
      if (angle >= 120 || angle <= -120) nextDirs.add('Left');
      if (angle >= -60 && angle <= 60) nextDirs.add('Right');
    }

    const prevDirs = activeDpadDirsRef.current;
    for (const oldDir of prevDirs) {
      if (!nextDirs.has(oldDir)) {
        releaseButton(oldDir);
      }
    }
    for (const newDir of nextDirs) {
      if (!prevDirs.has(newDir)) {
        pressButton(newDir, true);
      }
    }
    activeDpadDirsRef.current = nextDirs;
  };

  const clearDpad = () => {
    for (const dir of activeDpadDirsRef.current) {
      releaseButton(dir);
    }
    activeDpadDirsRef.current = new Set();
  };

  // Quick Save / Load State Slots
  const handleSaveSlot = async (slot: number) => {
    const emu = emuRef.current;
    if (!emu) return;
    const ok = emu.saveState(slot);
    if (ok) {
      await syncSaveToIndexedDB(`state-slot-${slot}`);
      showToast(`Saved State Slot ${slot}`);
      setDrawerOpen(false);
    } else {
      showToast(`Failed to save Slot ${slot}`);
    }
  };

  const handleLoadSlot = (slot: number) => {
    const emu = emuRef.current;
    if (!emu) return;
    const ok = emu.loadState(slot);
    if (ok) {
      showToast(`Loaded State Slot ${slot}`);
      setDrawerOpen(false);
    } else {
      showToast(`Slot ${slot} is empty`);
    }
  };

  // Export .sav backup
  const handleExportSav = () => {
    const emu = emuRef.current;
    if (!emu) return;
    try {
      const saveBytes = emu.getSave();
      if (!saveBytes || saveBytes.length === 0) {
        showToast('No in-game save yet — use START > SAVE first!');
        return;
      }
      const copy = new Uint8Array(saveBytes.byteLength);
      copy.set(saveBytes);
      const blob = new Blob([copy], { type: 'application/octet-stream' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'josephred.sav';
      a.click();
      URL.revokeObjectURL(url);
      showToast('Exported josephred.sav');
    } catch (err) {
      console.error('[JosephRed] Export .sav error:', err);
      showToast('Failed to export .sav');
    }
  };

  // Import .sav backup
  const handleImportSavFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    const emu = emuRef.current;
    if (!file || !emu) return;
    const renamed = new File([file], 'josephred.sav', { type: 'application/octet-stream' });
    emu.uploadSaveOrSaveState(renamed, () => {
      void syncSaveToIndexedDB('import-sav').then(() => {
        emu.quickReload();
        showToast('Imported save & reloaded!');
        setDrawerOpen(false);
      });
    });
    e.target.value = '';
  };

  // Optional custom ROM loader from UI (Rule 12)
  const handleImportCustomRom = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    const emu = emuRef.current;
    if (!file || !emu) return;
    emu.uploadRom(file, () => {
      const paths = emu.filePaths();
      const loaded = emu.loadGame(`${paths.gamePath}/${file.name}`);
      if (loaded) {
        showToast(`Loaded ${file.name}`);
        setDrawerOpen(false);
      } else {
        showToast('Invalid GBA ROM file');
      }
    });
    e.target.value = '';
  };

  const makeButtonHandlers = (btn: GBAButton) => ({
    onPointerDown: (e: React.PointerEvent<HTMLButtonElement>) => {
      e.preventDefault();
      e.currentTarget.setPointerCapture(e.pointerId);
      pressButton(btn, true);
    },
    onPointerUp: (e: React.PointerEvent<HTMLButtonElement>) => {
      e.preventDefault();
      releaseButton(btn);
    },
    onPointerCancel: () => releaseButton(btn),
  });

  return (
    <div className="gba-shell-root">
      {toast && <div className="toast-banner">{toast}</div>}

      {/* Upper GBA SP Clamshell Display */}
      <div className="lcd-housing">
        <div className="lcd-top-status">
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <Coffee size={12} color="#f6c453" /> EUR/USD • COFFEE FUELED
          </span>
          <div className="led-cluster">
            <span>{lastSavedLabel}</span>
            <span className={`led-dot ${isSaving ? 'saving' : ''}`} />
          </div>
        </div>

        <div className="lcd-viewport" onPointerDown={unlockAudioIfNeeded}>
          <canvas ref={canvasRef} width={240} height={160} className="gba-canvas" />
          {bootState !== 'ready' && (
            <div className="lcd-overlay">
              <div style={{ fontWeight: 800, fontSize: 14, color: '#f6c453' }}>
                POKéMON JOSEPHRED
              </div>
              <div style={{ fontSize: 12, color: '#d1d5db' }}>{bootMessage}</div>
            </div>
          )}
        </div>

        <div className="lcd-badge-bar">
          <div className="brand-engraving">
            JOSEPH<span>RED</span> SP
          </div>
          <div className="motto-tag">TEAMWORK MAKES THE DREAMWORK</div>
        </div>
      </div>

      {/* Hinge Bar: L + Fast-Forward / RunLock / Save / Mute + R */}
      <div className="hinge-bar">
        <button
          type="button"
          className={`shoulder-btn ${pressedUI.L ? 'pressed' : ''}`}
          {...makeButtonHandlers('L')}
        >
          L
        </button>

        <div className="utility-pills">
          <button
            type="button"
            className={`util-pill ${speed > 1 ? 'active' : ''}`}
            onClick={cycleSpeed}
            title="Toggle 1x / 2x / 4x Turbo Speed"
          >
            <FastForward size={13} />
            {speed}×
          </button>

          <button
            type="button"
            className={`util-pill ${runLock ? 'active' : ''}`}
            onClick={toggleRunLock}
            title="Auto-hold B for Running Shoes"
          >
            RUN
          </button>

          <button
            type="button"
            className="util-pill"
            onClick={() => setDrawerOpen(true)}
            title="Save States & Backup"
          >
            <Save size={13} />
          </button>

          <button
            type="button"
            className={`util-pill ${muted ? 'active' : ''}`}
            onClick={toggleMute}
            title="Toggle Audio"
          >
            {muted ? <VolumeX size={13} /> : <Volume2 size={13} />}
          </button>
        </div>

        <button
          type="button"
          className={`shoulder-btn ${pressedUI.R ? 'pressed' : ''}`}
          {...makeButtonHandlers('R')}
        >
          R
        </button>
      </div>

      {/* Main Tactile Deck: Thumb-Slide D-Pad + Angled B/A */}
      <div className="controls-deck">
        <div
          ref={dpadRef}
          className="dpad-zone"
          onPointerDown={(e) => {
            e.preventDefault();
            e.currentTarget.setPointerCapture(e.pointerId);
            updateDpadFromPointer(e.clientX, e.clientY);
          }}
          onPointerMove={(e) => {
            if (e.buttons === 0 && e.pressure === 0) return;
            updateDpadFromPointer(e.clientX, e.clientY);
          }}
          onPointerUp={clearDpad}
          onPointerCancel={clearDpad}
        >
          <div className="dpad-cross">
            <div className={`dpad-arm dpad-up ${pressedUI.Up ? 'pressed' : ''}`}>▲</div>
            <div className={`dpad-arm dpad-down ${pressedUI.Down ? 'pressed' : ''}`}>▼</div>
            <div className={`dpad-arm dpad-left ${pressedUI.Left ? 'pressed' : ''}`}>◀</div>
            <div className={`dpad-arm dpad-right ${pressedUI.Right ? 'pressed' : ''}`}>▶</div>
            <div className="dpad-center" />
          </div>
        </div>

        <div className="ab-zone">
          <button
            type="button"
            className={`face-btn btn-b ${pressedUI.B ? 'pressed' : ''}`}
            {...makeButtonHandlers('B')}
          >
            B
          </button>
          <button
            type="button"
            className={`face-btn btn-a ${pressedUI.A ? 'pressed' : ''}`}
            {...makeButtonHandlers('A')}
          >
            A
          </button>
        </div>
      </div>

      {/* Start / Select + GBA SP Speaker Grille */}
      <div className="bottom-bar">
        <div className="meta-btns">
          <div className="pill-btn-wrap">
            <button
              type="button"
              aria-label="Select"
              className={`pill-btn ${pressedUI.Select ? 'pressed' : ''}`}
              {...makeButtonHandlers('Select')}
            />
            <span className="pill-label">SELECT</span>
          </div>

          <div className="pill-btn-wrap">
            <button
              type="button"
              aria-label="Start"
              className={`pill-btn ${pressedUI.Start ? 'pressed' : ''}`}
              {...makeButtonHandlers('Start')}
            />
            <span className="pill-label">START</span>
          </div>
        </div>

        <div className="speaker-dots" aria-hidden="true">
          {Array.from({ length: 12 }).map((_, i) => (
            <span key={i} />
          ))}
        </div>
      </div>

      {/* Slide-up Save States & Backup Drawer */}
      {drawerOpen && (
        <div className="drawer-backdrop" onClick={() => setDrawerOpen(false)}>
          <div className="drawer-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div className="drawer-title">
                <Settings size={16} color="#f6c453" />
                JosephRed Save & System Deck
              </div>
              <button
                type="button"
                className="util-pill"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close menu"
              >
                <X size={14} />
              </button>
            </div>

            <div style={{ fontSize: 12, color: '#9ca3af', lineHeight: 1.4 }}>
              In-game <strong>START → SAVE</strong> automatically persists to browser storage. You
              can also snapshot Quick States or export a <code>.sav</code> backup below.
            </div>

            <div className="slot-grid">
              {[1, 2, 3].map((slot) => (
                <div key={slot} className="slot-card">
                  <div className="slot-card-title">Quick Slot {slot}</div>
                  <div className="slot-actions">
                    <button
                      type="button"
                      className="drawer-btn primary"
                      onClick={() => void handleSaveSlot(slot)}
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      className="drawer-btn"
                      onClick={() => handleLoadSlot(slot)}
                    >
                      Load
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="backup-row">
              <button type="button" className="drawer-btn" onClick={handleExportSav}>
                <Download size={14} /> Export .sav
              </button>
              <button
                type="button"
                className="drawer-btn"
                onClick={() => saveImportInputRef.current?.click()}
              >
                <FolderUp size={14} /> Import .sav
              </button>
              <input
                ref={saveImportInputRef}
                type="file"
                accept=".sav,.ss1,.ss2,.ss3"
                style={{ display: 'none' }}
                onChange={handleImportSavFile}
              />
            </div>

            <div className="backup-row">
              <button
                type="button"
                className="drawer-btn"
                onClick={() => {
                  emuRef.current?.quickReload();
                  setDrawerOpen(false);
                  showToast('Soft Reset Cartridge');
                }}
              >
                <RotateCcw size={14} /> Soft Reset
              </button>
              <button
                type="button"
                className="drawer-btn"
                onClick={() => romImportInputRef.current?.click()}
              >
                <FolderUp size={14} /> Load Custom .gba
              </button>
              <input
                ref={romImportInputRef}
                type="file"
                accept=".gba"
                style={{ display: 'none' }}
                onChange={handleImportCustomRom}
              />
            </div>

            <div style={{ fontSize: 11, color: '#6b7280', textAlign: 'center' }}>
              Desktop Keys: Arrows/WASD • Z=A • X=B • Q/E=L/R • Enter=Start • Space=4× Turbo
              <br />
              <em>&ldquo;You may be cool, but are you as cool as Commander Riker sitting down?&rdquo;</em>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
