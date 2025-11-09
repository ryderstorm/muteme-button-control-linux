# 01-spec-basic-toggle-control.md

## Introduction/Overview

This specification defines the implementation of a Python-based MuteMe button control application that provides basic toggle functionality for microphone mute/unmute operations. The application will convert the essential features of the original Rust `mutebtn` project to a modern Python implementation using Typer CLI, structured logging, and PulseAudio integration.

## Goals

- Provide reliable toggle-mode control of MuteMe button hardware
- Integrate with PulseAudio for microphone mute/unmute operations
- Deliver a modern CLI interface with comprehensive configuration options
- Establish a robust testing foundation following strict TDD methodology
- Create maintainable code structure for future feature extensions

## User Stories

**As a MuteMe button user**, I want to press the button to toggle my microphone mute state so that I can quickly control audio during calls and meetings.

**As a system administrator**, I want to configure the application through TOML files and CLI overrides so that I can deploy the application across different environments with consistent behavior.

**As a developer**, I want comprehensive test coverage and structured logging so that I can maintain and debug the application effectively.

## Demoable Units of Work

### Unit 1: CLI Foundation and Configuration

**Purpose:** Establish the basic application structure and user interface
**Demo Criteria:** CLI commands respond correctly with help text, version information, and configuration validation
**Proof Artifacts:**

- `uv run muteme-btn-control --help` output showing available commands
- `uv run muteme-btn-control --version` displaying version 0.1.0
- Configuration file loading with validation errors for invalid TOML

### Unit 2: HID Device Communication

**Purpose:** Enable basic communication with the MuteMe button hardware
**Demo Criteria:** Application successfully detects, connects to, and receives button press events from the MuteMe device
**Proof Artifacts:**

- Device discovery log showing VID:0x20a0, PID:0x42da detection
- Button press event logs with timestamps
- LED color change confirmation on device interaction

> **Note**: This unit requires manual testing with physical MuteMe hardware - automated tests will use mocked device interfaces

### Unit 3: Audio Integration and Toggle Logic

**Purpose:** Implement the core mute/unmute functionality with PulseAudio
**Demo Criteria:** Button presses successfully toggle microphone mute state with LED feedback reflecting current status
**Proof Artifacts:**

- PulseAudio mute state changes logged on button press
- LED color changes (red for muted, green for unmuted) synchronized with audio state
- End-to-end demo showing button press → audio mute → LED red → button press → audio unmute → LED green

## Functional Requirements

1. **The system shall** discover MuteMe devices using USB VID:0x20a0 and PID:0x42da
2. **The system shall** establish HID communication with discovered devices
3. **The system shall** monitor button press events from the device
4. **The system shall** toggle PulseAudio microphone mute state on button press
5. **The system shall** control device LED colors to reflect current mute status
6. **The system shall** load configuration from TOML files with CLI override capability
7. **The system shall** provide structured logging in both text and JSON formats
8. **The system shall** handle device disconnection gracefully with error logging
9. **The system shall** validate configuration parameters on startup
10. **The system shall** support daemon mode operation with proper signal handling

## Non-Goals (Out of Scope)

1. **Push-to-Talk mode**: Only toggle mode will be implemented in this specification
2. **Hybrid mode with double-tap detection**: Advanced timing modes are excluded
3. **MuteMe Mini device support**: Only main MuteMe device variant will be supported
4. **PipeWire audio backend**: Only PulseAudio integration will be implemented
5. **Hot-plug device handling**: Device must be connected at application startup
6. **Runtime configuration changes**: Configuration is loaded once at startup
7. **GUI or tray interface**: CLI-only implementation
8. **systemd service integration**: Basic daemon mode without system service files

## Design Considerations

### User Interface Requirements

- **CLI Framework**: Typer with modern subcommand structure
- **Help System**: Comprehensive help text with examples for all commands
- **Error Messages**: Human-readable errors with suggested fixes
- **Progress Indicators**: Verbose logging for device discovery and connection

### Technical Constraints

- **Python Version**: Requires Python 3.12+ for modern type annotations
- **HID Communication**: Uses hidapi library for USB device access
- **Audio Backend**: PulseAudio integration via pulsectl library
- **Configuration**: TOML format with Pydantic validation
- **Concurrency**: asyncio with thread-based HID I/O for blocking operations

### Dependencies and Integration

- **Device Access**: Requires proper UDEV rules for USB device permissions
- **Audio System**: Depends on PulseAudio server availability
- **System Integration**: Standard Unix signal handling for graceful shutdown
- **File System**: Read access to configuration files, write access to log files

### Performance Requirements

- **Button Response**: Sub-100ms latency from button press to audio state change
- **CPU Usage**: <1% CPU usage during idle monitoring
- **Memory Footprint**: <50MB RSS during normal operation
- **Startup Time**: <2 seconds from launch to ready state

## Technical Architecture

### Component Structure

```text
src/muteme_btn/
├── cli.py           # Typer CLI interface and command routing
├── config.py        # Configuration models and loading logic
├── hid/
│   ├── device.py    # HID device discovery and communication
│   └── events.py    # Button event handling and processing
├── audio/
│   └── pulse.py     # PulseAudio backend implementation
├── core/
│   ├── state.py     # Button state machine and toggle logic
│   └── daemon.py    # Main application orchestration
└── utils/
    └── logging.py   # Structured logging configuration

justfile              # Task runner recipes for development workflow
```

