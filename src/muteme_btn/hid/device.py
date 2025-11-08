"""HID device discovery and communication for MuteMe buttons."""

import hid
import os
import stat
import pwd
import grp
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import structlog

logger = structlog.get_logger(__name__)


class LEDColor(Enum):
    """LED color options for MuteMe devices."""
    NOCOLOR = 0x00
    RED = 0x01
    GREEN = 0x02
    BLUE = 0x03
    YELLOW = 0x04
    CYAN = 0x05
    PURPLE = 0x06
    WHITE = 0x07
    
    @classmethod
    def from_name(cls, name: str) -> 'LEDColor':
        """Create LEDColor from string name.
        
        Args:
            name: Color name (case-insensitive)
            
        Returns:
            LEDColor enum value
            
        Raises:
            ValueError: If color name is not recognized
        """
        try:
            return cls[name.upper()]
        except KeyError:
            raise ValueError(f"Invalid LED color: {name}. Valid colors: {[c.name.lower() for c in cls]}")


@dataclass
class DeviceInfo:
    """Information about a discovered MuteMe device."""
    vendor_id: int
    product_id: int
    path: str
    manufacturer: Optional[str] = None
    product: Optional[str] = None


class DeviceError(Exception):
    """Raised when device operations fail."""
    pass


class MuteMeDevice:
    """HID device communication for MuteMe buttons."""
    
    # Supported MuteMe device variants
    MUTEME_VID = 0x20a0
    MUTEME_PIDS = [0x42da, 0x42db]  # Main MuteMe devices
    MINI_VID = 0x3603
    MINI_PIDS = [0x0001, 0x0002, 0x0003, 0x0004]  # MuteMe Mini variants
    
    def __init__(self, device: Optional[hid.device] = None, device_info: Optional[DeviceInfo] = None):
        """Initialize MuteMe device.
        
        Args:
            device: hidapi device instance
            device_info: Device information if available
        """
        self._device = device
        self._device_info = device_info
        
    @classmethod
    def discover_devices(cls) -> List[DeviceInfo]:
        """Discover all connected MuteMe devices.
        
        Returns:
            List of DeviceInfo objects for found devices
        """
        devices = []
        
        try:
            # Enumerate all HID devices
            hid_devices = hid.enumerate()
            logger.debug("Enumerated HID devices", count=len(hid_devices))
            
            for device in hid_devices:
                vid = device['vendor_id']
                pid = device['product_id']
                
                # Check if this is a supported MuteMe device
                if cls._is_muteme_device(vid, pid):
                    path = device['path'].decode('utf-8') if isinstance(device['path'], bytes) else device['path']
                    device_info = DeviceInfo(
                        vendor_id=vid,
                        product_id=pid,
                        path=path,
                        manufacturer=device.get('manufacturer_string'),
                        product=device.get('product_string')
                    )
                    devices.append(device_info)
                    logger.info("Found MuteMe device", 
                              vendor_id=f"0x{vid:04x}", 
                              product_id=f"0x{pid:04x}",
                              path=path,
                              product=device_info.product)
                    
        except Exception as e:
            logger.error("Failed to enumerate HID devices", error=str(e))
            raise DeviceError(f"Device enumeration failed: {e}")
            
        return devices
    
    @classmethod
    def _is_muteme_device(cls, vendor_id: int, product_id: int) -> bool:
        """Check if device is a supported MuteMe variant.
        
        Args:
            vendor_id: USB vendor ID
            product_id: USB product ID
            
        Returns:
            True if device is supported MuteMe variant
        """
        return (vendor_id == cls.MUTEME_VID and product_id in cls.MUTEME_PIDS) or \
               (vendor_id == cls.MINI_VID and product_id in cls.MINI_PIDS)
    
    @classmethod
    def connect(cls, device_path: str) -> 'MuteMeDevice':
        """Connect to a specific MuteMe device.
        
        Args:
            device_path: Device path (e.g., '/dev/hidraw0')
            
        Returns:
            Connected MuteMeDevice instance
            
        Raises:
            DeviceError: If connection fails
        """
        try:
            logger.info("Connecting to MuteMe device", path=device_path)
            
            # Create hidapi device instance
            device = hid.device()
            
            # Open connection to device
            device.open_path(device_path.encode('utf-8'))
            
            # Get device info for logging
            device_info = None
            for info in cls.discover_devices():
                if info.path == device_path:
                    device_info = info
                    break
                    
            logger.info("Successfully connected to MuteMe device", 
                       path=device_path,
                       vendor_id=f"0x{device_info.vendor_id:04x}" if device_info else "unknown",
                       product_id=f"0x{device_info.product_id:04x}" if device_info else "unknown")
            
            return cls(device, device_info)
            
        except Exception as e:
            logger.error("Failed to connect to MuteMe device", path=device_path, error=str(e))
            raise DeviceError(f"Failed to connect to device {device_path}: {e}")
    
    def disconnect(self) -> None:
        """Close device connection."""
        if self._device:
            try:
                self._device.close()
                logger.info("Disconnected from MuteMe device", path=self._device_info.path if self._device_info else "unknown")
            except Exception as e:
                logger.warning("Error closing device connection", error=str(e))
            finally:
                self._device = None
    
    def is_connected(self) -> bool:
        """Check if device is connected.
        
        Returns:
            True if device is connected
        """
        return self._device is not None
    
    def get_device_info(self) -> Optional[DeviceInfo]:
        """Get device information.
        
        Returns:
            DeviceInfo if available, None otherwise
        """
        return self._device_info
    
    def read(self, size: int, timeout_ms: int = 1000) -> bytes:
        """Read data from device.
        
        Args:
            size: Number of bytes to read
            timeout_ms: Read timeout in milliseconds
            
        Returns:
            Raw bytes read from device
            
        Raises:
            DeviceError: If read fails
        """
        if not self.is_connected():
            raise DeviceError("Device not connected")
            
        try:
            data = self._device.read(size, timeout_ms)
            logger.debug("Read data from device", size=len(data), timeout_ms=timeout_ms)
            return bytes(data)
        except Exception as e:
            logger.error("Failed to read from device", error=str(e))
            raise DeviceError(f"Device read failed: {e}")
    
    def write(self, data: bytes) -> None:
        """Write data to device.
        
        Args:
            data: Bytes to write to device
            
        Raises:
            DeviceError: If write fails
        """
        if not self.is_connected():
            raise DeviceError("Device not connected")
            
        try:
            self._device.write(list(data))
            logger.debug("Wrote data to device", size=len(data))
        except Exception as e:
            logger.error("Failed to write to device", error=str(e))
            raise DeviceError(f"Device write failed: {e}")
    
    def set_led_color(self, color: LEDColor) -> None:
        """Set LED color on the device.
        
        Args:
            color: LED color to set
            
        Raises:
            DeviceError: If device not connected or write fails
        """
        if not self.is_connected():
            raise DeviceError("Device not connected")
            
        try:
            # MuteMe uses 2-byte HID reports for LED control
            # Byte 0: Report ID (0x01 for LED control)
            # Byte 1: Color value
            report = bytes([0x01, color.value])
            self.write(report)
            logger.info("Set LED color", color=color.name, value=color.value)
        except Exception as e:
            logger.error("Failed to set LED color", color=color.name, error=str(e))
            raise DeviceError(f"LED control failed: {e}")
    
    def set_led_color_by_name(self, color_name: str) -> None:
        """Set LED color by name.
        
        Args:
            color_name: Name of color to set
            
        Raises:
            ValueError: If color name is invalid
            DeviceError: If device operation fails
        """
        color = LEDColor.from_name(color_name)
        self.set_led_color(color)
    
    @classmethod
    def check_device_permissions(cls, device_path: str) -> bool:
        """Check if we have read/write permissions for the device.
        
        Args:
            device_path: Path to the HID device
            
        Returns:
            True if we have permissions, False otherwise
        """
        try:
            return os.access(device_path, os.R_OK | os.W_OK)
        except OSError:
            return False
    
    @classmethod
    def get_device_permissions_error(cls, device_path: str) -> str:
        """Get detailed error message about device permissions.
        
        Args:
            device_path: Path to the HID device
            
        Returns:
            Detailed error message with permission information
        """
        try:
            device_stat = os.stat(device_path)
            mode = device_stat.st_mode
            uid = device_stat.st_uid
            gid = device_stat.st_gid
            
            # Get user and group names
            try:
                user_name = pwd.getpwuid(uid).pw_name
            except KeyError:
                user_name = str(uid)
                
            try:
                group_name = grp.getgrgid(gid).gr_name
            except KeyError:
                group_name = str(gid)
            
            # Check current user
            current_uid = os.getuid()
            current_user = pwd.getpwuid(current_uid).pw_name
            
            # Check permissions
            readable = bool(mode & stat.S_IRUSR) or bool(mode & stat.S_IRGRP) or bool(mode & stat.S_IROTH)
            writable = bool(mode & stat.S_IWUSR) or bool(mode & stat.S_IWGRP) or bool(mode & stat.S_IWOTH)
            
            error_msg = (
                f"Cannot access device {device_path}.\n"
                f"Device permissions: {oct(mode)} owned by {user_name}:{group_name}\n"
                f"Current user: {current_user} (UID: {current_uid})\n"
                f"Device is readable: {readable}, writable: {writable}"
            )
            
            # Suggest fixes
            if not readable or not writable:
                error_msg += "\n\nSuggested fixes:\n"
                error_msg += "1. Add your user to the plugdev group: sudo usermod -a -G plugdev $USER\n"
                error_msg += "2. Install UDEV rules for MuteMe devices\n"
                error_msg += "3. Run with sudo (not recommended for regular use)\n"
                error_msg += "4. Change device permissions: sudo chmod 666 " + device_path
            
            return error_msg
            
        except OSError as e:
            return f"Device {device_path} not found or inaccessible: {e}"
        except Exception as e:
            return f"Error checking device permissions for {device_path}: {e}"
