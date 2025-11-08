# MuteMe Button Control - Implementation Plan

## Project Overview

This document outlines the conversion of the Rust `mutebtn` project to a modern Python implementation using Typer CLI, uv for dependency management, and just for task management.

## Current Status (2025-11-08)

**Stage 1 (Foundation)**: ✅ **100% Complete** (22/22 tasks)
**Stage 2 (Core Functionality)**: ✅ **100% Complete** (16/16 tasks for toggle mode)
**Stage 3 (Advanced Features)**: ⏳ **8% Complete** (2/24 tasks)

**Key Metrics**:
- **Test Coverage**: 90% (215 tests, all passing)
- **Quality Gates**: All passing (0 lint errors, 0 type errors)
- **Spec Compliance**: 100% (all functional requirements met for basic toggle control)

**Current Spec**: `01-spec-basic-toggle-control.md` (Basic Toggle Control) - ✅ Complete

## Analysis Summary

### Original Rust Architecture Analysis

The `mutebtn` Rust project uses a **4-thread architecture** with crossbeam channels:

- **INT thread**: Reads HID interrupts from USB device
- **CTRL thread**: Manages button state machine (toggle/PTT/hybrid modes)
- **AUDIO thread**: Controls PulseAudio mute/unmute operations
- **EXEC thread**: Writes HID reports for LED color control

### Key Features Implemented

- **Device**: MuteMe button (VID: `0x20a0`, PID: `0x42da`) plus Mini variants
- **Operation Modes**: Toggle, Push-to-Talk, Hybrid (double-tap latch)
- **Audio Backend**: PulseAudio only (all/default/selected device targeting)
- **LED Control**: 8 colors + no color, simple byte-based HID reports
- **Configuration**: TOML files with CLI override support
- **UDEV Integration**: Required for device permissions and access

### Identified Limitations

- PulseAudio-only (no PipeWire support)
- No hot-plug/reconnect handling
- No runtime configuration changes
- Basic logging (just `println!`)
- No GUI or tray interface
- Limited device variant support (only main MuteMe device)
- No UDEV rules included in packaging

## High-Level Python Architecture

### Project Structure

```text
muteme-btn-control/
├── pyproject.toml          # uv project configuration
├── justfile                 # task runner recipes
├── src/
│   └── muteme_btn/
│       ├── __init__.py
│       ├── cli.py           # Typer CLI interface
│       ├── config.py        # Configuration management
│       ├── hid/
│       │   ├── __init__.py
│       │   ├── device.py    # HID device communication
│       │   └── events.py    # Device event handling
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── base.py      # Audio backend interface
│       │   ├── pulse.py     # PulseAudio backend
│       │   └── pipewire.py  # PipeWire backend (future)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── state.py     # Button state machine
│       │   └── daemon.py    # Main daemon orchestration
│       └── utils/
│           ├── __init__.py
│           └── logging.py   # Structured logging
├── tests/
├── docs/
└── config/
    ├── muteme.toml.example
    └── udev/99-muteme.rules
```

### Technology Stack

- **CLI Framework**: Typer (modern, type-hint friendly)
- **HID Communication**: `hidapi` Python bindings
- **Audio Control**: `pulsectl` for PulseAudio, D-Bus for PipeWire
- **Configuration**: TOML with `pydantic` for validation
- **Concurrency**: `asyncio` with thread-based HID I/O
- **Logging**: `structlog` for structured, human-readable text logs
- **Testing**: `pytest` with async support
- **Entry Points**: Modern uv console scripts for `uv run muteme-btn-control`

### AI-Friendly Development Features

1. **Extensive Logging**: Structured logs with JSON output for AI parsing
2. **Health Checks**: Built-in status endpoints and diagnostics
3. **Configuration Validation**: Clear error messages and defaults
4. **Modular Design**: Clear separation of concerns for easy modification
5. **Comprehensive Testing**: Unit tests for state machine, integration tests
6. **Task Runner**: `just` recipes for common development tasks
7. **Dependency Management**: `uv` for fast, reliable dependency handling

