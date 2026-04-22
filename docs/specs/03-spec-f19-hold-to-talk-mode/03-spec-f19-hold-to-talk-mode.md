# 03-spec-f19-hold-to-talk-mode.md

## Introduction/Overview

This specification defines a new dual-mode interaction model for the MuteMe button controller. The existing normal mode must keep the current toggle behavior unchanged. The new Push-to-Talk (PTT) mode must act as true hold-to-talk for the user's already-working `utter` workflow by emulating F19 key down on button press and F19 key up on button release.

This specification is intentionally scoped as a narrow extension of the current daemon rather than a broad redesign. It prioritizes preserving the current stable behavior while adding a second mode with clear visual feedback and low-friction switching.

A key implementation constraint discovered from live logs is that the MuteMe HID device does not emit a single clean press and release pair for a hold. Instead, it emits repeated press frames during a hold and multiple release-like packets during release. The implementation therefore must normalize raw HID reports into stable semantic edges before adding any PTT behavior.

## Goals

- Preserve the current normal toggle-mode behavior exactly as it works today
- Add a real hold-to-talk PTT mode that emits synthetic F19 down/up events rather than toggling audio directly
- Reuse the user's proven `Scroll Lock -> F19 -> utter` workflow rather than introducing a new app-level integration path
- Provide a deliberate, low-accident mode-switch gesture
- Provide clear LED feedback for normal mode, PTT idle, PTT active, and successful mode switches
- Ensure cleanup paths cannot leave F19 logically stuck down during shutdown, disconnect, reconnect, or mode changes

## User Stories

**As a MuteMe button user**, I want my current button behavior to remain unchanged in normal mode so I do not lose the reliable mute-toggle workflow I already use.

**As a user of `utter` push-to-talk**, I want the MuteMe button to act as a real hold-to-talk trigger so that transcription only happens while I am physically holding the button.

**As a user switching between workflows**, I want an easy but deliberate way to move between normal mode and PTT mode so I can adapt quickly without accidental mode flips.

**As a developer maintaining the daemon**, I want noisy HID reports normalized into stable button edges so PTT and gesture logic are reliable and testable.

**As a developer**, I want cleanup behavior to force F19 release on failure and shutdown paths so the system cannot get stuck in an active-talk state.

## Demoable Units of Work

### Unit 1: HID Edge Normalization

**Purpose:** Convert noisy raw MuteMe HID reports into stable semantic button transitions suitable for mode-aware logic.

**Demo Criteria:**

- A held button produces one logical press-start edge, not repeated press actions
- A release produces one logical release edge, even if the raw HID sequence contains extra release-like packets
- The normalization behavior is covered by tests modeled on the observed device log behavior

**Proof Artifacts:**

- `pytest tests/test_hid_device.py -v` showing coverage for repeated `0x01` hold frames and noisy release tails
- Code review of `src/muteme_btn/hid/device.py` showing stateful edge normalization rather than one-event-per-read behavior
- Debug log output showing reduced button-event spam during a long hold

### Unit 2: Dual-Mode Action Model

**Purpose:** Preserve current toggle behavior in normal mode while introducing true hold-to-talk behavior in PTT mode.

**Demo Criteria:**

- Normal mode still toggles PulseAudio mute exactly once per intentional press/release cycle
- PTT mode emits one logical talk-start action on press and one talk-stop action on release
- No duplicate PTT actions are emitted from repeated held-report traffic

**Proof Artifacts:**

- `pytest tests/test_core_state.py -v`
- `pytest tests/test_core_daemon.py -v`
- Code review showing explicit mode and action handling in `src/muteme_btn/core/state.py` and `src/muteme_btn/core/daemon.py`

### Unit 3: F19 Hold-to-Talk Emulation

**Purpose:** Integrate PTT mode with the user's working `utter` setup by emitting synthetic F19 key down/up events.

**Demo Criteria:**

