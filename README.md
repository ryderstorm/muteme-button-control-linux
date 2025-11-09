# MuteMe Button Control

[![CI Status](https://github.com/ryderstorm/muteme-button-control-linux/actions/workflows/ci.yml/badge.svg)](https://github.com/ryderstorm/muteme-button-control-linux/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

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
   brew install uv
   # or
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
   uv run pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg --overwrite
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

| Action | Command |
|--------|---------|
| Run the application | `just run` or `uv run muteme-btn-control` |
| Run with debug logging | `just run-debug` |

### CLI Commands

| Command | Description |
|---------|-------------|
| `uv run muteme-btn-control --version` | Show version information |
| `uv run muteme-btn-control check-device` | Check device status |
| `uv run muteme-btn-control check-device --verbose` | Check device status with detailed output |
| `uv run muteme-btn-control --help` | Show help information |

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development standards and guidelines.

This project uses **Spec-Driven Development (SDD)** methodology, where features are developed through a structured workflow: **idea → specification → tasks → implementation → validation**. Specifications are defined in [`docs/specs/`](docs/specs/) before implementation begins. All code follows **strict Test-Driven Development (TDD)** methodology.

### Quick Start

```bash
just setup    # Install dependencies and pre-commit hooks
just check    # Run all quality checks (lint, type, test)
just test     # Run tests with coverage
```

Run `just` or view the [justfile](./justfile) to see additional recipes.

### Testing & Quality

The project maintains >85% test coverage. All code must pass quality gates:
- **Linting**: Ruff (zero errors/warnings)
- **Type Checking**: ty (zero type errors)
- **Test Coverage**: >85% overall
- **Security**: Bandit (zero high/critical findings)
- **Pre-commit Hooks**: Automatic checks on commit

Run `just check` to verify all quality gates pass.

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

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture and project structure documentation.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development standards, coding guidelines, and workflow instructions.

**Quick checklist**:
- Use Spec-Driven Development (SDD) methodology
- Follow Test-Driven Development (TDD) methodology
- Maintain >85% test coverage
- Run `just check` before committing
- Update documentation alongside code changes
- Follow code style guidelines (ruff formatting)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on the original Rust `mutebtn` project
- Uses modern Python tooling: `uv`, `typer`, `pydantic`, `pytest`
- Built with `just` for consistent development workflows
