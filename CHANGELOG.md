# CHANGELOG

<!-- version list -->

## v0.2.1 (2026-03-05)

### Bug Fixes

- **device**: Improve reconnect resilience and distro-aware udev handling
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

- **device**: Recover from disconnects with reconnect backoff
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

- **review**: Address PR feedback for reconnect and udev hardening
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

- **udev**: Install distro-aware udev rules
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

### Chores

- **config**: Add CodeRabbit review filters
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

### Continuous Integration

- **cache**: Extract uv cache logic into reusable composite actions
  ([#11](https://github.com/ryderstorm/muteme-button-control-linux/pull/11),
  [`e0e86e4`](https://github.com/ryderstorm/muteme-button-control-linux/commit/e0e86e434eb7a98abdedada4b5c9097ce89b1382))

- **pre-commit**: Update markdownlint configuration and fix linting issues
  ([#10](https://github.com/ryderstorm/muteme-button-control-linux/pull/10),
  [`8f335f3`](https://github.com/ryderstorm/muteme-button-control-linux/commit/8f335f3b226276b5069d1b5b343bb5ef6c9e9995))

### Documentation

- **agents**: Add repository AGENTS guidance
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

- **plan**: Clarify udev install and CLI invocation
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

- **plan**: Sync udev and test-count status
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

- **plan**: Update reconnect status and CLI examples
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

- **readme**: Include Mini IDs in lsusb verification
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

- **readme**: Include Mini vendor in udev trigger example
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))

### Testing

- **hid**: Cover usb-node detection and CLI permission paths
  ([#12](https://github.com/ryderstorm/muteme-button-control-linux/pull/12),
  [`0557e90`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0557e90028075912845b12892826c361286dab38))


## v0.2.0 (2025-11-10)

### Bug Fixes

- Address PR review feedback for flashing and kill-instances
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **ci**: Install curl before installing uv in semantic-release
  ([`40cd8ee`](https://github.com/ryderstorm/muteme-button-control-linux/commit/40cd8ee1bac50a6188b8deb0a9105c534745c5a6))

- **ci**: Install uv in build_command for semantic-release
  ([`48edf87`](https://github.com/ryderstorm/muteme-button-control-linux/commit/48edf879f4ceefac1a0ac63ff48910c5cbd61028))

- **cli**: Address remaining PR review feedback
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **cli**: Exclude child processes from kill-instances when parent is also listed
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **cli**: Fix quick test mode cleanup and input handling
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **cli**: Improve kill-instances filtering to only target daemon processes
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **cli**: Remove duplicate testing message for flashing
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **cli**: Show full command line in kill-instances output
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **cli**: Use exact token matching for kill-instances exclude check
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **device**: Implement flashing as software-side animation
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

### Continuous Integration

- Replace markdownlint-cli2 with Ruby markdownlint
  ([#9](https://github.com/ryderstorm/muteme-button-control-linux/pull/9),
  [`84b0d14`](https://github.com/ryderstorm/muteme-button-control-linux/commit/84b0d14a26f0e177666314112021d48890a53b6a))

### Documentation

- Add link to inspiration repository
  ([#9](https://github.com/ryderstorm/muteme-button-control-linux/pull/9),
  [`84b0d14`](https://github.com/ryderstorm/muteme-button-control-linux/commit/84b0d14a26f0e177666314112021d48890a53b6a))

- Mark task 2.7 as complete - flashing animation verified working
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- Remove Windows/macOS installation instructions
  ([#9](https://github.com/ryderstorm/muteme-button-control-linux/pull/9),
  [`84b0d14`](https://github.com/ryderstorm/muteme-button-control-linux/commit/84b0d14a26f0e177666314112021d48890a53b6a))

- **spec**: Add task breakdown for test-device improvements
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **spec**: Add test-device improvements specification
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **spec**: Clarify Rich library usage in test-device command
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

### Features

- **cli**: Add --color and --brightness flags to test-device command
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **cli**: Add detailed process information to kill-instances output
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **cli**: Add kill-instances command to find and kill running processes
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **cli**: Refactor test-device command and add flashing animation
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **cli**: Refactor test-device command with proper structure and comprehensive tests
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **device**: Add flashing animation brightness level feature
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

- **docs**: Redesign README with modern best practices
  ([#9](https://github.com/ryderstorm/muteme-button-control-linux/pull/9),
  [`84b0d14`](https://github.com/ryderstorm/muteme-button-control-linux/commit/84b0d14a26f0e177666314112021d48890a53b6a))

- **docs**: Redesign README with modern best practices and fix CI
  ([#9](https://github.com/ryderstorm/muteme-button-control-linux/pull/9),
  [`84b0d14`](https://github.com/ryderstorm/muteme-button-control-linux/commit/84b0d14a26f0e177666314112021d48890a53b6a))

### Performance Improvements

- **tests**: Fix slow tests by mocking time.sleep and asyncio.sleep
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))

### Refactoring

- **cli**: Address final PR review feedback
  ([#6](https://github.com/ryderstorm/muteme-button-control-linux/pull/6),
  [`0472f69`](https://github.com/ryderstorm/muteme-button-control-linux/commit/0472f691509f8d2e42d4b23095e74782a25cfc4b))


## v0.1.1 (2025-11-09)

### Bug Fixes

- Ignore local config file ([#5](https://github.com/ryderstorm/muteme-button-control-linux/pull/5),
  [`05cadf9`](https://github.com/ryderstorm/muteme-button-control-linux/commit/05cadf9565d092dadd3e3423a08590c2280a6c5b))

- Resolve pre-existing type-checking issues
  ([#5](https://github.com/ryderstorm/muteme-button-control-linux/pull/5),
  [`05cadf9`](https://github.com/ryderstorm/muteme-button-control-linux/commit/05cadf9565d092dadd3e3423a08590c2280a6c5b))

- **audio**: Mute microphone sources instead of output sinks
  ([#5](https://github.com/ryderstorm/muteme-button-control-linux/pull/5),
  [`05cadf9`](https://github.com/ryderstorm/muteme-button-control-linux/commit/05cadf9565d092dadd3e3423a08590c2280a6c5b))

### Refactoring

- **cli**: Address PR review feedback and improve RGB pattern
  ([#5](https://github.com/ryderstorm/muteme-button-control-linux/pull/5),
  [`05cadf9`](https://github.com/ryderstorm/muteme-button-control-linux/commit/05cadf9565d092dadd3e3423a08590c2280a6c5b))

- **cli**: Remove dead code and consolidate imports
  ([#5](https://github.com/ryderstorm/muteme-button-control-linux/pull/5),
  [`05cadf9`](https://github.com/ryderstorm/muteme-button-control-linux/commit/05cadf9565d092dadd3e3423a08590c2280a6c5b))


## v0.1.0 (2025-11-09)

- Initial Release