## Implementation Roadmap

### Stage 1: Foundation - CLI & Testing Infrastructure

#### 1.1 Project Structure & CLI Foundation ✅ Complete

- [x] Configure `uv` project with dependencies ✅
- [x] Set up `justfile` with development recipes (20 recipes)
- [x] Create basic project structure with `src/muteme_btn/`
- [x] Implement basic Typer CLI with `--help`, `--version` commands
- [x] Add basic logging configuration (structlog) with text/JSON formats
- [x] Create basic configuration file handling (pydantic) with validation
- [x] Set up console scripts entry point in `pyproject.toml`
- [x] Create initial README with basic usage instructions

#### 1.2 Testing Infrastructure ✅ Complete

- [x] Create basic test structure (`tests/` directory) - 15 test files
- [x] Add CLI command tests (help, version, basic functionality) - 14 tests
- [x] Add configuration loading tests - 21 tests
- [x] Add logging output tests - 31 tests (`test_utils_logging.py`)
- [x] Set up pytest with coverage reporting - 90% coverage achieved
- [x] Add CLI integration tests using `typer.testing.CliRunner`
- [x] Configure test fixtures for configuration and logging (`conftest.py`)
- [x] Set up CI-ready test commands in justfile (`just test`)
- [x] Add test coverage thresholds and quality gates (85% threshold, 90% achieved)

#### 1.3 Development Tooling ✅ Complete

- [x] Configure ruff for linting and formatting ✅
- [x] Configure ty for type checking ✅
- [x] Add pre-commit hooks with quality checks ✅
- [x] Add UDEV rules template for future device integration (`config/udev/99-muteme.rules`)
- [x] Add just recipe for running all quality checks (`just check`)
- [x] Configure development environment validation

### Stage 2: Device Integration & Core Functionality

#### 2.1 HID Layer ✅ Complete

- [x] Device discovery and connection (`src/muteme_btn/hid/device.py`)
- [x] Support for multiple MuteMe variants (VID/PID combinations)
  - MuteMe: `0x20A0:0x42DA`, `0x20A0:0x42DB`
  - MuteMe Mini: `0x3603:0x0001-0x0004`
- [x] Basic HID event reading (touch/release) (`src/muteme_btn/hid/events.py`)
- [x] LED color control via HID reports (8 colors + no color)
- [x] Device error handling and permission checking

#### 2.2 Audio Layer ✅ Complete

- [x] PulseAudio backend implementation (`src/muteme_btn/audio/pulse.py`)
- [x] Mute/unmute operations (`set_mute_state()`, `is_muted()`)
- [x] Device targeting (all/default/selected) - currently defaults to all/default
- [x] Audio backend interface design (PulseAudioBackend class)

#### 2.3 State Machine ✅ Complete (Toggle Mode)

- [x] Toggle mode implementation (`src/muteme_btn/core/state.py`)
- [ ] Push-to-Talk mode implementation - **Not in current spec** (explicitly excluded)
- [x] Basic event timing and debouncing (debounce_time_ms parameter)
- [x] State synchronization between components (`src/muteme_btn/core/daemon.py`)

#### 2.4 LED Control & Feedback ✅ Complete

- [x] Color mapping and validation (`LEDColor` enum with 8 colors)
- [x] LED feedback for mute status (`src/muteme_btn/core/led_feedback.py`)
- [x] Basic visual effects (red=muted, green=unmuted)

### Stage 3: Advanced Features & Polish

#### 3.1 Advanced Operation Modes

- [ ] Hybrid mode with double-tap detection
- [ ] Configurable timing windows
- [ ] Advanced button state handling

#### 3.2 Multi-Backend Audio Support

- [ ] PipeWire backend via D-Bus
- [ ] Runtime backend detection
- [ ] Backend fallback strategies

#### 3.3 Device Resilience

- [ ] Hot-plug detection and handling
- [ ] Automatic device reconnection
- [ ] Device state recovery

#### 3.4 Runtime Configuration