- Pressing and holding the MuteMe button in PTT mode emits F19 key down once
- Releasing the button emits F19 key up once
- Cleanup paths force key release if shutdown or disconnect occurs while active

**Proof Artifacts:**

- Unit tests for the key-emitter abstraction and daemon cleanup behavior
- Manual validation showing transcription only occurs while the button is held
- Manual validation showing no stuck F19 state after daemon stop or device disconnect

### Unit 4: Mode Switching and LED Feedback

**Purpose:** Make mode changes deliberate and visible without requiring a separate GUI.

**Demo Criteria:**

- Double-tap-and-hold switches modes reliably without frequent accidental activation
- Normal mode continues using current mute-status LED feedback
- PTT idle and PTT active states use distinct colors
- Successful mode changes trigger a short confirmation animation

**Proof Artifacts:**

- `pytest tests/test_led_feedback.py -v`
- State-machine tests covering the mode-switch gesture
- Manual LED verification on hardware showing normal mode, PTT idle, PTT active, and switch confirmation states

## Functional Requirements

### Mode and Behavior Requirements

1. **The system shall** preserve the current normal mode behavior as the default operating mode unless configuration explicitly selects otherwise.
2. **The system shall** toggle PulseAudio mute state in normal mode using the current press/release behavior.
3. **The system shall** add a PTT operating mode that performs hold-to-talk behavior rather than toggle behavior.
4. **The system shall** emit synthetic F19 key down when the button is pressed in PTT mode.
5. **The system shall** emit synthetic F19 key up when the button is released in PTT mode.
6. **The system shall not** toggle PulseAudio mute state directly while in PTT mode.
7. **The system shall** prevent duplicate F19 key down or key up emission from repeated raw HID frames.
8. **The system shall** force synthetic key release during shutdown, disconnect, reconnect failure, or mode switch away from PTT when a synthetic key is logically down.

### HID Normalization Requirements

1. **The system shall** normalize noisy raw MuteMe HID reports into stable semantic button transitions before state-machine action handling.
2. **The system shall** treat repeated press frames during a hold as one logical press-start event.
3. **The system shall** treat noisy release tails as one logical release event.
4. **The system shall** ignore steady-state duplicate button frames that would otherwise create duplicate toggle or PTT actions.
5. **The system shall** retain sufficient debug logging for troubleshooting while avoiding tight-loop hold spam in normal operation.

### Mode-Switch Requirements

1. **The system shall** support a deliberate gesture for switching between normal mode and PTT mode.
2. **The system shall** use double-tap-and-hold as the initial mode-switch gesture.
3. **The system shall** require the second tap to be held past a configurable threshold before switching modes.
4. **The system shall** avoid switching modes on ordinary single taps or common short-tap usage.
5. **The system shall** expose timing thresholds for mode switching through configuration.

### LED Feedback Requirements

1. **The system shall** preserve the current mute-status LED behavior in normal mode.
2. **The system shall** display a distinct PTT idle LED state when PTT mode is active but the button is not currently held.
3. **The system shall** display a distinct PTT active LED state while the button is currently held in PTT mode.
4. **The system shall** display a short confirmation animation when the operating mode changes.
5. **The system shall** continue to deduplicate LED writes where practical to avoid unnecessary device chatter.

### Configuration and Observability Requirements

1. **The system shall** support configuration for default operating mode.
2. **The system shall** support configuration for the double-tap timeout and the hold threshold used for mode switching.
3. **The system shall** support configuration or code-level defaults for PTT idle and active LED colors.
4. **The system shall** provide enough runtime observability to determine the current mode during troubleshooting.

## Non-Goals (Out of Scope)

