# AGENTS.md

## Context Marker

Always begin your response with all active emoji markers, in the order they were introduced.

Format:  "<marker1><marker2><marker3>\n<response>"

The marker for this instruction is:  🤖

## Project Snapshot

- Python 3.12+ Linux CLI/daemon for MuteMe HID button + PulseAudio.
- Core package: `src/muteme_btn/`.
- Tooling: `uv`, `just`, `pytest`, `ruff`, `ty`, `pre-commit`, `bandit`.
- This repo uses strict TDD (Red -> Green -> Refactor).

## Fast Start Commands (Run These Exactly)

- Setup: `just setup`
- Full quality gate: `just check`
- Tests only: `just test`
- Lint: `just lint`
- Type check: `just type-check`
- Run daemon: `uv run muteme-btn-control run`
- Run daemon (debug): `uv run muteme-btn-control run --log-level DEBUG`
- Check device: `uv run muteme-btn-control check-device`
- Verbose device check: `uv run muteme-btn-control check-device --verbose`
- Run all hooks: `uv run pre-commit run --all-files`

## Required Workflow (TDD)

1. Write or adjust failing tests first.
2. Implement minimal code to pass tests.
3. Refactor while keeping tests green.
4. Re-run targeted tests, then `just check`.
5. Keep changes scoped and reviewable.

If behavior changes, add or adjust tests in `tests/` in the same change.

## Code and Architecture Expectations

- Follow existing module boundaries:
  - `hid/` for device I/O and HID semantics
  - `audio/` for backend integration
  - `core/` for daemon/state/LED orchestration
- Use typed Python and existing patterns (Ruff + ty must pass).
- Prefer explicit error handling with actionable messages.
- Use structured logging style already present in the codebase.

## Logging and Runtime Behavior Rules

When changing reconnect/device logic:

- Never reintroduce tight-loop log spam for expected transient states.
- Expected reconnect-time `open failed` paths should be warning/debug level, not noisy
  error floods.
- Preserve exponential reconnect backoff behavior.
- On reconnect, restore LED to reflect current backend mute state.
- Ensure stale HID read failures transition to disconnect/reconnect flow cleanly.

## Validation for Device/Reconnect Changes

For HID/daemon reconnect work, run:

1. Targeted tests for touched modules (for example `tests/test_hid_device.py`,
   `tests/test_core_daemon.py`, `tests/test_led_feedback.py`).
2. `just check`.
3. Manual smoke test in debug mode:
   - start `just run-debug`
   - unplug/replug device
   - verify reconnect attempts back off and recover
   - verify LED state is restored after reconnect

## Documentation Rules

- Keep docs in sync with behavior and CLI shape.
- Update `README.md` and `docs/IMPLEMENTATION_PLAN.md` when commands or behavior change.
- Treat `docs/specs.zip` as the archived SDD record. Do not extract or modify archived specs unless explicitly requested.

## Git and Commit Rules

- Use Conventional Commits.
- Do not bypass hooks (`--no-verify` is forbidden).
- Do not amend existing commits unless explicitly requested.
- Keep commits focused; split mixed concerns when reasonable.

## Safety Boundaries

### Always

- Run relevant tests for changed code.
- Run project quality checks before finishing.
- Keep secrets out of code and commits.

### Ask First

- New dependencies
- CI/workflow changes
- Security-sensitive behavior changes
- Broad refactors across multiple subsystems

### Never

- Commit secrets or credentials
- Disable or bypass hooks/checks
- Use destructive git commands without explicit instruction
