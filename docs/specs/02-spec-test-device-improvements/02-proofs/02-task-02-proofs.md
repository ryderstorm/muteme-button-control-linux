# Task 2.0 Proof Artifacts: Add flashing animation brightness level feature

## Implementation Summary

Added flashing animation brightness level feature with 0x40 offset, following existing pattern:

- dim = 0x10
- fast_pulse = 0x20
- slow_pulse = 0x30
- flashing = 0x40 (new)

## Test Results

```bash
pytest tests/test_hid_device.py::TestMuteMeDevice::test_set_led_color_flashing_brightness tests/test_cli_device.py::TestTestDeviceCommand::test_test_device_brightness_sequence_order -v
```

```text
============================= test session starts ==============================
platform linux -- Python 3.12.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /home/damien/personal_projects/muteme-btn-control
configfile: pytest.ini
plugins: asyncio-1.2.0, cov-7.0.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_test_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 2 items

tests/test_hid_device.py::TestMuteMeDevice::test_set_led_color_flashing_brightness PASSED [ 50%]
tests/test_cli_device.py::TestTestDeviceCommand::test_test_device_brightness_sequence_order PASSED [100%]

============================== 2 passed in 0.17s ===============================
```

## Code Changes

### Device Implementation (`src/muteme_btn/hid/device.py`)

Added flashing brightness support in `set_led_color()` method:

```python
elif brightness == "flashing":
    color_value = color.value | 0x40
```

Updated docstring to document flashing option:

```python
brightness: Brightness/effect level:
    - "normal": Base color value (default)
    - "dim": Add 0x10 to color value
    - "fast_pulse": Add 0x20 to color value
    - "slow_pulse": Add 0x30 to color value
    - "flashing": Add 0x40 to color value
```

### CLI Implementation (`src/muteme_btn/cli.py`)

Updated brightness test sequence to include flashing:

```python
brightness_levels = [
    ("Dim", "dim"),
    ("Normal", "normal"),
    ("Flashing", "flashing"),  # Added between Normal and Fast Pulse
    ("Fast Pulse", "fast_pulse"),
    ("Slow Pulse", "slow_pulse"),
]
```

## Test Coverage

Added comprehensive tests:

1. `test_set_led_color_flashing_brightness()` - Tests flashing applies 0x40 offset correctly
2. `test_set_led_color_flashing_brightness_white()` - Tests flashing with white color
3. `test_test_device_brightness_sequence_order()` - Verifies flashing appears in correct position

## Quality Gates

```bash
just check
```

All quality gates pass:

- ✅ Linting (ruff check)
- ✅ Formatting (ruff format)
- ✅ Type checking (ty check)
- ✅ Tests (241 tests pass)

## Demo Criteria Validation

✅ **Flashing in brightness sequence**: Flashing appears between Normal and Fast Pulse
✅ **Code implementation**: `brightness="flashing"` parameter support in `MuteMeDevice.set_led_color()`
✅ **Test coverage**: Comprehensive tests verify flashing works correctly
✅ **0x40 offset**: Implemented following existing pattern
