"""Main daemon orchestration with asyncio."""

import asyncio
import logging
import signal

from muteme_btn.audio.pulse import AudioConfig, PulseAudioBackend
from muteme_btn.config import DeviceConfig
from muteme_btn.core.led_feedback import LEDFeedbackController
from muteme_btn.core.state import ButtonEvent, ButtonStateMachine
from muteme_btn.hid.device import MuteMeDevice

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

        self.device = device or MuteMeDevice(self.device_config)
        self.audio_backend = audio_backend or PulseAudioBackend(self.audio_config)
        self.state_machine = state_machine or ButtonStateMachine()
        self.led_controller = led_controller or LEDFeedbackController(
            device=self.device, audio_backend=self.audio_backend
        )

        self.running: bool = False
        self._shutdown_event = asyncio.Event()

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

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        try:
            self._shutdown_event.set()
        except Exception as e:
            logger.error(f"Error in signal handler: {e}")

    async def start(self) -> None:
        """Start the daemon main loop."""
        if self.running:
            logger.warning("Daemon is already running")
            return

        logger.info("Starting MuteMe daemon")
        self.running = True
        self._shutdown_event.clear()

        try:
            # Initialize LED to current mute status
            await self._update_led_feedback()

            # Run main loop
            await self._main_loop()
        except Exception as e:
            logger.error(f"Daemon error: {e}")
        finally:
            self.running = False
            # Ensure cleanup is called on shutdown
            self.cleanup()
            logger.info("MuteMe daemon stopped")

    async def stop(self) -> None:
        """Stop the daemon gracefully."""
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
            self.running = False

    async def _main_loop(self) -> None:
        """Main daemon loop."""
        while self.running and not self._shutdown_event.is_set():
            try:
                # Process button events
                await self._process_button_events()

                # Update LED feedback
                await self._update_led_feedback()

                # Small delay to prevent busy waiting
                try:
                    await asyncio.wait_for(
                        asyncio.sleep(0.01),  # 10ms poll interval
                        timeout=0.1,
                    )
                except TimeoutError:
                    # Continue loop if sleep times out
                    pass

            except asyncio.CancelledError:
                logger.debug("Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                # Continue running despite errors

    async def _process_button_events(self) -> None:
        """Process button events from the device."""
        try:
            if not self.device.is_connected():
                logger.debug("Device not connected, skipping event processing")
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

    async def _update_led_feedback(self) -> None:
        """Update LED feedback based on current mute status."""
        try:
            self.led_controller.update_led_to_mute_status()
        except Exception as e:
            logger.error(f"Error updating LED feedback: {e}")

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