1. **Direct app-specific integrations beyond F19 emulation**: This spec reuses the existing F19/`utter` workflow instead of adding app-specific APIs.
2. **Direct audio-control PTT**: PTT mode will not directly unmute/remute PulseAudio in the first implementation.
3. **GUI or tray application**: Mode switching and feedback remain daemon/CLI/LED-based.
4. **Per-application automatic mode switching**: The initial implementation uses explicit switching only.
5. **Cross-platform key injection support**: This specification is Linux-specific.
6. **Persistent multi-profile UX**: A single default mode plus runtime switching is sufficient for the initial implementation.
7. **Broad input subsystem refactoring beyond what is needed for stable edges and PTT support**.

## Design Considerations

### Why F19 Emulation Is the Preferred PTT Path

The user already has a working push-to-talk setup using:

- physical key: `Scroll Lock`
- `keyd`: `scrolllock = f19`
- `utter`: watch `--key f19`

Because that path already works well, the narrowest and safest implementation is for PTT mode to emulate the same logical F19 press/release behavior instead of introducing direct application or direct audio-control logic. This minimizes blast radius, preserves compatibility with the current workflow, and keeps rollback simple.

### HID Input Realities

The live touch-test log demonstrates that the hardware input stream is not a clean edge stream:

- repeated `0x01` frames occur while held
- release sequences include `0x04`, `0x02`, and `0x00` packets
- the current implementation treats any non-`0x01` report as release, which is sufficient for naive toggle but too fragile for PTT

The architecture therefore must separate:

1. raw HID report reading
2. semantic edge normalization
3. mode-aware action interpretation
4. execution of audio, key-emitter, and LED effects

### Mode Switch UX

The preferred initial gesture is double-tap-and-hold because it balances speed and safety:

- faster than triple-tap
- less accident-prone than plain double-tap
- does not require a new GUI or external control surface

Recommended thresholds:

- double-tap window: roughly current double-tap semantics or a configurable equivalent
- second-hold confirmation threshold: approximately 700-1000ms, configurable

### LED Feedback Model

Recommended initial LED meanings:

- normal mode muted: existing muted color
- normal mode unmuted: existing unmuted color
- PTT idle: blue
- PTT active: yellow
- mode-switch success: short animation using existing LED effect support

A hardware validation step is required because the current `LEDColor` enum contains comments indicating historical color-swapping quirks on the device.

## Technical Architecture

### Proposed Component Additions

```text
src/muteme_btn/
├── config.py
├── hid/
│   └── device.py            # raw HID reads + semantic edge normalization
├── core/
│   ├── state.py             # mode-aware state machine / gesture logic
│   ├── daemon.py            # action execution, cleanup, orchestration
│   └── led_feedback.py      # mode-aware LED rendering
└── input/
    ├── __init__.py
    └── key_emitter.py       # synthetic F19 key down/up abstraction
```

### Data Flow

1. `hid/device.py` reads raw HID reports from the MuteMe button.
2. The HID layer normalizes raw reports into stable button edges.
3. `core/state.py` interprets edges according to the current operating mode and gesture windows.
4. `core/daemon.py` executes resulting actions:
   - normal toggle -> PulseAudio mute state change
   - PTT press/release -> F19 key down/up
   - mode switch -> mode update and LED confirmation
5. `core/led_feedback.py` renders the appropriate LED presentation for the current mode and activity state.
6. Cleanup paths in the daemon guarantee a synthetic key-up if any failure path occurs mid-hold.

## Configuration Schema

The exact final schema can evolve, but the implementation shall support configuration equivalent to:

```toml
[mode]
default = "normal"          # normal | ptt
switch_gesture = "double_tap_hold"
double_tap_timeout_ms = 300
switch_hold_threshold_ms = 800

[ptt]
key = "f19"
idle_color = "blue"
active_color = "yellow"

[normal]
muted_color = "red"
unmuted_color = "green"
```

## Success Criteria

### Functional Success

