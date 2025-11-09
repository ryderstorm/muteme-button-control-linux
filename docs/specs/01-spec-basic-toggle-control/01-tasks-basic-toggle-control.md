# 01-tasks-basic-toggle-control.md

> **Development Pattern Reference**: This implementation follows the strict TDD methodology and development patterns established in [docs/IMPLEMENTATION_PLAN.md](../../../IMPLEMENTATION_PLAN.md), including test-first development, comprehensive logging, and incremental demoable units.

## Tasks

- [x] 1.0 CLI Foundation and Configuration System
  - Demo Criteria: "Run `uv run muteme-btn-control --help` and see complete command structure with version, config validation, and logging options working"
  - Proof Artifact(s): "CLI: `uv run muteme-btn-control --version` outputs '0.1.0'; Test: pytest tests/test_cli.py passes; Config: TOML loading with validation errors"
  - [x] 1.1 Create project structure and basic Typer CLI framework
  - [x] 1.2 Implement configuration models with Pydantic validation
  - [x] 1.3 Add structured logging with text and JSON output formats
  - [x] 1.4 Create comprehensive CLI tests following TDD methodology
  - [x] 1.5 Add configuration loading and validation tests

- [x] 2.0 HID Device Communication Layer
  - Demo Criteria: "Application detects MuteMe device (VID:0x20a0, PID:0x42da) and logs button press events with timestamps"
  - Proof Artifact(s): "Log: device discovery with VID/PID; Test: mocked HID device tests pass; CLI: `--check-device` shows device status"
  - [x] 2.1 Implement HID device discovery and connection logic
  - [x] 2.2 Create button event handling and processing system
  - [x] 2.3 Add LED color control via HID reports
  - [x] 2.4 Implement device error handling and permission checking
  - [x] 2.5 Create mocked HID device tests for CI compatibility
  - [x] 2.6 Add device status checking CLI functionality

- [x] 3.0 Audio Integration and Toggle Logic
  - Demo Criteria: "Button press toggles PulseAudio mute state and changes LED color (red= muted, green=unmuted) with sub-100ms latency"
  - Proof Artifact(s): "Log: audio state changes synchronized with button events; Test: end-to-end toggle workflow passes; Performance: latency measurements <100ms"
  - [x] 3.1 Implement PulseAudio backend with pulsectl integration
  - [x] 3.2 Create button state machine for toggle logic
  - [x] 3.3 Add LED feedback synchronized with mute status
  - [x] 3.4 Implement main daemon orchestration with asyncio
  - [x] 3.5 Add signal handling for graceful shutdown
  - [x] 3.6 Create mocked audio backend tests
  - [x] 3.7 Implement end-to-end integration tests
  - [x] 3.8 Add performance measurement and validation

- [x] 4.0 Task Runner and Development Infrastructure
  - Demo Criteria: "Run `just setup` to install dependencies, `just check` to run quality gates, and `just run` to start the application"
  - Proof Artifact(s): "CLI: `just --help` shows all recipes; Test: `just test` runs with coverage >85%; Quality: `just check` passes all gates"
  - [x] 4.1 Create justfile with development recipes
  - [x] 4.2 Configure pre-commit hooks and quality gates - reference ./docs/IMPLEMENTATION_PLAN.md for tooling
  - [x] 4.3 Set up pytest with coverage reporting
  - [x] 4.4 Add UDEV rules template for device permissions
  - [x] 4.5 Create example configuration file
  - [x] 4.6 Update README with installation and usage instructions

## Relevant Files

### Core Application Files

- `src/muteme_btn/__init__.py` - Package initialization and version information
- `src/muteme_btn/cli.py` - Main Typer CLI interface and command routing (implements spec requirements for modern CLI)
- `src/muteme_btn/config.py` - Configuration models and loading logic using Pydantic validation
- `src/muteme_btn/main.py` - Application entry point for console script

### HID Communication Layer

- `src/muteme_btn/hid/__init__.py` - HID package initialization
- `src/muteme_btn/hid/device.py` - HID device discovery and communication for MuteMe VID:0x20a0, PID:0x42da
- `src/muteme_btn/hid/events.py` - Button event handling and processing with timestamp logging
- `tests/test_hid_device.py` - Mocked HID device tests for CI compatibility
- `tests/test_hid_events.py` - Button event handling tests

### Audio Backend Layer

- `src/muteme_btn/audio/__init__.py` - Audio package initialization
- `src/muteme_btn/audio/pulse.py` - PulseAudio backend implementation using pulsectl
- `tests/test_audio_pulse.py` - Mocked PulseAudio backend tests

### Core Logic and Orchestration

- `src/muteme_btn/core/__init__.py` - Core package initialization
- `src/muteme_btn/core/state.py` - Button state machine and toggle logic
- `src/muteme_btn/core/daemon.py` - Main daemon orchestration with asyncio event loop
- `tests/test_core_state.py` - State machine unit tests
- `tests/test_core_daemon.py` - Daemon orchestration tests

### Utilities and Infrastructure

- `src/muteme_btn/utils/__init__.py` - Utils package initialization
- `src/muteme_btn/utils/logging.py` - Structured logging configuration with text/JSON formats
- `tests/test_utils_logging.py` - Logging configuration tests

### Configuration and Documentation

- `justfile` - Task runner recipes for development workflow (per implementation plan)
- `config/muteme.toml.example` - Example configuration file with all supported options
- `config/udev/99-muteme.rules` - UDEV rules template for device permissions
- `README.md` - Installation and usage instructions

### Test Infrastructure

- `tests/__init__.py` - Test package initialization
- `tests/test_cli.py` - CLI command tests using Typer testing framework
- `tests/test_config.py` - Configuration loading and validation tests
- `tests/conftest.py` - Pytest fixtures and configuration
- `pytest.ini` - Pytest configuration with coverage settings

### Development and Quality Assurance

- `.pre-commit-config.yaml` - Pre-commit hooks for quality gates (already configured)
- `ruff.toml` - Ruff configuration for linting and formatting (extends existing setup)
- `pyproject.toml` - Update with console scripts entry point and test configuration
