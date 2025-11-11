# MuteMe Button Control

<div align="center">

[![CI Status](https://github.com/ryderstorm/muteme-button-control-linux/actions/workflows/ci.yml/badge.svg)](https://github.com/ryderstorm/muteme-button-control-linux/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## A modern Linux CLI tool for controlling MuteMe hardware buttons with seamless PulseAudio integration

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [About](#-about)
- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
  - [Prerequisites](#prerequisites)
  - [Quick Setup](#quick-setup)
- [Usage](#-usage)
  - [Basic Commands](#basic-commands)
  - [Configuration](#configuration)
- [Development](#development)
  - [Quick Start](#quick-start)
  - [Testing & Quality](#testing--quality)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

---

## 🎯 About

**MuteMe Button Control** is a Python-based Linux daemon that provides reliable toggle-mode control for MuteMe hardware buttons. It seamlessly integrates with PulseAudio to manage microphone mute/unmute operations, offering visual LED feedback and a modern command-line interface.

### Key Highlights

- 🎙️ **Hardware Integration**: Direct control of MuteMe button devices via HID
- 🔊 **Audio Control**: Seamless PulseAudio integration for microphone management
- 💡 **Visual Feedback**: LED indicators (red=muted, green=unmuted) synchronized with audio state
- ⚙️ **Flexible Configuration**: TOML-based configuration with validation
- 📊 **Structured Logging**: Human-readable text logs or JSON format for machine parsing
- 🔍 **Device Detection**: Automatic discovery and connection to MuteMe devices

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Toggle Mode** | Press the MuteMe button to toggle microphone mute/unmute state |
| **PulseAudio Integration** | Seamless integration with PulseAudio for audio control |
| **LED Feedback** | Visual LED feedback (red=muted, green=unmuted) synchronized with audio state |
| **Modern CLI** | Clean Typer-based command-line interface |
| **Configuration** | Flexible TOML-based configuration with validation |
| **Structured Logging** | Human-readable text logs or JSON format for machine parsing |
| **Device Detection** | Automatic discovery and connection to MuteMe devices |

---

## 📦 Requirements

- **Operating System**: Linux (tested on Ubuntu/Debian-based systems)
- **Python**: 3.12 or higher
- **Hardware**: MuteMe button device (VID: `0x20A0`, PID: `0x42DA`)
- **Audio System**: PulseAudio
- **Dependencies**: Managed via `uv` (see `pyproject.toml`)

---

## 🚀 Installation

### Prerequisites

#### 1. Install `uv` (Python package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. Install `just` (task runner, optional but recommended)

**Ubuntu/Debian:**

```bash
sudo apt install just
```

**Or via cargo:**

```bash
cargo install just
```

### Quick Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/ryderstorm/muteme-button-control-linux.git
   cd muteme-button-control-linux
   ```

2. **Install dependencies and setup:**

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

4. **Verify device connection:**

   ```bash
   just check-device
   ```

---

## 💻 Usage

### Basic Commands

| Action | Command |
|--------|---------|
| Run the application | `just run` or `uv run muteme-btn-control` |
| Run with debug logging | `just run-debug` |
| Check device status | `uv run muteme-btn-control check-device` |
| Check device (verbose) | `uv run muteme-btn-control check-device --verbose` |
| Show version | `uv run muteme-btn-control --version` |
| Show help | `uv run muteme-btn-control --help` |

### Configuration

The application supports configuration via TOML files. Configuration files are checked in the following order:

1. CLI argument: `--config /path/to/config.toml`
2. `~/.config/muteme/muteme.toml`
3. `/etc/muteme/muteme.toml`
4. Default values

#### Setup Configuration

1. **Create configuration directory:**

   ```bash
   mkdir -p ~/.config/muteme
   ```

2. **Copy example configuration:**

   ```bash
   cp config/muteme.toml.example ~/.config/muteme/muteme.toml
   ```

3. **Edit configuration:**

   ```bash
   nano ~/.config/muteme/muteme.toml
   ```

#### Example Configuration

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

---

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development standards and guidelines.

This project uses **Spec-Driven Development (SDD)** methodology, where features are developed through a structured workflow: **idea → specification → tasks → implementation → validation**. Specifications are defined in [`docs/specs/`](docs/specs/) before implementation begins. All code follows **strict Test-Driven Development (TDD)** methodology.

### Quick Start

```bash
# Install dependencies and pre-commit hooks
just setup

# Run all quality checks (lint, type, test)
just check

# Run tests with coverage
just test
```

Run `just` or view the [justfile](./justfile) to see additional recipes.

### Testing & Quality

The project maintains **>85% test coverage**. All code must pass quality gates:

- ✅ **Linting**: Ruff (zero errors/warnings)
- ✅ **Type Checking**: ty (zero type errors)
- ✅ **Test Coverage**: >85% overall
- ✅ **Security**: Bandit (zero high/critical findings)
- ✅ **Pre-commit Hooks**: Automatic checks on commit

Run `just check` to verify all quality gates pass.

---

## 🔧 Troubleshooting

### Device Not Found

If `check-device` reports no devices found:

1. **Verify UDEV rules are installed:**

   ```bash
   ls -la /etc/udev/rules.d/99-muteme.rules
   ```

2. **Check device permissions:**

   ```bash
   ls -la /dev/hidraw*
   ```

3. **Reload UDEV rules:**

   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

4. **Verify device is connected:**

   ```bash
   lsusb | grep -i "20a0:42da"
   ```

### Permission Errors

If you encounter permission errors:

1. **Add user to `plugdev` group:**

   ```bash
   sudo usermod -a -G plugdev $USER
   ```

   **Note:** Log out and log back in for group changes to take effect.

2. **Verify group membership:**

   ```bash
   groups | grep plugdev
   ```

### Audio Issues

If audio control doesn't work:

1. **Verify PulseAudio is running:**

   ```bash
   pulseaudio --check && echo "Running" || echo "Not running"
   ```

2. **Check PulseAudio sinks:**

   ```bash
   pactl list sinks short
   ```

3. **Test PulseAudio control:**

   ```bash
   pactl set-sink-mute @DEFAULT_SINK@ toggle
   ```

---

## 📁 Project Structure

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture and project structure documentation.

```text
muteme-btn-control/
├── src/muteme_btn/      # Main application source code
├── tests/               # Test suite
├── config/              # Configuration files and examples
├── docs/                # Documentation
│   ├── specs/          # Specification documents (SDD)
│   └── ARCHITECTURE.md  # Architecture documentation
├── .github/             # GitHub workflows and templates
├── justfile             # Task runner recipes
└── pyproject.toml       # Project configuration and dependencies
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development standards, coding guidelines, and workflow instructions.

### Quick Checklist

- ✅ Use Spec-Driven Development (SDD) methodology
- ✅ Follow Test-Driven Development (TDD) methodology
- ✅ Maintain >85% test coverage
- ✅ Run `just check` before committing
- ✅ Update documentation alongside code changes
- ✅ Follow code style guidelines (ruff formatting)

### Development Workflow

1. **Create a specification** in `docs/specs/` before implementing features
2. **Write tests first** following TDD principles
3. **Implement the feature** to make tests pass
4. **Run quality checks** with `just check`
5. **Update documentation** as needed
6. **Submit a pull request** with a clear description

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Based on the original Rust [`mutebtn`](https://github.com/merll/mutebtn) project
- Uses modern Python tooling: `uv`, `typer`, `pydantic`, `pytest`
- Built with `just` for consistent development workflows
- Thanks to all [contributors](https://github.com/ryderstorm/muteme-button-control-linux/graphs/contributors) who help improve this project

---

<div align="center">

**[⬆ Back to Top](#-table-of-contents)**

Made with ❤️ for the Linux community

</div>