- [ ] Normal mode remains behaviorally identical to the current toggle workflow
- [ ] PTT mode emits one F19 key down on press and one F19 key up on release
- [ ] Transcription only occurs while the button is physically held in PTT mode
- [ ] Double-tap-and-hold switches modes reliably
- [ ] LED feedback makes the current mode obvious enough to avoid confusion
- [ ] Cleanup paths prevent stuck F19 state after shutdown, disconnect, or mode changes

### Quality Success

- [ ] HID normalization behavior is covered by tests based on observed live device patterns
- [ ] State-machine logic is covered by unit tests for both modes and gesture timing
- [ ] Daemon integration tests cover cleanup and duplicate-action prevention
- [ ] Documentation reflects the new dual-mode behavior clearly
- [ ] `just check` passes after implementation

### UX Success

- [ ] The user can switch modes quickly without needing a separate GUI
- [ ] The user can tell whether PTT mode is active at a glance
- [ ] Accidental mode switches are rare during normal use
- [ ] PTT mode feels responsive and reliable enough for daily dictation/transcription use

## Testing Strategy

### Unit Tests

- **HID normalization tests**: repeated hold frames, noisy release sequences, stray initial packets
- **State-machine tests**: normal toggle mode, PTT mode, double-tap-and-hold gesture detection, threshold boundaries
- **Key-emitter tests**: synthetic press/release abstraction behavior with mocked backend
- **LED tests**: mode-aware rendering and deduplicated writes

### Integration Tests

- **Daemon action routing**: mode-aware action execution and cleanup behavior
- **Disconnect/reconnect handling**: forced key release and LED recovery behavior
- **Configuration loading**: mode defaults and timing threshold validation

### Manual Validation

- Run daemon in debug mode
- Verify normal mode remains unchanged
- Switch into PTT mode with double-tap-and-hold
- Hold button and confirm transcription works only while held
- Release button and confirm transcription stops immediately
- Stress test rapid taps, long holds, disconnects, and daemon shutdown during active PTT

## Risks and Mitigations

### Risk: Noisy HID stream causes duplicate PTT actions

**Mitigation:** Normalize raw HID reports into stable edges before state-machine handling.

### Risk: Synthetic F19 gets stuck down during failure paths

**Mitigation:** Centralize cleanup and force key release during shutdown, disconnect, reconnect failure, and mode transitions.

### Risk: Mode switch gesture is too easy or too hard to trigger

**Mitigation:** Use configurable timing thresholds and start with the safer double-tap-and-hold interaction.

### Risk: LED colors are not visually what the enum names suggest on real hardware

**Mitigation:** Validate the chosen colors manually on device and allow configuration overrides if necessary.

### Risk: Linux key injection adds dependency or permission complexity

**Mitigation:** Isolate key injection behind a narrow adapter and keep the rest of the daemon independent of implementation details.

## Dependencies and Integration Notes

- The daemon remains Linux-specific.
- PTT behavior depends on a reliable synthetic key injection mechanism, likely via a Python-native Linux approach.
- The implementation should prefer a narrow adapter abstraction so backend selection does not leak into the daemon.
- This spec intentionally does not require changes to the user's existing `keyd` and `utter` setup beyond continuing to use F19 as the logical PTT trigger.

## Proof of Completion

### Required Proof Artifacts

- `pytest tests/test_hid_device.py -v`
- `pytest tests/test_core_state.py -v`
- `pytest tests/test_core_daemon.py -v`
- `pytest tests/test_led_feedback.py -v`
- `just check`
- Manual validation notes demonstrating:
  - normal mode parity
  - successful switch to PTT mode
  - transcription only while held
  - no stuck F19 after cleanup paths

### Reviewer Checklist

- Does the spec preserve existing behavior while clearly defining the new dual-mode scope?
- Does it explicitly account for the noisy HID behavior observed in the live log?
- Does it define PTT as true hold-to-talk rather than toggle semantics?
- Does it define safe cleanup requirements for synthetic key state?
- Does it keep scope narrow by reusing the proven F19/`utter` workflow?
