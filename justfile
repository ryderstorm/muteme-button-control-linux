# MuteMe Button Control - Task Runner Recipes
# See docs/IMPLEMENTATION_PLAN.md for development workflow details

_default:
    @just --list --unsorted

# Setup and development
setup:  # Install dependencies and pre-commit hooks
    #!/usr/bin/env bash
    uv sync
    uv run pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg --overwrite

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
    uv run muteme-btn-control run --log-level DEBUG

status:  # Check daemon status
    @echo "Status checking not yet implemented"

stop:  # Stop running daemon
    @echo "Daemon stop not yet implemented"

# Device management
install-udev:  # Install UDEV rules for device access
    #!/usr/bin/env bash
    set -euo pipefail

    echo "Installing UDEV rules..."

    rules_dir="/etc/udev/rules.d"
    # IMPORTANT: keep this file number < 73 so TAG+=\"uaccess\" is applied before 73-seat-late.rules
    dest_rules="${rules_dir}/72-muteme.rules"
    legacy_rules="${rules_dir}/99-muteme.rules"

    src_rules=""
    chosen_group=""

    if getent group plugdev >/dev/null 2>&1; then
        src_rules="config/udev/72-muteme-plugdev.rules"
        chosen_group="plugdev"
    else
        src_rules="config/udev/72-muteme-users.rules"
        chosen_group="users"
    fi

    if [ ! -f "${src_rules}" ]; then
        echo "❌ UDEV rules file not found at ${src_rules}"
        exit 1
    fi

    if [ -f "${legacy_rules}" ]; then
        echo "Removing legacy rules file: ${legacy_rules}"
        sudo rm -f "${legacy_rules}"
    fi

    echo "Installing ${src_rules} → ${dest_rules} (group=${chosen_group})"
    sudo install -m 0644 "${src_rules}" "${dest_rules}"

    echo "Reloading and triggering udev rules..."
    sudo udevadm control --reload-rules
    sudo udevadm trigger

    # Best-effort hint if the user isn't a member of the chosen group (uaccess may still work)
    install_user="${SUDO_USER:-${USER}}"
    if ! id -nG "${install_user}" | tr ' ' '\n' | grep -qx "${chosen_group}"; then
        echo ""
        echo "⚠️  Note: user '${install_user}' is not in group '${chosen_group}'."
        echo "   Desktop sessions should still work via TAG+=\"uaccess\"."
        echo "   For headless/SSH/system services, add group membership and re-login:"
        echo "   sudo usermod -a -G ${chosen_group} ${install_user}"
    fi

    echo "✅ UDEV rules installed successfully"

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
