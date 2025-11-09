# 02-spec-test-device-improvements.md

## Introduction/Overview

This specification defines improvements to the `test-device` CLI command and overall CLI structure. The `test-device` command was recently added (~500 lines) but was "vibe-coded" without proper structure or tests. This spec addresses code quality through refactoring and modularization, then adds new features including a flashing animation and enhanced interactive UI using the Rich library.

## Goals

- Refactor the `test-device` command to follow repository standards with proper structure and comprehensive test coverage
- Modularize `cli.py` by splitting commands into separate modules and extracting shared utilities
- Add a new "flashing" animation brightness level that's faster than fast_pulse with full brightness range
- Enhance the interactive test experience using Rich library for better visual feedback and progress indication
- Maintain backward compatibility with existing CLI functionality and behavior

## User Stories

**As a developer**, I want the `test-device` command to be well-structured and tested so that I can maintain and extend it confidently.

**As a developer**, I want CLI commands organized in separate modules so that the codebase remains maintainable as it grows.

**As a user**, I want to see a flashing animation option during device testing so that I can verify the full range of LED brightness capabilities.

**As a user**, I want an enhanced interactive test experience with visual progress indicators and colored output so that I can more easily understand test progress and results.

## Demoable Units of Work

### Unit 1: Code Quality Audit and Refactoring

**Purpose:** Bring the test-device command up to repository standards with proper structure and test coverage
**Demo Criteria:**
- Test-device command functionality extracted into well-structured functions/modules
- Comprehensive unit tests added covering all test-device functionality
- Code follows repository patterns (type hints, docstrings, error handling)
- All existing functionality preserved and working
**Proof Artifacts:**
- `pytest tests/test_cli_device.py -v` showing comprehensive test coverage for test-device command
- Code review showing extracted functions with clear responsibilities
- `uv run muteme-btn-control test-device --help` showing same command interface
- `uv run muteme-btn-control test-device` (non-interactive) producing same output as before

### Unit 2: CLI Modularization

**Purpose:** Split cli.py into maintainable command modules and extract shared utilities
**Demo Criteria:**
- CLI commands organized into separate modules (e.g., `cli/commands/test_device.py`, `cli/commands/run.py`)
- Shared utilities extracted into helper modules (e.g., `cli/utils/`)
- Main CLI app remains functional with all commands accessible
- No breaking changes to CLI interface or behavior
**Proof Artifacts:**
- Directory structure showing `src/muteme_btn/cli/commands/` and `src/muteme_btn/cli/utils/` directories
- `uv run muteme-btn-control --help` showing all commands still available
- All existing CLI tests passing (`pytest tests/test_cli*.py -v`)
- Code review showing clear separation of concerns

### Unit 3: Flashing Animation Feature

**Purpose:** Add a new "flashing" brightness level that's faster than fast_pulse with full brightness range
**Demo Criteria:**
- Flashing animation available as brightness option in `set_led_color()` method
- Flashing animation runs between Dim and Fast Pulse tests in test-device command
- Animation demonstrates gradual brightness change from completely off to full brightness
- Animation speed is noticeably faster than fast_pulse
- Flashing animation usable in daemon LED feedback (not just tests)
**Proof Artifacts:**
- `uv run muteme-btn-control test-device --interactive` showing flashing animation between Dim and Fast Pulse tests
- Visual confirmation of flashing animation on device (faster than fast_pulse, full brightness range)
- Code showing `brightness="flashing"` parameter support in `MuteMeDevice.set_led_color()`
- Test demonstrating flashing animation can be used in daemon context

### Unit 4: Rich Library Integration