### Task Runner Integration

The project uses `just` as the primary task runner for development operations:

```makefile
# Setup and development
setup                 # Install dependencies and pre-commit hooks
check                 # Run all quality checks (lint, type, test)
test                  # Run tests with coverage reporting
lint                  # Run linting and formatting
clean                 # Clean build artifacts

# Application execution
run                   # Run the daemon in foreground
run-debug             # Run with debug logging enabled
status                # Check daemon status
stop                  # Stop running daemon

# Device management
install-udev          # Install UDEV rules for device access
check-device          # Verify device permissions and connectivity
```

**Task Runner Benefits:**

- Consistent development commands across environments
- Automated quality gate execution
- Simplified testing and validation workflows
- Device setup and permission management

### Data Flow

1. **Device Discovery**: HID layer scans for MuteMe devices
2. **Event Loop**: Main asyncio loop coordinates component communication
3. **Button Input**: HID thread captures button press events
4. **State Processing**: Core state machine updates mute status
5. **Audio Control**: PulseAudio backend applies mute/unmute changes
6. **LED Feedback**: HID layer updates device LED colors
7. **Logging**: All operations logged with structured context

### Concurrency Model

- **Main Thread**: asyncio event loop for coordination
- **HID Thread**: Blocking reads from USB device via hidapi
- **Communication**: asyncio Queues between HID and main threads
- **Audio Operations**: Synchronous PulseAudio calls in main thread

## Configuration Schema

```toml
[main]
mute_on_startup = true    # Optional: mute state on application start
log_level = "info"        # debug, info, warning, error
log_format = "text"       # text, json (text for humans, json for AI)

[muteme]
muted_color = "red"       # LED color when muted
unmuted_color = "green"   # LED color when unmuted
operation_mode = "toggle" # Fixed to toggle for this spec

[audio]
backend = "pulseaudio"    # Fixed to pulseaudio for this spec
mute_device = "all"       # all, default, selected
unmute_device = "all"     # all, default, selected
selected_device_name = "" # Specific device name if using "selected"

[daemon]
socket_path = "/tmp/muteme.sock"  # Unix socket for future features
pid_file = "/tmp/muteme.pid"       # PID file for daemon mode
```

## Success Criteria

### Functional Success

- [ ] CLI commands execute without errors
- [ ] MuteMe device is detected and connected successfully
- [ ] Button presses toggle microphone mute state
- [ ] LED colors reflect current mute status accurately
- [ ] Configuration files load and validate properly
- [ ] Application runs in both foreground and daemon modes
- [ ] Graceful shutdown on SIGINT/SIGTERM signals

### Quality Success

- [ ] greater than 85% test coverage maintained throughout development
- [ ] All tests pass before any code commit
- [ ] Pre-commit hooks run without failures
- [ ] Structured logs provide useful debugging information
- [ ] Error handling covers all failure scenarios
- [ ] Code follows Python type hints and formatting standards

### Performance Success

- [ ] Button press to audio mute latency <100ms
- [ ] Application startup time <2 seconds
- [ ] CPU usage <1% during idle operation
- [ ] Memory usage <50MB during normal operation
- [ ] No memory leaks during extended operation

## Testing Strategy

### Unit Tests

- **Configuration Loading**: Test TOML parsing and Pydantic validation
- **CLI Commands**: Test all command-line interface functionality
- **State Machine**: Test toggle logic and state transitions
- **LED Control**: Test color mapping and HID report generation
- **Logging**: Test structured log output in different formats

### Integration Tests

- **HID Device**: Mock device communication for testing without hardware
- **PulseAudio**: Mock audio backend for reliable CI testing
- **End-to-End**: Test complete button press to audio change workflow
- **Error Handling**: Test device disconnection and permission errors

### Test-Driven Development Requirements

- **Test First**: All production code must have corresponding failing tests written first
- **Red-Green-Refactor**: Follow strict TDD cycle for all features
- **Coverage**: Maintain >90% test coverage throughout development
- **CI Ready**: All tests must pass in headless environments

## Proof of Completion

### Demonstration Artifacts

1. **CLI Help Output**: `uv run muteme-btn-control --help` showing complete command structure
2. **Device Detection**: Log output showing successful MuteMe device discovery
3. **Button Response**: Video or logs showing button press → mute toggle → LED change
4. **Configuration**: Example TOML file with all supported options
5. **Test Results**: pytest coverage report showing >90% coverage
6. **Error Handling**: Logs demonstrating graceful error recovery

### Validation Commands

```bash
# Task runner functionality
just                           # Show available recipes
just setup                     # Install dependencies and hooks
just check                     # Run all quality gates

# CLI functionality
uv run muteme-btn-control --help
uv run muteme-btn-control --version
uv run muteme-btn-control --validate-config

# Device interaction
uv run muteme-btn-control --check-device
uv run muteme-btn-control --log-level debug

# Testing and quality
just test                      # Run tests with coverage
just lint                      # Run linting and formatting
```

This specification provides a clear, actionable foundation for implementing basic MuteMe button toggle functionality while establishing robust development practices for future enhancements.