- [ ] Unix socket for live configuration
- [ ] Configuration change notifications
- [ ] Runtime parameter validation

#### 3.5 Enhanced Monitoring ⏳ Partial (2/4 Complete)

- [x] Structured logging with JSON output (`src/muteme_btn/utils/logging.py`)
- [x] Performance metrics collection (`tests/test_performance.py` with latency measurements)
- [ ] Health check endpoints - **Not implemented**
- [x] Debug mode with verbose output (`--log-level debug`)

#### 3.6 Packaging and Distribution ⏳ Partial (1/4 Complete)

- [ ] systemd service files - **Not implemented**
- [x] udev rules for device permissions (`config/udev/99-muteme.rules`)
- [ ] .deb/.rpm packaging - **Not implemented**
- [ ] Installation scripts - **Partial** (`just install-udev` exists)

## Key Design Decisions

### Concurrency Model

- **Main Thread**: asyncio event loop for coordination
- **HID Thread**: Blocking reads from USB device
- **Audio Operations**: Async calls to PulseAudio/PipeWire
- **Communication**: asyncio Queues between components

### Configuration Strategy

- **Pydantic Models**: Type-safe configuration with validation
- **Multiple Sources**: CLI args → config file → defaults
- **Runtime Changes**: Unix socket for live reconfiguration
- **File Locations**: `./muteme.toml`, `~/.config/muteme/muteme.toml`,
  `/etc/muteme/muteme.toml`

### Error Handling Philosophy

- **Graceful Degradation**: Continue operating if non-critical components fail
- **Structured Errors**: JSON-formatted error details for AI debugging
- **Recovery Logic**: Automatic device reconnection attempts
- **Comprehensive Logging**: Every error logged with context

### Testing Strategy

- **Unit Tests**: State machine logic, configuration validation
- **Integration Tests**: HID device simulation, audio backend mocking
- **End-to-End Tests**: Full workflow with real hardware
- **Performance Tests**: Latency measurements for PTT mode

### Device Variants Supported

Based on official MuteMe documentation:

- **MuteMe**: `20A0:42DA`, `20A0:42DB`
- **MuteMe Mini**: `3603:0001` through `3603:0004`

### UDEV Requirements

Official UDEV rules required for proper device access:

```bash
# Main MuteMe devices
SUBSYSTEM=="usb", ATTRS{idVendor}=="20A0", ATTRS{idProduct}=="42DA",
  MODE="0666", GROUP="plugdev"
KERNEL=="hidraw*", ATTRS{idVendor}=="20A0", ATTRS{idProduct}=="42DA",
  MODE="0666", GROUP="plugdev"

# MuteMe Mini variants
SUBSYSTEM=="usb", ATTRS{idVendor}=="3603", ATTRS{idProduct}=="0001",
  MODE="0666", GROUP="plugdev"
KERNEL=="hidraw*", ATTRS{idVendor}=="3603", ATTRS{idProduct}=="0001",
  MODE="0666", GROUP="plugdev"
# ... additional Mini variants
```

## Dependencies and Libraries

### Core Dependencies

```toml
[project]
name = "muteme-btn-control"
dependencies = [
    "typer",
    "hidapi",
    "pulsectl",
    "pydantic",
    "structlog",
    "toml",
]

[project.scripts]
muteme-btn-control = "muteme_btn.cli:main"
```

### Development Dependencies

```toml
[dev-dependencies]
pytest
pytest-asyncio
pytest-cov
ruff
ty
pre-commit
```

### Optional Dependencies

```toml
[optional-dependencies]
pipewire = ["dbus-next"]
gui = ["PySide6"]
packaging = ["build"]
```

## Pre-commit Configuration

### .pre-commit-config.yaml

```yaml
repos:
  # Basic file checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
      - id: debug-statements

  # Python linting and formatting with ruff
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.4
    hooks:
      - id: ruff          # Linting
        args: [--fix]
      - id: ruff-format   # Formatting

  # Type checking with ty
  - repo: local
    hooks:
      - id: ty
        name: ty check
        entry: uv run ty check
        language: python


  # Security checks
  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.3
    hooks:
      - id: bandit
        args: [-c, pyproject.toml]
        additional_dependencies: ["bandit[toml]"]

# Default language version
default_language_version:
  python: python3.12
```