**Purpose:** Enhance interactive test output with Rich library for better visual feedback
**Demo Criteria:**
- Rich library added as dependency to project
- Interactive test mode uses Rich components (progress bars, colored text, tables) for output
- Non-interactive mode and other CLI commands remain unchanged (still use Typer/logging)
- Enhanced visual feedback improves user understanding of test progress
**Proof Artifacts:**
- `pyproject.toml` showing Rich dependency
- `uv run muteme-btn-control test-device --interactive` showing Rich-enhanced output (progress bars, colored status, formatted tables)
- `uv run muteme-btn-control test-device` (non-interactive) showing standard output unchanged
- `uv run muteme-btn-control --help` showing standard Typer help (unchanged)

## Functional Requirements

### Refactoring Requirements

1. **The system shall** extract test-device command logic into well-structured functions with single responsibilities
2. **The system shall** add comprehensive unit tests for all test-device command functionality using mocked devices
3. **The system shall** maintain 100% backward compatibility with existing test-device command interface and behavior
4. **The system shall** follow repository coding standards (type hints, docstrings, error handling patterns)
5. **The system shall** organize CLI commands into separate modules under `src/muteme_btn/cli/commands/`
6. **The system shall** extract shared CLI utilities into `src/muteme_btn/cli/utils/` module
7. **The system shall** maintain all existing CLI command functionality after modularization

### Flashing Animation Requirements

8. **The system shall** support a new `brightness="flashing"` parameter in `MuteMeDevice.set_led_color()` method
9. **The system shall** implement flashing animation with gradual brightness change from completely off (0x00) to full brightness
10. **The system shall** make flashing animation faster than fast_pulse animation
11. **The system shall** include flashing animation in test-device brightness tests between Dim and Fast Pulse tests
12. **The system shall** make flashing animation available for use in daemon LED feedback controller
13. **The system shall** use appropriate HID report value offset for flashing brightness level (following existing pattern: dim=0x10, fast_pulse=0x20, slow_pulse=0x30)

14. **The system shall** add Rich library as a project dependency (`rich>=14.0.0`)
15. **The system shall** use Rich components (Console, Progress, Table, Panel) in interactive test-device mode only
16. **The system shall** use `rich.console.Console` as the primary interface for all Rich output
17. **The system shall** use `console.status()` for indeterminate operations (e.g., waiting for button press)
18. **The system shall** use Progress bars with context managers for test step progress indication
19. **The system shall** preserve standard Typer output for non-interactive test-device mode
20. **The system shall** preserve standard Typer/logging output for all other CLI commands (check-device, run, version, etc.)
21. **The system shall** use Rich to enhance visual feedback for test progress, status indicators, and diagnostic summaries
22. **The system shall** gracefully fall back to standard Typer output if Rich is unavailable

## Non-Goals (Out of Scope)

1. **Rich library for all CLI output**: Rich will only be used for interactive test-device mode; all other commands use Typer/logging
2. **Breaking CLI changes**: All existing CLI interfaces and behavior must remain unchanged
3. **New CLI commands**: This spec focuses on improving existing commands, not adding new ones
4. **Animation timing configuration**: Flashing animation timing will be fixed (not user-configurable)
5. **Multiple animation speeds**: Only one flashing animation speed will be implemented
6. **GUI or TUI interface**: This remains a CLI-only application
7. **Refactoring other commands**: Only test-device command and overall CLI structure will be refactored

## Design Considerations

### Code Organization

- **Command Modules**: Each CLI command should be in its own module under `src/muteme_btn/cli/commands/`
  - `test_device.py` - test-device command implementation
  - `run.py` - run command implementation
  - `check_device.py` - check-device command implementation
  - `version.py` - version command implementation
- **Shared Utilities**: Common CLI helpers in `src/muteme_btn/cli/utils/`
  - `config_loader.py` - configuration loading logic
  - `device_helpers.py` - device discovery and connection helpers
- **Main CLI**: `cli.py` becomes a thin orchestrator that imports and registers commands

### Flashing Animation Design

- **HID Report Value**: Following existing pattern, flashing should use offset 0x40 (next available after slow_pulse=0x30)
- **Animation Characteristics**:
  - Faster than fast_pulse (which uses 0x20 offset)
  - Gradual brightness change (not instant on/off)
  - Full range: completely off to full brightness
  - Device firmware handles actual animation timing
