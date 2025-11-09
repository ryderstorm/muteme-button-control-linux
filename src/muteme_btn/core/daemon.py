"""Main daemon orchestration with asyncio."""

import asyncio
import logging
import signal
import traceback
from types import FrameType

from muteme_btn.audio.pulse import AudioConfig, PulseAudioBackend
from muteme_btn.config import DeviceConfig
from muteme_btn.core.led_feedback import LEDFeedbackController
from muteme_btn.core.state import ButtonEvent, ButtonStateMachine
from muteme_btn.hid.device import DeviceError, LEDColor, MuteMeDevice

logger = logging.getLogger(__name__)


class MuteMeDaemon:
    """Main daemon that orchestrates all components."""

    def __init__(
        self,
        device_config: DeviceConfig | None = None,
        audio_config: AudioConfig | None = None,
        device: MuteMeDevice | None = None,
        audio_backend: PulseAudioBackend | None = None,
        state_machine: ButtonStateMachine | None = None,
        led_controller: LEDFeedbackController | None = None,
    ):
        """Initialize MuteMe daemon.

        Args:
            device_config: Device configuration (created if not provided)
            audio_config: Audio configuration (created if not provided)
            device: HID device instance (created if not provided)
            audio_backend: Audio backend instance (created if not provided)
            state_machine: Button state machine (created if not provided)
            led_controller: LED feedback controller (created if not provided)
        """
        # Use provided instances or create new ones
        self.device_config = device_config or DeviceConfig()
        self.audio_config = audio_config or AudioConfig()

        # Device will be connected in start() if not provided
        self.device = device
        self.audio_backend = audio_backend or PulseAudioBackend(self.audio_config)
        self.state_machine = state_machine or ButtonStateMachine()
        # LED controller will be created after device is connected
        self.led_controller = led_controller

        self.running: bool = False
        self._shutdown_event = asyncio.Event()
        # Lock for thread-safe access to running flag
        # Note: Signal handlers run in the main thread, so GIL provides protection,
        # but this lock ensures explicit synchronization for async operations
        self._running_lock = asyncio.Lock()

        # Setup signal handlers
        self._setup_signal_handlers()

        logger.info("Initialized MuteMe daemon")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        try:
            # Register signal handlers for SIGINT and SIGTERM
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            logger.debug("Signal handlers registered for SIGINT and SIGTERM")
        except Exception as e:
            logger.warning(f"Failed to setup signal handlers: {e}")

    def _signal_handler(self, signum: int, frame: FrameType | None) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame (may be None in some contexts)
        """
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        try:
            self._shutdown_event.set()
        except Exception as e:
            logger.error(f"Error in signal handler: {e}")

    async def start(self) -> None:
        """Start the daemon main loop."""
        async with self._running_lock:
            if self.running:
                logger.warning("Daemon is already running")
                return

            logger.info("Starting MuteMe daemon")
            self.running = True
            self._shutdown_event.clear()

        device_connected = False
        try:
            # Connect to device if not already connected
            if not self.device or not self.device.is_connected():
                await self._connect_device()
                device_connected = True
                # Give device a moment to initialize after connection
                # Some HID devices need time before accepting commands
                await asyncio.sleep(0.1)

            # Create LED controller if not already created
            if not self.led_controller:
                if not self.device:
                    raise DeviceError("Device not connected, cannot create LED controller")
                self.led_controller = LEDFeedbackController(
                    device=self.device, audio_backend=self.audio_backend
                )

            # Show startup connection pattern: flash blue-green-red 3 times
            await self._show_startup_pattern()

            # Initialize LED to current mute status
            await self._update_led_feedback()

            # Run main loop
            await self._main_loop()
        except Exception as e:
            logger.error(f"Daemon error: {e}")
            # Log traceback in debug mode for better debugging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Exception traceback:\n{traceback.format_exc()}")
            # Ensure device cleanup on exception
            if device_connected and self.device:
                try:
                    if hasattr(self.device, "close"):
                        self.device.close()  # type: ignore[call-overload]
                    elif hasattr(self.device, "disconnect"):
                        self.device.disconnect()  # type: ignore[call-overload]
                except Exception as cleanup_error:
                    logger.warning(f"Error cleaning up device after exception: {cleanup_error}")
        finally:
            async with self._running_lock:
                self.running = False
            # Ensure cleanup is called on shutdown
            self.cleanup()
            logger.info("MuteMe daemon stopped")

    async def _connect_device(self) -> None:
        """Discover and connect to a MuteMe device."""
        logger.info("Discovering MuteMe devices...")
        devices = MuteMeDevice.discover_devices()

        if not devices:
            raise DeviceError(
                "No MuteMe devices found. Please ensure your device is connected "
                "and UDEV rules are installed."
            )

        # Filter by configured VID/PID if specified
        matching_devices = [
            d
            for d in devices
            if d.vendor_id == self.device_config.vid and d.product_id == self.device_config.pid
        ]

        if not matching_devices:
            vid_pid = f"VID:0x{self.device_config.vid:04x} PID:0x{self.device_config.pid:04x}"
            logger.warning(f"No devices found matching {vid_pid}")
            # Try any discovered device
            matching_devices = devices

        # Use the first matching device
        device_info = matching_devices[0]
        vid_pid = f"VID:0x{device_info.vendor_id:04x} PID:0x{device_info.product_id:04x}"
        logger.info(f"Found device: {vid_pid} Path:{device_info.path}")

        # Try connecting using VID/PID first (more reliable)
        try:
            logger.debug("Attempting connection by VID/PID")
            self.device = MuteMeDevice.connect_by_vid_pid(
                device_info.vendor_id, device_info.product_id
            )
            logger.info("Successfully connected to device using VID/PID")
        except DeviceError as e:
            logger.warning(f"VID/PID connection failed: {e}, trying path-based connection")
            # Fallback to path-based connection
            try:
                logger.debug(f"Attempting connection by path: {device_info.path}")
                self.device = MuteMeDevice.connect(device_info.path)
                logger.info(f"Successfully connected to device at {device_info.path}")
            except DeviceError as path_error:
                # Combine both error messages
                vid_pid = f"VID:0x{device_info.vendor_id:04x} PID:0x{device_info.product_id:04x}"
                raise DeviceError(
                    f"Failed to connect using both methods:\n"
                    f"VID/PID method: {e}\n"
                    f"Path method: {path_error}\n\n"
                    f"Device info: {vid_pid} Path:{device_info.path}"
                ) from path_error

    async def stop(self) -> None:
        """Stop the daemon gracefully."""
        async with self._running_lock:
            if not self.running:
                logger.debug("Daemon is not running")
                return

        logger.info("Stopping MuteMe daemon")
        self._shutdown_event.set()

        # Wait a moment for graceful shutdown
        try:
            await asyncio.wait_for(asyncio.sleep(0.1), timeout=1.0)
        except TimeoutError:
            logger.warning("Graceful shutdown timeout, forcing stop")
        finally:
            async with self._running_lock:
                self.running = False

    async def _main_loop(self) -> None:
        """Main daemon loop."""
        # Use configurable poll interval and timeout from device config
        poll_interval = self.device_config.poll_interval_ms / 1000.0
        poll_timeout = self.device_config.poll_timeout_ms / 1000.0

        while True:
            # Thread-safe check of running flag
            async with self._running_lock:
                if not self.running:
                    break
                running_state = self.running

            if not running_state or self._shutdown_event.is_set():
                break

            try:
                # Process button events
                await self._process_button_events()

                # Update LED feedback
                await self._update_led_feedback()

                # Small delay to prevent busy waiting
                try:
                    await asyncio.wait_for(
                        asyncio.sleep(poll_interval),
                        timeout=poll_timeout,
                    )
                except TimeoutError:
                    # Continue loop if sleep times out
                    pass

            except asyncio.CancelledError:
                logger.debug("Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                # Log traceback in debug mode
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Exception traceback:\n{traceback.format_exc()}")
                # Continue running despite errors

    async def _process_button_events(self) -> None:
        """Process button events from the device."""
        try:
            if not self.device.is_connected():
                logger.info("Device not connected, skipping event processing")
                return

            # Read events from device
            events = await self.device.read_events()  # type: ignore[call-overload]

            for event in events:
                # Convert to button event
                button_event = ButtonEvent(type=event.type, timestamp=event.timestamp)

                # Process through state machine
                actions = self.state_machine.process_event(button_event)

                # Handle actions (avoid duplicates)
                for action in set(actions):  # Use set to avoid duplicate actions
                    await self._handle_action(action)

        except Exception as e:
            logger.error(f"Error processing button events: {e}")
            # Log traceback in debug mode for better debugging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Exception traceback:\n{traceback.format_exc()}")

    async def _handle_action(self, action: str) -> None:
        """Handle an action from the state machine.

        Args:
            action: Action to handle (e.g., "toggle")
        """
        try:
            if action == "toggle":
                # Toggle mute state
                current_muted = self.audio_backend.is_muted(None)
                new_muted = not current_muted
                self.audio_backend.set_mute_state(None, new_muted)

                # Update LED to reflect new state
                await self._update_led_feedback()

                logger.info(f"Toggled mute state: {new_muted}")
            else:
                logger.debug(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error handling action '{action}': {e}")
            # Log traceback in debug mode for better debugging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Exception traceback:\n{traceback.format_exc()}")

    async def _show_startup_pattern(self) -> None:
        """Show startup connection pattern: flash blue-green-red 3 times."""
        try:
            if not self.device or not self.device.is_connected():
                logger.warning("Device not connected, skipping startup pattern")
                return

            colors = [LEDColor.BLUE, LEDColor.GREEN, LEDColor.RED]
            flash_duration = 0.15  # 150ms per color
            repeats = 3

            logger.info("Showing startup connection pattern")
            errors = []
            for repeat_num in range(repeats):
                for color in colors:
                    try:
                        self.device.set_led_color(color)
                        await asyncio.sleep(flash_duration)
                        # Turn off briefly between colors
                        self.device.set_led_color(LEDColor.NOCOLOR)
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        error_msg = (
                            f"Error setting LED color {color.name} in repeat {repeat_num + 1}: {e}"
                        )
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        # Continue trying other colors even if one fails

            # Brief pause before showing actual status
            await asyncio.sleep(0.1)

            if errors:
                logger.warning(
                    f"Startup pattern completed with {len(errors)} error(s). "
                    "Device may not be ready or LED control may be failing."
                )
            else:
                logger.info("Startup pattern complete")

        except Exception as e:
            logger.error(f"Error showing startup pattern: {e}", exc_info=True)

    async def _update_led_feedback(self) -> None:
        """Update LED feedback based on current mute status."""
        try:
            # Check if device and LED controller are available
            if not self.device or not self.device.is_connected():
                logger.info("Device not connected, skipping LED feedback update")
                return

            if not self.led_controller:
                logger.debug("LED controller not initialized, skipping LED feedback update")
                return

            self.led_controller.update_led_to_mute_status()
        except Exception as e:
            logger.error(f"Error updating LED feedback: {e}")
            # Log traceback in debug mode for better debugging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Exception traceback:\n{traceback.format_exc()}")

    def cleanup(self) -> None:
        """Clean up resources on shutdown."""
        try:
            logger.debug("Cleaning up daemon resources")

            # Close device connection
            if hasattr(self, "device") and self.device:
                try:
                    if hasattr(self.device, "close"):
                        self.device.close()  # type: ignore[call-overload]
                    elif hasattr(self.device, "disconnect"):
                        self.device.disconnect()  # type: ignore[call-overload]
                except Exception as e:
                    logger.warning(f"Error closing device: {e}")

            # Close audio backend
            if hasattr(self, "audio_backend") and self.audio_backend:
                try:
                    self.audio_backend.close()
                except Exception as e:
                    logger.warning(f"Error closing audio backend: {e}")

            # Reset state machine
            if hasattr(self, "state_machine") and self.state_machine:
                try:
                    self.state_machine.reset()
                except Exception as e:
                    logger.warning(f"Error resetting state machine: {e}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.running:
            await self.stop()
        self.cleanup()