### Setup Commands

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run hooks on all files
uv run pre-commit run --all-files

# Update hook versions
uv run pre-commit autoupdate

# Remove hooks if needed
uv run pre-commit uninstall
```

## Justfile Recipes

```makefile
# Setup
setup:         # Install dependencies and pre-commit hooks
check:         # Run all quality checks (lint, type, test)
test:          # Run tests with coverage
lint:          # Run linting and formatting
clean:         # Clean build artifacts

# Application
run:           # Run the daemon
run-debug:     # Run with debug logging
status:        # Check daemon status

# Device
install-udev:  # Install UDEV rules for device access
check-device:  # Verify device permissions and connectivity

# Building
build:         # Build package
install:       # Install locally
```

## Configuration Schema

```toml
[main]
mute_on_startup = true  # Optional: mute/unmute on startup
log_level = "info"      # debug, info, warning, error
log_format = "text"     # text, json (text for human readability, json for AI parsing)

[muteme]
muted_color = "red"     # red, green, blue, yellow, cyan, purple, white, nocolor
unmuted_color = "green"
operation_mode = "toggle"  # toggle, pushtotalk, hybrid
double_tap_duration_1 = 300  # ms (hybrid mode)
double_tap_duration_2 = 250  # ms (hybrid mode)
# Device variant selection (optional)
device_variant = "auto"  # auto, muteme, mini

[audio]
backend = "pulseaudio"  # pulseaudio, pipewire, auto
mute_device = "all"     # all, default, selected
unmute_device = "all"   # all, default, selected
selected_device_name = ""  # specific device name

[daemon]
socket_path = "/tmp/muteme.sock"
pid_file = "/tmp/muteme.pid"
user_service = true    # run as user service
# UDEV and device setup
udev_rules = true      # auto-install UDEV rules if possible
device_check = true    # verify device access on startup
```

## Success Criteria

### Stage 1 Success (Foundation) ✅ Complete

- [x] Basic Typer CLI with help and version commands working
- [x] Configuration file loading and validation (pydantic)
- [x] Structured logging setup (structlog) with JSON/text output
- [x] Comprehensive test coverage for CLI and configuration (90% coverage)
- [x] Development tooling configured (ruff, ty, pytest-cov)
- [x] Just recipes for development workflow (20 recipes)
- [x] Project structure ready for device integration

### Stage 2 Success (Core Functionality) ✅ Complete (Toggle Mode)

- [x] Successfully connects to MuteMe button (all variants)
- [x] Toggle mode works correctly ✅ | PTT mode - **Not in spec scope**
- [x] LED colors reflect mute status
- [x] PulseAudio integration with device targeting (default/all)
- [x] Clean shutdown on signals (SIGINT/SIGTERM)
- [x] Basic error handling and device permission checking
- [x] UDEV rules template and device utilities

### Stage 3 Success (Feature Complete) ⏳ Partial (2/8 Complete)

- [x] All original features working (for toggle mode scope)
- [ ] PipeWire support added - **Not in spec** (explicitly excluded)
- [ ] Hot-plug device handling - **Not in spec** (explicitly excluded)
- [ ] Runtime configuration changes - **Not in spec** (explicitly excluded)
- [ ] systemd service integration - **Not implemented**
- [x] Comprehensive test coverage (>90%) - **90% achieved**
- [x] Complete device variant support - **All variants supported**
- [ ] Automated setup and installation scripts - **Partial** (just recipes)

## CLI Testing Patterns

### Modern Typer Testing Approach

```python
# tests/test_cli.py
from typer.testing import CliRunner
from muteme_btn.cli import app

runner = CliRunner()

def test_help_command():
    """Test CLI help output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "MuteMe Button Control" in result.stdout

def test_version_command():
    """Test version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout

def test_config_validation():
    """Test configuration validation."""
    result = runner.invoke(app, ["--config", "invalid.toml"])
    assert result.exit_code != 0
    assert "Invalid configuration" in result.stdout
```

### Simple Development Setup

```bash
# Quick setup (one-time)
just setup

# Development workflow
just check          # Run all quality checks
just run            # Run the application
just test           # Run tests
```

Or manually:

```bash
uv sync && uv run pre-commit install
uv run muteme-btn-control --help
```

### Initial PoC Validation Checklist ✅ All Prerequisites Met

Before starting device integration, ensure:

- [x] CLI `--help` shows proper usage and commands
- [x] CLI `--version` displays correct version (0.1.0)
- [x] Configuration file loads and validates properly
- [x] Logging works in both text and JSON formats
- [x] All tests pass with >80% coverage (90% achieved, 215 tests)
- [x] Pre-commit hooks run successfully
- [x] Project can be installed via `uv pip install -e .`
- [x] Console script `muteme-btn-control` works globally

## Development Methodology

### Strict Test-Driven Development (TDD)

**All development must follow TDD workflow** - no code without tests first.

#### TDD Process

1. **Red**: Write a failing test for the desired functionality
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Improve code while keeping tests green
4. **Repeat**: Continue cycle for each feature

#### TDD Requirements

- **Test First**: Always write tests before implementation code
- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test component interactions
- **CLI Tests**: Test all command-line interface functionality
- **Coverage**: Maintain >90% test coverage throughout development
- **No Exceptions**: No production code without corresponding tests

#### TDD Workflow Examples

```bash
# Feature development cycle
# 1. Write failing test
uv run pytest tests/test_new_feature.py -v  # Should fail

# 2. Implement minimal code
# Edit src/muteme_btn/new_feature.py

# 3. Verify test passes
uv run pytest tests/test_new_feature.py -v  # Should pass

# 4. Refactor if needed
uv run pytest tests/ --cov=muteme_btn  # Maintain coverage
```

## Documentation Maintenance

### Critical for AI-Driven Development

**Documentation must be kept in sync with code changes** - this is essential for autonomous AI development and debugging.

### Documentation Requirements

1. **Update Immediately** - When adding features, update docs in the same PR/commit
2. **API Documentation** - Keep function signatures and examples current
3. **Configuration Changes** - Update configuration schema when adding options
4. **Architecture Decisions** - Document why changes were made
5. **CLI Commands** - Update command examples when adding new flags/subcommands

### Documentation Workflow

```bash
# Before implementing changes
# 1. Read relevant docs to understand current state
# 2. Plan documentation updates alongside code changes

# During development
# 3. Update docs as you implement features
# 4. Keep examples working and tested

# Before committing
# 5. Verify all documentation is accurate
# 6. Test all command examples
# 7. Check configuration schema matches code
```

### Documentation Files to Maintain

- **`IMPLEMENTATION_PLAN.md`** - Project status and roadmap
- **`README.md`** - Installation and usage instructions
- **`docs/`** - Detailed technical documentation
- **Code docstrings** - API documentation for all public functions
- **Configuration examples** - Keep `muteme.toml.example` current

### AI Documentation Standards

- **Clear Examples** - All code examples must be tested and working
- **Version-Specific** - Document version-specific behavior
- **Error Scenarios** - Document common errors and solutions
- **Debugging Info** - Include troubleshooting steps
- **Configuration Mappings** - Show how config options affect behavior

**Remember: Outdated documentation is worse than no documentation for AI development.**

## Development Loop

### Local Development Workflow (TDD)

1. **Write Test** - Create failing test for desired functionality
2. **Run Test** - Verify test fails (Red phase)
3. **Implement Code** - Write minimal code to make test pass (Green phase)
4. **Run Test** - Verify test passes
5. **Refactor** - Improve code while keeping tests green
6. **Run Tests** - Full test suite with coverage
7. **Analyze Output** - Review test results and code quality
8. **Repeat** - Continue TDD cycle for next feature

### Running the Application

#### Foreground (Interactive Development)

```bash
# Run with default settings
uv run muteme-btn-control

