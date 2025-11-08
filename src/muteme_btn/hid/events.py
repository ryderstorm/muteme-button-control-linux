"""Button event handling and processing for MuteMe devices."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
import structlog
import time

logger = structlog.get_logger(__name__)


class ButtonState(Enum):
    """Button press states."""
    RELEASED = 0
    PRESSED = 1


@dataclass
class ButtonEvent:
    """Represents a button press/release event."""
    state: ButtonState
    timestamp: float
    device_path: str
    
    @property
    def is_press(self) -> bool:
        """Check if this is a press event."""
        return self.state == ButtonState.PRESSED
    
    @property
    def is_release(self) -> bool:
        """Check if this is a release event."""
        return self.state == ButtonState.RELEASED


class EventHandler:
    """Handles button events from MuteMe devices."""
    
    def __init__(self, device_path: str):
        """Initialize event handler.
        
        Args:
            device_path: Path to the device generating events
        """
        self.device_path = device_path
        self._event_callback: Optional[Callable[[ButtonEvent], None]] = None
        
    def set_event_callback(self, callback: Callable[[ButtonEvent], None]) -> None:
        """Set callback function for button events.
        
        Args:
            callback: Function to call when button events occur
        """
        self._event_callback = callback
        
    def process_hid_data(self, data: bytes) -> None:
        """Process raw HID data and generate button events.
        
        Args:
            data: Raw bytes from HID device
        """
        # MuteMe sends simple 1-byte reports where 0x00 = released, 0x01 = pressed
        if len(data) >= 1:
            button_byte = data[0]
            state = ButtonState.PRESSED if button_byte == 0x01 else ButtonState.RELEASED
            
            event = ButtonEvent(
                state=state,
                timestamp=time.time(),
                device_path=self.device_path
            )
            
            logger.debug("Button event detected", 
                        state=state.name, 
                        timestamp=event.timestamp,
                        device_path=self.device_path)
            
            if self._event_callback:
                self._event_callback(event)