- **Test Sequence**: Brightness tests should run in order: Dim → Flashing → Normal → Fast Pulse → Slow Pulse

### Rich Library Integration

- **Selective Usage**: Rich components only in interactive test-device mode
- **Primary Interface**: Use `rich.console.Console` object as the primary interface for all Rich output
- **Components to Use**:
  - `rich.console.Console` - Main console object for styled output and logging
  - `rich.progress.Progress` - Progress bars for test steps (use context manager: `with Progress() as progress:`)
  - `rich.console.Console.status()` - Spinner animations for indeterminate operations (e.g., waiting for button press)
  - `rich.table.Table` - Diagnostic summaries and structured data display
  - `rich.panel.Panel` - Section headers and grouped content
  - `rich.console.Console.log()` - Timestamped logging with syntax highlighting
- **Best Practices**:
  - Use `console.print()` instead of standard `print()` for all Rich output
  - Use context managers for Progress bars (`with Progress() as progress:`)
  - Use transient progress bars (`transient=True`) for operations that complete quickly
  - Use `console.status()` for operations without known progress (e.g., waiting for user input)
  - Create a single `Console` instance and reuse it throughout the command
- **Fallback**: If Rich is unavailable, fall back to standard Typer output gracefully using try/except around Rich imports
- **Terminal Compatibility**: Rich automatically handles terminal compatibility; no special handling needed

## Repository Standards

This implementation must follow the standards documented in [CONTRIBUTING.md](../../../CONTRIBUTING.md) and [ARCHITECTURE.md](../../ARCHITECTURE.md). Key standards include:

- **Testing**: Use `typer.testing.CliRunner` for CLI command tests, mock HID devices for hardware-dependent tests (see [CONTRIBUTING.md Testing Requirements](../../../CONTRIBUTING.md#testing-requirements))
- **Type Hints**: All functions must have complete type annotations (Python 3.12+) (see [CONTRIBUTING.md Coding Standards](../../../CONTRIBUTING.md#coding-standards))
- **Docstrings**: All public functions and classes must have docstrings following existing patterns
- **Error Handling**: Use structured exception handling with clear error messages
- **Code Style**: Follow ruff configuration (line-length=100, target-version=py312)
- **Module Structure**: Follow module organization principles in [ARCHITECTURE.md](../../ARCHITECTURE.md#module-organization-principles)
- **File Size**: Aim for <300 lines per file (see [ARCHITECTURE.md File Size Guidelines](../../ARCHITECTURE.md#file-size-guidelines))
- **Test Coverage**: Maintain >85% overall coverage; aim for >95% coverage of test-device command specifically
- **Dependencies**: Add Rich to main dependencies (not dev dependencies) since it's used in production CLI
- **Commit Messages**: Follow [Conventional Commits](https://www.conventionalcommits.org/) specification (see [CONTRIBUTING.md Commit Guidelines](../../../CONTRIBUTING.md#commit-guidelines))

## Technical Considerations

### Development Methodology

This spec follows **Spec-Driven Development (SDD)** methodology. Implementation must follow **Test-Driven Development (TDD)** workflow as documented in [CONTRIBUTING.md](../../../CONTRIBUTING.md#development-methodology):
1. Write failing tests first (Red phase)
2. Implement minimal code to pass tests (Green phase)
3. Refactor while keeping tests green
4. Repeat for each feature

### Refactoring Approach

- **Incremental Refactoring**: Refactor test-device command first, then modularize CLI structure
- **Test-Driven**: Write tests for refactored code before extracting functions (TDD workflow)
- **Backward Compatibility**: Ensure all existing tests pass throughout refactoring process
- **Import Paths**: Update imports carefully to maintain compatibility with existing code
- **Documentation**: Update [ARCHITECTURE.md](../../ARCHITECTURE.md) when CLI modularization is complete

### Flashing Animation Implementation

- **HID Protocol**: Flashing uses device firmware animation capability (similar to pulse animations)
- **Brightness Offset**: Use 0x40 offset in color value (e.g., `color.value | 0x40`)
- **Device Compatibility**: Verify flashing works on all supported MuteMe device variants
- **Animation Timing**: Device firmware controls actual animation speed; we only set the brightness mode

### Rich Library Integration

- **Dependency Management**: Add `rich>=14.0.0` to `pyproject.toml` dependencies (latest stable version)
- **Conditional Import**: Import Rich only when needed (interactive test-device mode) with graceful fallback:
  ```python
  try:
      from rich.console import Console
      from rich.progress import Progress
      from rich.table import Table
      from rich.panel import Panel
      RICH_AVAILABLE = True
  except ImportError:
      RICH_AVAILABLE = False
  ```
- **Console Instance**: Create a single `Console` instance per command execution and reuse it
- **Output Consistency**: Ensure Rich output maintains same information as current output
- **Terminal Compatibility**: Rich handles terminal compatibility automatically (no special handling needed)
- **Testing**: Use `console.capture()` context manager for testing Rich output in unit tests

### Module Structure

The modularized CLI structure will follow the architecture patterns documented in [ARCHITECTURE.md](../../ARCHITECTURE.md):

```
src/muteme_btn/
├── cli/
│   ├── __init__.py          # Export main app
│   ├── app.py               # Main Typer app instance
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── test_device.py   # test-device command
│   │   ├── run.py           # run command
│   │   ├── check_device.py  # check-device command
│   │   └── version.py       # version command
│   └── utils/
│       ├── __init__.py
│       ├── config_loader.py  # Configuration loading helpers
│       └── device_helpers.py # Device discovery/connection helpers
```

This structure aligns with the "Modular CLI" consideration in [ARCHITECTURE.md Future Architecture Considerations](../../ARCHITECTURE.md#future-architecture-considerations).

## Success Metrics

1. **Code Quality**:
   - Test-device command has >95% test coverage (exceeds repository minimum of >85%)
   - All functions have type hints and docstrings (per [CONTRIBUTING.md Coding Standards](../../../CONTRIBUTING.md#coding-standards))
   - Code follows repository style guidelines (ruff passes, zero errors/warnings)
   - All quality gates pass (`just check`)
2. **Modularity**:
   - CLI commands organized into separate modules (per [ARCHITECTURE.md Module Organization](../../ARCHITECTURE.md#module-organization-principles))
   - No single file exceeds 300 lines (per [ARCHITECTURE.md File Size Guidelines](../../ARCHITECTURE.md#file-size-guidelines))
   - Clear separation of concerns between commands and utilities
3. **Feature Completeness**:
   - Flashing animation works in test-device command and daemon
   - Rich library enhances interactive test output
   - All existing functionality preserved
4. **User Experience**:
   - Interactive test mode provides clear visual feedback
   - Test output is easier to understand with Rich formatting
   - No regressions in CLI behavior or output
5. **Documentation**:
   - [ARCHITECTURE.md](../../ARCHITECTURE.md) updated to reflect modularized CLI structure
   - All code changes documented with appropriate docstrings

## Open Questions

1. **Flashing Animation Timing**: Should we verify specific timing requirements with device firmware, or rely on firmware defaults? (Answer: Use firmware defaults, verify visually)
2. **Rich Output Format**: Should diagnostic summary use Rich table, or maintain current text format? (Answer: Use Rich table for better readability)
3. **Test Coverage Target**: Should we aim for 100% coverage of test-device command, or maintain 90% overall? (Answer: Aim for >95% coverage of test-device command specifically)
4. **Module Naming**: Should command modules use snake_case (`test_device.py`) or match command names (`test-device.py`)? (Answer: Use snake_case for Python module naming conventions)