# Run with debug logging
uv run muteme-btn-control --log-level debug

# Run with JSON logs for AI analysis
uv run muteme-btn-control --log-format json
```

#### Background (Daemon Mode)

```bash
# Start in background
uv run muteme-btn-control --daemon

# Check if running
uv run muteme-btn-control --status

# Stop the daemon
uv run muteme-btn-control --stop

# Restart with new config
uv run muteme-btn-control --restart
```

### Development Commands

```bash
# Quick test cycle
uv run muteme-btn-control --config test.toml --log-level debug

# Pre-commit quality checks (automatic on commit)
uv run pre-commit run --all-files

# Individual quality tools
uv run ruff check src/
uv run ruff format src/
uv run ty check src/muteme_btn/

# Run specific tests
uv run pytest tests/test_cli.py -v

# Run tests with coverage
uv run pytest --cov=muteme_btn --cov-report=term-missing
```

### Debugging Workflow

1. **Start with verbose logging**: `--log-level debug`
2. **Use JSON format for AI analysis**: `--log-format json`
3. **Check device permissions**: `uv run muteme-btn-control --check-device`
4. **Test configuration**: `uv run muteme-btn-control --validate-config`
5. **Run specific components**: `uv run muteme-btn-control --test-hid` or `--test-audio`

### Background Process Management

The application will handle PID files and process management:

- **PID File**: `/tmp/muteme-btn-control.pid` (configurable)
- **Signal Handling**: Clean shutdown on SIGINT/SIGTERM
- **Status Checking**: Query running daemon state
- **Log Rotation**: Prevent log files from growing too large

## Next Steps

### ✅ Completed

1. ✅ **Stage 1 Foundation** - Complete (22/22 tasks)
2. ✅ **Stage 2 Core Functionality** - Complete for toggle mode (16/16 tasks)
3. ✅ **Spec 01: Basic Toggle Control** - Complete (10/10 functional requirements)

### ⏳ Future Work (Stage 3)

1. **Push-to-Talk Mode** (if added to spec)
   - Extend state machine for PTT logic
   - Add PTT-specific timing and state handling
   - Update configuration schema

2. **Selected Device Targeting**
   - Implement device name selection in audio backend
   - Add device listing CLI command
   - Update configuration schema

3. **Hybrid Mode** (if added to spec)
   - Double-tap detection logic (already partially implemented)
   - Configurable timing windows
   - State machine extensions

4. **PipeWire Support** (if added to spec)
   - Implement PipeWire backend via D-Bus
   - Runtime backend detection
   - Backend fallback strategies

5. **Device Resilience**
   - Hot-plug detection
   - Automatic reconnection
   - Device state recovery

6. **Runtime Configuration**
   - Unix socket for live configuration
   - Configuration change notifications
   - Runtime parameter validation

7. **Packaging**
   - systemd service files
   - .deb/.rpm packaging
   - Installation scripts

---

## Implementation Summary

**Current Status**: ✅ **Production Ready for Basic Toggle Control**

The implementation has successfully completed:
- ✅ **100% of Stage 1** (Foundation)
- ✅ **100% of Stage 2 Core** (for toggle mode scope)
- ✅ **100% of Spec 01** (Basic Toggle Control)

**What's Working**:
- Complete CLI foundation with configuration
- Full HID device communication layer (all MuteMe variants)
- PulseAudio integration with toggle functionality
- LED feedback synchronized with mute status
- Comprehensive test suite (90% coverage, 215 tests)
- All quality gates passing (0 lint errors, 0 type errors)

**What's Deferred** (by design):
- Push-to-Talk mode (explicitly excluded from spec)
- Hybrid mode (explicitly excluded from spec)
- PipeWire support (explicitly excluded from spec)
- Hot-plug handling (explicitly excluded from spec)
- Runtime configuration (explicitly excluded from spec)

---

This plan is designed to be iterative and AI-friendly, with clear milestones and extensive feedback mechanisms at each stage.
