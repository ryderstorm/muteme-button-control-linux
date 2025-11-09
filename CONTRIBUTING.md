# Contributing to MuteMe Button Control

Thank you for your interest in contributing! This document outlines the development standards, patterns, and workflows used in this project.

## Table of Contents

- [Development Methodology](#development-methodology)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Code Organization](#code-organization)
- [Documentation Standards](#documentation-standards)
- [Development Workflow](#development-workflow)
- [Quality Gates](#quality-gates)
- [Commit Guidelines](#commit-guidelines)

## Development Methodology

### Spec-Driven Development (SDD)

This project uses **Spec-Driven Development (SDD)** methodology, where features are developed through a structured workflow: **idea → specification → tasks → implementation → validation**. Detailed specifications in [`docs/specs/`](../docs/specs/) define system behavior, requirements, and success criteria before implementation begins. This approach ensures clear communication, reduces ambiguity, and provides a shared understanding for both human developers and AI coding assistants.

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
- **Coverage**: Maintain >85% test coverage throughout development
- **No Exceptions**: No production code without corresponding tests

#### TDD Workflow Example

```bash
# 1. Write failing test
uv run pytest tests/test_new_feature.py -v  # Should fail

# 2. Implement minimal code
# Edit src/muteme_btn/new_feature.py

# 3. Verify test passes
uv run pytest tests/test_new_feature.py -v  # Should pass

# 4. Refactor if needed
uv run pytest tests/ --cov=muteme_btn  # Maintain coverage
```

## Coding Standards

### Python Version

- **Minimum Version**: Python 3.12+
- **Type Hints**: All functions must have complete type annotations
- **Target Version**: Configured in `pyproject.toml` and ruff settings

### Code Style

- **Formatter**: Ruff (configured in `pyproject.toml`)
- **Line Length**: 100 characters
- **Import Sorting**: Automatic via ruff isort
- **Style Guide**: Follow PEP 8 with ruff-specific rules

### Type Hints

All public functions and classes must have complete type annotations:

```python
def process_event(self, event: ButtonEvent) -> List[str]:
    """Process button event and return actions."""
    ...
```

### Docstrings

All public functions and classes must have docstrings:

```python
def set_led_color(
    self,
    color: LEDColor,
    brightness: str = "normal",
) -> None:
    """Set LED color on device.

    Args:
        color: LED color to set
        brightness: Brightness level (normal, dim, fast_pulse, slow_pulse)

    Raises:
        DeviceError: If device is not connected
    """
    ...
```

### Error Handling

- **Structured Errors**: Use custom exception classes with clear messages
- **Graceful Degradation**: Continue operating if non-critical components fail
- **Comprehensive Logging**: Every error logged with context
- **User-Friendly Messages**: Provide actionable error messages

Example:

```python
if not device.is_connected():
    raise DeviceError("Device not connected. Check USB connection.")
```

## Testing Requirements

### Test Structure

- **Location**: All tests in `tests/` directory
- **Naming**: Test files must start with `test_`
- **Test Functions**: Must start with `test_`
- **Test Classes**: Use descriptive class names like `TestMuteMeDaemon`

### Test Patterns

#### CLI Command Testing

Use `typer.testing.CliRunner` for CLI tests:

```python
from typer.testing import CliRunner
from muteme_btn.cli import app

runner = CliRunner()

def test_version_command():
    """Test version command outputs correct version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "muteme-btn-control 0.1.0" in result.stdout
```

#### Mocking Hardware Dependencies

Mock HID devices and audio backends for reliable CI testing:

```python
from unittest.mock import patch

@patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
def test_device_discovery(mock_discover):
    """Test device discovery with mocked hardware."""
    mock_discover.return_value = [mock_device]
    # Test implementation
```

#### Async Testing

Use `pytest-asyncio` for async function tests:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Coverage Requirements

- **Minimum Coverage**: >85% overall
- **New Code**: Must maintain or improve coverage
- **Coverage Report**: Run `just coverage` to see current coverage

See [README.md](README.md) for test execution commands.

## Code Organization

See [ARCHITECTURE.md](../docs/ARCHITECTURE.md) for detailed project structure, module organization principles, and architecture documentation.

## Documentation Standards

### Critical for AI-Driven Development

**Documentation must be kept in sync with code changes** - this is essential for autonomous AI development and debugging.

### Documentation Requirements

1. **Update Immediately**: When adding features, update docs in the same PR/commit
2. **API Documentation**: Keep function signatures and examples current
3. **Configuration Changes**: Update configuration schema when adding options
4. **Architecture Decisions**: Document why changes were made
5. **CLI Commands**: Update command examples when adding new flags/subcommands

### Documentation Files to Maintain

- **`README.md`**: Installation, usage, and basic development info
- **`CONTRIBUTING.md`**: This file - development standards and guidelines
- **`docs/ARCHITECTURE.md`**: Project structure, architecture, and design decisions
- **`docs/IMPLEMENTATION_PLAN.md`**: Project status and roadmap
- **`docs/specs/`**: Feature specifications
- **Code docstrings**: API documentation for all public functions
- **Configuration examples**: Keep `config/muteme.toml.example` current

### Documentation Workflow

- **Before implementing**: Read relevant docs and plan documentation updates
- **During development**: Update docs as you implement features
- **Before committing**: Verify all documentation is accurate and examples work

### AI Documentation Standards

- **Clear Examples**: All code examples must be tested and working
- **Version-Specific**: Document version-specific behavior
- **Error Scenarios**: Document common errors and solutions
- **Debugging Info**: Include troubleshooting steps
- **Configuration Mappings**: Show how config options affect behavior

**Remember: Outdated documentation is worse than no documentation for AI development.**

## Development Workflow

### Development Loop (TDD)

1. **Write Test**: Create failing test for desired functionality
2. **Run Test**: Verify test fails (Red phase)
3. **Implement Code**: Write minimal code to make test pass (Green phase)
4. **Run Test**: Verify test passes
5. **Refactor**: Improve code while keeping tests green
6. **Run Tests**: Full test suite with coverage (`just check`)
7. **Repeat**: Continue TDD cycle for next feature

See [README.md](README.md) for setup instructions and available `just` recipes.

## Quality Gates

### Pre-Commit Hooks

[Pre-commit](https://pre-commit.com/) hooks run automatically on commit. They check:

- **Trailing whitespace**: Removed automatically
- **End of file**: Newline added automatically
- **YAML/TOML**: Syntax validation
- **Large files**: Warning for files >500KB
- **Debug statements**: Check for debugger statements
- **Ruff linting**: Python code quality checks
- **Ruff formatting**: Code formatting checks
- **Type checking**: Static type analysis with `ty`
- **Security**: Bandit security checks

### Quality Standards

- **Linting**: Zero ruff errors or warnings
- **Type Checking**: Zero type errors
- **Test Coverage**: >85% overall coverage
- **Security**: Zero high/critical bandit findings
- **All Tests**: All tests must pass

Before committing, run `just check` to verify all quality gates pass.

## Commit Guidelines

### Commit Message Format

Use clear, descriptive commit messages:

```bash
feat: add flashing animation brightness level

- Add brightness="flashing" parameter to set_led_color()
- Implement flashing animation with 0x40 offset
- Add flashing test to test-device command between Dim and Fast Pulse
- Update device.py with flashing brightness support

Closes #123
```

### Commit Types

This project follows [Conventional Commits](https://www.conventionalcommits.org/) specification:

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **test**: Test additions or changes
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **chore**: Maintenance tasks

### Commit Best Practices

- **Atomic Commits**: One logical change per commit
- **Test Coverage**: Include tests in same commit as feature
- **Documentation**: Update docs in same commit as code changes
- **Quality Gates**: Ensure `just check` passes before committing

## Development Tools

See [README.md](README.md) for available `just` recipes and development commands.

## Code Review Guidelines

When reviewing code, check for:

1. **TDD Compliance**: Tests written before implementation
2. **Test Coverage**: Adequate test coverage for new code
3. **Type Hints**: Complete type annotations
4. **Docstrings**: Clear documentation for public APIs
5. **Code Style**: Follows ruff formatting rules
6. **Error Handling**: Proper exception handling
7. **Documentation**: Docs updated alongside code
8. **Quality Gates**: All checks pass

Thank you for contributing to MuteMe Button Control!
