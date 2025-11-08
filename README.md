# MuteMe Button Control

A Linux CLI tool for controlling MuteMe button hardware with PulseAudio integration. This Python application provides reliable toggle-mode control for microphone mute/unmute operations.

## Features

- **Toggle Mode**: Press the MuteMe button to toggle microphone mute/unmute state
- **PulseAudio Integration**: Seamless integration with PulseAudio for audio control
- **LED Feedback**: Visual LED feedback (red=muted, green=unmuted) synchronized with audio state
- **Modern CLI**: Clean Typer-based command-line interface
- **Configuration**: Flexible TOML-based configuration with validation
- **Structured Logging**: Human-readable text logs or JSON format for machine parsing
- **Device Detection**: Automatic discovery and connection to MuteMe devices

## Requirements

- **Python**: 3.12 or higher
- **Linux**: Tested on Ubuntu/Debian-based systems
- **Hardware**: MuteMe button device (VID:0x20A0, PID:0x42DA)
- **Audio System**: PulseAudio
- **Dependencies**: Managed via `uv` (see `pyproject.toml`)

## Installation

### Prerequisites

1. **Install `uv`** (Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install `just`** (task runner, optional but recommended):
   ```bash
   # Ubuntu/Debian
   sudo apt install just

   # Or via cargo
   cargo install just
   ```

### Quick Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd muteme-btn-control
   ```

2. **Install dependencies and setup**:
   ```bash
   just setup
   ```

   Or manually:
   ```bash
   uv sync
   uv run pre-commit install
   ```

3. **Install UDEV rules** (required for device access):
   ```bash
   just install-udev
   ```

   Or manually:
   ```bash
   sudo cp config/udev/99-muteme.rules /etc/udev/rules.d/99-muteme.rules
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

4. **Verify device connection**:
   ```bash
   just check-device
   ```

## Usage

### Basic Usage

**Run the application**:
```bash
just run
```

Or directly:
```bash
uv run muteme-btn-control
```

**Run with debug logging**:
```bash
just run-debug
```

### CLI Commands

**Show version**:
```bash
uv run muteme-btn-control --version
```

**Check device status**:
```bash
uv run muteme-btn-control check-device
```

**Check device with verbose output**:
```bash
uv run muteme-btn-control check-device --verbose
```

**Show help**:
```bash
uv run muteme-btn-control --help
```

### Configuration

The application supports configuration via TOML files. Copy the example configuration:

```bash
mkdir -p ~/.config/muteme
cp config/muteme.toml.example ~/.config/muteme/muteme.toml
```

Edit `~/.config/muteme/muteme.toml` to customize settings:

```toml
[device]
vid = 8352      # 0x20A0
pid = 17114     # 0x42DA
timeout = 5.0

[audio]
backend = "pulseaudio"
poll_interval = 0.1

[logging]
level = "INFO"
format = "text"  # or "json" for machine parsing
```

Configuration file locations (checked in order):
1. CLI argument: `--config /path/to/config.toml`
2. `~/.config/muteme/muteme.toml`
3. `/etc/muteme/muteme.toml`
4. Default values

## Development

### Development Workflow

**Run all quality checks**:
```bash
just check
```

**Run tests**:
```bash
just test
```

**Run tests with coverage**:
```bash
just coverage
```

**Run linting**:
```bash
just lint
```

**Fix linting issues automatically**:
```bash
just lint-fix
```

**Run type checking**:
```bash
just type-check
```

**Clean build artifacts**:
```bash
just clean
```

### Available Just Recipes

- `just setup` - Install dependencies and pre-commit hooks
- `just check` - Run all quality checks (lint, type, test)
- `just test` - Run tests with coverage
- `just lint` - Run linting and formatting checks
- `just lint-fix` - Auto-fix linting issues
- `just type-check` - Run type checking
- `just coverage` - Show coverage report
- `just coverage-html` - Generate HTML coverage report
- `just run` - Run the application
- `just run-debug` - Run with debug logging
- `just check-device` - Verify device connection
- `just install-udev` - Install UDEV rules
- `just clean` - Clean build artifacts

### Testing

The project follows strict Test-Driven Development (TDD) methodology:

```bash
# Run all tests
just test

# Run specific test file
uv run pytest tests/test_cli.py -v

# Run with coverage
just coverage

# Generate HTML coverage report
just coverage-html
```

Test coverage is maintained above 85% (currently 87%).

## Troubleshooting

### Device Not Found

If `check-device` reports no devices found:

1. **Verify UDEV rules are installed**:
   ```bash
   ls -la /etc/udev/rules.d/99-muteme.rules
   ```

2. **Check device permissions**:
   ```bash
   ls -la /dev/hidraw*
   ```

3. **Reload UDEV rules**:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

4. **Verify device is connected**:
   ```bash
   lsusb | grep -i "20a0:42da"
   ```

### Permission Errors

If you encounter permission errors:

1. **Add user to `plugdev` group**:
   ```bash
   sudo usermod -a -G plugdev $USER
   ```

   Log out and log back in for group changes to take effect.

2. **Verify group membership**:
   ```bash
   groups | grep plugdev
   ```

### Audio Issues

If audio control doesn't work:

1. **Verify PulseAudio is running**:
   ```bash
   pulseaudio --check && echo "Running" || echo "Not running"
   ```

2. **Check PulseAudio sinks**:
   ```bash
   pactl list sinks short
   ```

3. **Test PulseAudio control**:
   ```bash
   pactl set-sink-mute @DEFAULT_SINK@ toggle
   ```

## Project Structure

```
muteme-btn-control/
├── src/muteme_btn/          # Main application code
│   ├── cli.py              # CLI interface
│   ├── config.py           # Configuration models
│   ├── hid/                # HID device communication
│   ├── audio/              # Audio backend (PulseAudio)
│   ├── core/               # Core logic and daemon
│   └── utils/              # Utilities (logging)
├── tests/                  # Test suite
├── config/                 # Configuration files
│   ├── muteme.toml.example # Example configuration
│   └── udev/               # UDEV rules
├── docs/                   # Documentation
├── justfile                # Task runner recipes
└── pyproject.toml          # Project configuration
```

## Contributing

This project follows strict TDD methodology:

1. Write failing tests first
2. Implement minimal code to pass tests
3. Refactor while keeping tests green
4. Maintain >85% test coverage

Before committing:

```bash
just check  # Runs all quality gates
```

## License

[Add license information here]

## Acknowledgments

- Based on the original Rust `mutebtn` project
- Uses modern Python tooling: `uv`, `typer`, `pydantic`, `pytest`
- Built with `just` for consistent development workflows
