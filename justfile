# MuteMe Button Control - Task Runner Recipes
# See docs/IMPLEMENTATION_PLAN.md for development workflow details

_default:
    @just --list --unsorted

# Setup and development
setup:  # Install dependencies and pre-commit hooks
    #!/usr/bin/env bash
    uv sync
    uv run pre-commit install

check:  # Run all quality checks (lint, type, test)
    just lint
    just type-check
    just test

test:  # Run tests with coverage
    uv run pytest

lint:  # Run linting and formatting
    uv run ruff check src/ tests/
    uv run ruff format src/ tests/ --check

lint-fix:  # Run linting and formatting with auto-fix
    uv run ruff check src/ tests/ --fix
    uv run ruff format src/ tests/

type-check:  # Run type checking
    uv run ty check src/muteme_btn/

clean:  # Clean build artifacts
    rm -rf htmlcov/
    rm -rf .pytest_cache/
    rm -rf .ruff_cache/
    rm -rf src/*.egg-info/
    rm -rf dist/
    rm -rf build/
    find . -type d -name __pycache__ -exec rm -r {} +
    find . -type f -name "*.pyc" -delete

# Application execution
run:  # Run the daemon in foreground
    uv run muteme-btn-control

run-debug:  # Run with debug logging
    uv run muteme-btn-control --log-level debug

status:  # Check daemon status
    @echo "Status checking not yet implemented"

stop:  # Stop running daemon
    @echo "Daemon stop not yet implemented"

# Device management
install-udev:  # Install UDEV rules for device access
    @echo "Installing UDEV rules..."
    @if [ -f config/udev/99-muteme.rules ]; then \
        sudo cp config/udev/99-muteme.rules /etc/udev/rules.d/99-muteme.rules && \
        sudo udevadm control --reload-rules && \
        sudo udevadm trigger && \
        echo "✅ UDEV rules installed successfully"; \
    else \
        echo "❌ UDEV rules file not found at config/udev/99-muteme.rules"; \
        exit 1; \
    fi

check-device:  # Verify device permissions and connectivity
    uv run muteme-btn-control check-device

check-device-verbose:  # Verify device permissions with detailed output
    uv run muteme-btn-control check-device --verbose

# Building and installation
build:  # Build package
    uv build

install:  # Install locally
    uv pip install -e .

# Development utilities
coverage:  # Show coverage report
    uv run pytest --cov=src/muteme_btn --cov-report=term-missing

coverage-html:  # Generate HTML coverage report
    uv run pytest --cov=src/muteme_btn --cov-report=html
    @echo "Coverage report generated in htmlcov/index.html"

pre-commit-all:  # Run pre-commit hooks on all files
    uv run pre-commit run --all-files

version:  # Show version information
    uv run muteme-btn-control --version

help:  # Show CLI help
    uv run muteme-btn-control --help
