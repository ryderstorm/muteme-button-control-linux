# 03 Validation Report: F19 Hold-to-Talk Mode

## Summary

Automated validation passed for the dual-mode MuteMe implementation. The feature preserves normal toggle behavior, adds a PTT mode that emits synthetic F19 key down/up while held, normalizes noisy HID reports into stable edges, and adds mode-aware LED/config/docs updates.

Manual hardware validation is still recommended before merging to main because LED colors, physical gesture feel, `utter` transcription behavior, and unplug/replug cleanup require the physical MuteMe device and desktop session.

## Automated Proof Artifacts

### Targeted behavior tests

Command:

```bash
uv run pytest tests/test_hid_device.py tests/test_core_state.py tests/test_key_emitter.py tests/test_led_feedback.py tests/test_config.py tests/test_core_daemon.py -q
```

Result:

```text
129 passed in 0.54s
```

Coverage included:

- HID edge normalization for repeated hold reports and noisy release tails
- normal vs. PTT state-machine actions
- double-tap-and-hold mode switching
- synthetic F19 emitter idempotency and cleanup
- daemon PTT action routing and cleanup release
- mode-aware LED rendering
- mode/PTT configuration defaults and validation

### Full project quality gate

Command:

```bash
just check
```

Result:

```text
ruff check: passed
ruff format --check: passed
ty check: passed
pytest: 276 passed
```

### CLI/config smoke check

Command:

```bash
uv run muteme-btn-control --help
uv run python - <<'PY'
from pathlib import Path
from muteme_btn.config import AppConfig
config = AppConfig.from_toml_file(Path('config/muteme.toml.example'))
print(config.mode.default, config.ptt.key, config.ptt.idle_color, config.ptt.active_color)
PY
```

Result:

```text
CLI help rendered successfully
OperationMode.NORMAL f19 blue yellow
```

### Device discovery smoke check

Command:

```bash
uv run muteme-btn-control check-device --verbose
```

Result:

```text
Found 1 MuteMe device
VID:PID: 0x20a0:0x42da
USB Path: 1-1.4.2.4.2:1.0
USB Device Node: /dev/bus/usb/001/017
Permissions: OK
All devices are accessible and ready to use
```

### uinput/F19 emitter smoke check

Command:

```bash
uv run python - <<'PY'
from muteme_btn.input.key_emitter import F19KeyEmitter
emitter = F19KeyEmitter()
emitter._get_device()
emitter.close()
print('uinput F19 emitter initialization OK')
PY
```

Result:

```text
uinput F19 emitter initialization OK
```

Note: this initialized and closed the uinput device without emitting an F19 key press.

## Manual Validation Still Recommended

Run before merging or relying on daily use:

1. Start the daemon in debug mode:

   ```bash
   just run-debug
   ```

2. Confirm normal mode parity:
   - press/release toggles mute exactly once
   - red/green LED feedback still matches mute state

3. Switch modes:
   - quick tap once
   - press again within the double-tap window
   - hold the second press for about 800ms
   - confirm visible mode-switch animation
   - confirm PTT idle LED is blue

4. Confirm true hold-to-talk behavior with `utter`:
   - hold the MuteMe button
   - verify transcription starts only while held
   - release the button
   - verify transcription stops immediately
   - confirm PTT active LED is yellow while held

5. Confirm cleanup safety:
   - stop the daemon while PTT is active
   - unplug/replug the device while PTT is active
   - verify F19 does not remain logically stuck down
   - verify reconnect backoff and LED recovery still work

## Known UX Caveat

The double-tap-and-hold gesture preserves immediate existing behavior, so the first quick tap in normal mode still performs the normal toggle before the hold portion switches modes. This keeps normal mode responsive and avoids deferring every single press, but the physical gesture should be validated to make sure it feels acceptable in daily use.
