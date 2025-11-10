"""HID device discovery and communication for MuteMe buttons."""

import grp
import os
import pwd
import stat
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import hid  # type: ignore[import-untyped]
import structlog

logger = structlog.get_logger(__name__)


class LEDColor(Enum):
    """LED color options for MuteMe devices."""

    NOCOLOR = 0x00
    RED = 0x01
    GREEN = 0x02
    YELLOW = 0x03  # Swapped: was BLUE
    BLUE = 0x04  # Swapped: was YELLOW
    PURPLE = 0x05  # Swapped: was CYAN
    CYAN = 0x06  # Swapped: was PURPLE
    WHITE = 0x07

    @classmethod
    def from_name(cls, name: str) -> "LEDColor":
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
            raise ValueError(
                f"Invalid LED color: {name}. Valid colors: {[c.name.lower() for c in cls]}"
            ) from None


@dataclass
class DeviceInfo:
    """Information about a discovered MuteMe device."""

    vendor_id: int
    product_id: int
    path: str
    manufacturer: str | None = None
    product: str | None = None


class DeviceError(Exception):
    """Raised when device operations fail."""

    pass


class MuteMeDevice:
    """HID device communication for MuteMe buttons."""

    # Supported MuteMe device variants
    MUTEME_VID = 0x20A0
    MUTEME_PIDS = [0x42DA, 0x42DB]  # Main MuteMe devices
    MINI_VID = 0x3603
    MINI_PIDS = [0x0001, 0x0002, 0x0003, 0x0004]  # MuteMe Mini variants

    def __init__(self, device: hid.device | None = None, device_info: DeviceInfo | None = None):
        """Initialize MuteMe device.

        Args:
            device: hidapi device instance
            device_info: Device information if available
        """
        self._device = device
        self._device_info = device_info

    @classmethod
    def discover_devices(cls) -> list[DeviceInfo]:
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
                vid = device["vendor_id"]
                pid = device["product_id"]

                # Check if this is a supported MuteMe device
                if cls._is_muteme_device(vid, pid):
                    path = (
                        device["path"].decode("utf-8")
                        if isinstance(device["path"], bytes)
                        else device["path"]
                    )
                    device_info = DeviceInfo(
                        vendor_id=vid,
                        product_id=pid,
                        path=path,
                        manufacturer=device.get("manufacturer_string"),
                        product=device.get("product_string"),
                    )
                    devices.append(device_info)
                    logger.info(
                        "Found MuteMe device",
                        vendor_id=f"0x{vid:04x}",
                        product_id=f"0x{pid:04x}",
                        path=path,
                        product=device_info.product,
                    )

        except Exception as e:
            logger.error("Failed to enumerate HID devices", error=str(e))
            raise DeviceError(f"Device enumeration failed: {e}") from e

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
        return (vendor_id == cls.MUTEME_VID and product_id in cls.MUTEME_PIDS) or (
            vendor_id == cls.MINI_VID and product_id in cls.MINI_PIDS
        )

    @classmethod
    def connect(cls, device_path: str) -> "MuteMeDevice":
        """Connect to a specific MuteMe device.

        Args:
            device_path: Device path from hid.enumerate() (USB path, not /dev/hidraw*)

        Returns:
            Connected MuteMeDevice instance

        Raises:
            DeviceError: If connection fails
        """
        try:
            logger.info("Connecting to MuteMe device", path=device_path)

            # Create hidapi device instance
            device = hid.device()

            # Try to open using the path from enumerate()
            # The path should be bytes
            path_bytes = (
                device_path.encode("utf-8") if isinstance(device_path, str) else device_path
            )
            logger.debug(
                f"Attempting to open device: path_bytes={path_bytes}, path_type={type(path_bytes)}"
            )

            device.open_path(path_bytes)

            logger.debug("Device opened successfully, verifying connection")

            # Get device info for logging
            device_info = None
            for info in cls.discover_devices():
                if info.path == device_path:
                    device_info = info
                    break

            logger.info(
                "Successfully connected to MuteMe device",
                path=device_path,
                vendor_id=f"0x{device_info.vendor_id:04x}" if device_info else "unknown",
                product_id=f"0x{device_info.product_id:04x}" if device_info else "unknown",
            )

            return cls(device, device_info)

        except Exception as e:
            logger.error(
                "Failed to connect to MuteMe device",
                path=device_path,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Provide helpful error message
            error_msg = f"Failed to connect to device {device_path}: {e}"
            if "open failed" in str(e).lower():
                error_msg += "\n\nTroubleshooting:"
                error_msg += "\n• Device may be in use by another process"
                error_msg += "\n• Try unplugging and replugging the device"
                error_msg += "\n• Check if another instance is running: "
                error_msg += "muteme-btn-control kill-instances"
                error_msg += "\n• Verify device permissions: just check-device"
                error_msg += (
                    f"\n• Path format: {device_path} "
                    "(should be USB path from enumerate, not /dev/hidraw*)"
                )
            raise DeviceError(error_msg) from e

    @classmethod
    def connect_by_vid_pid(cls, vendor_id: int, product_id: int) -> "MuteMeDevice":
        """Connect to a MuteMe device by VID/PID (alternative method).

        Args:
            vendor_id: USB Vendor ID
            product_id: USB Product ID

        Returns:
            Connected MuteMeDevice instance

        Raises:
            DeviceError: If connection fails
        """
        try:
            logger.info(
                "Connecting to MuteMe device by VID/PID",
                vendor_id=f"0x{vendor_id:04x}",
                product_id=f"0x{product_id:04x}",
            )

            # Create hidapi device instance
            device = hid.device()

            # Try to open using VID/PID
            device.open(vendor_id, product_id)

            logger.debug("Device opened successfully by VID/PID")

            # Get device info for logging
            device_info = None
            for info in cls.discover_devices():
                if info.vendor_id == vendor_id and info.product_id == product_id:
                    device_info = info
                    break

            logger.info(
                "Successfully connected to MuteMe device by VID/PID",
                vendor_id=f"0x{vendor_id:04x}",
                product_id=f"0x{product_id:04x}",
                path=device_info.path if device_info else "unknown",
            )

            return cls(device, device_info)

        except Exception as e:
            logger.error(
                "Failed to connect to MuteMe device by VID/PID",
                vendor_id=f"0x{vendor_id:04x}",
                product_id=f"0x{product_id:04x}",
                error=str(e),
            )
            raise DeviceError(
                f"Failed to connect to device VID:0x{vendor_id:04x} PID:0x{product_id:04x}: {e}"
            ) from e

    def disconnect(self) -> None:
        """Close device connection."""
        if self._device:
            try:
                self._device.close()
                logger.info(
                    "Disconnected from MuteMe device",
                    path=self._device_info.path if self._device_info else "unknown",
                )
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

    def get_device_info(self) -> DeviceInfo | None:
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

        if self._device is None:
            raise DeviceError("Device not connected")

        try:
            data = self._device.read(size, timeout_ms)  # type: ignore[union-attr]
            logger.debug("Read data from device", size=len(data), timeout_ms=timeout_ms)
            return bytes(data)
        except Exception as e:
            logger.error("Failed to read from device", error=str(e))
            raise DeviceError(f"Device read failed: {e}") from e

    def write(self, data: bytes) -> None:
        """Write data to device.

        Args:
            data: Bytes to write to device

        Raises:
            DeviceError: If write fails
        """
        if not self.is_connected():
            raise DeviceError("Device not connected")

        if self._device is None:
            raise DeviceError("Device not connected")

        try:
            self._device.write(data)  # type: ignore[union-attr]
            logger.debug("Wrote data to device", size=len(data))
        except Exception as e:
            logger.error("Failed to write to device", error=str(e))
            raise DeviceError(f"Device write failed: {e}") from e

    async def read_events(self) -> list[Any]:
        """Read button events from the device (non-blocking).

        Returns:
            List of button events. Each event has:
            - type: "press" or "release"
            - timestamp: datetime object

        Note:
            This method reads available data without blocking. If no data is available,
            it returns an empty list.
        """
        if not self.is_connected():
            return []

        if self._device is None:
            return []

        events = []
        try:
            # MuteMe sends 4-byte HID interrupt reports
            # Byte 3 (index 3) contains the button state: 0x00 = released, 0x01 = pressed
            data = self.read(size=4, timeout_ms=10)

            if len(data) >= 4:
                button_byte = data[3]
                event_type = "press" if button_byte == 0x01 else "release"
                timestamp = datetime.now()

                # Create a simple event object
                @dataclass
                class DeviceEvent:
                    type: str
                    timestamp: datetime

                events.append(DeviceEvent(type=event_type, timestamp=timestamp))
                logger.info(
                    f"Button event detected: {event_type} "
                    f"(raw data: {data.hex()}, button byte: 0x{button_byte:02x})"
                )

        except DeviceError:
            # No data available or read timeout - this is normal
            pass
        except Exception as e:
            logger.warning(f"Error reading events: {e}")

        return events

    def set_led_color(
        self,
        color: LEDColor,
        use_feature_report: bool = False,
        report_format: str = "report_id_0",
        brightness: str = "normal",
    ) -> None:
        """Set LED color on the device.

        Args:
            color: LED color to set
            use_feature_report: If True, use send_feature_report instead of write
            report_format: Report format to use:
                - "standard": [0x01, color_value]
                - "no_report_id": [color_value] (no report ID)
                - "report_id_0": [0x00, color_value] (report ID 0) - DEFAULT (works on MuteMe)
                - "report_id_2": [0x02, color_value] (report ID 2)
                - "padded": [0x01, color_value, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00] (8 bytes)
            brightness: Brightness/effect level:
                - "normal": Base color value (default)
                - "dim": Add 0x10 to color value
                - "fast_pulse": Add 0x20 to color value
                - "slow_pulse": Add 0x30 to color value
                - "flashing": Software-side animation (rapid on/off cycles)
                  Note: Hardware flashing (0x40 offset) may not be supported by all devices.
                  This implementation uses software animation for reliability.

        Raises:
            DeviceError: If device not connected or write fails
        """
        if not self.is_connected():
            raise DeviceError("Device not connected")

        def _build_report(raw_value: int) -> bytes:
            """Build report bytes based on report_format.

            Args:
                raw_value: Color value to include in report

            Returns:
                Report bytes according to report_format
            """
            if report_format == "no_report_id":
                return bytes([raw_value])
            elif report_format == "report_id_0":
                return bytes([0x00, raw_value])
            elif report_format == "report_id_2":
                return bytes([0x02, raw_value])
            elif report_format == "padded":
                return bytes([0x01, raw_value, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            else:  # standard
                return bytes([0x01, raw_value])

        def _send_report(report: bytes) -> None:
            """Send report using appropriate transport method.

            Args:
                report: Report bytes to send
            """
            if use_feature_report:
                self._device.send_feature_report(list(report))  # type: ignore[union-attr]
            else:
                self.write(report)

        try:
            # Apply brightness/effect offset
            color_value = color.value
            if brightness == "dim":
                color_value = color.value | 0x10
            elif brightness == "fast_pulse":
                color_value = color.value | 0x20
            elif brightness == "slow_pulse":
                color_value = color.value | 0x30
            elif brightness == "flashing":
                # Software-side flashing animation (device firmware may not support 0x40 offset)
                # This creates a rapid on/off flashing effect
                flash_duration = 0.15  # Duration for each flash cycle (faster than fast_pulse)
                flash_cycles = 20  # Number of cycles for flashing animation

                for _ in range(flash_cycles):
                    # Turn LED on with full brightness
                    report_on = _build_report(color.value)
                    _send_report(report_on)
                    time.sleep(flash_duration)
                    # Turn LED off
                    report_off = _build_report(LEDColor.NOCOLOR.value)
                    _send_report(report_off)
                    time.sleep(flash_duration * 0.3)  # Shorter off period for faster flash

                # Leave LED on at end of flashing
                color_value = color.value
                final_report = _build_report(color_value)
                _send_report(final_report)
                logger.debug(
                    "Set LED color (software flashing)",
                    color=color.name,
                    value=color_value,
                    format=report_format,
                    brightness=brightness,
                    report=final_report.hex(),
                )
                return
            else:
                # Normal brightness or other modes
                pass

            # Build report based on format
            report = _build_report(color_value)

            # Send report using appropriate transport
            _send_report(report)

            # Log the operation
            logger.debug(
                "Set LED color",
                color=color.name,
                value=color_value,
                format=report_format,
                brightness=brightness,
                report=report.hex(),
            )
        except Exception as e:
            logger.error("Failed to set LED color", color=color.name, error=str(e))
            raise DeviceError(f"LED control failed: {e}") from e

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
    def _find_hidraw_device(cls, vendor_id: int, product_id: int) -> str | None:
        """Find the /dev/hidraw* device file for a given vendor/product ID.

        Args:
            vendor_id: USB vendor ID
            product_id: USB product ID

        Returns:
            Path to hidraw device (e.g., '/dev/hidraw0') or None if not found
        """
        import glob

        # Check all hidraw devices by reading sysfs uevent
        for hidraw_path in sorted(glob.glob("/dev/hidraw*")):
            try:
                # Extract hidraw number (e.g., "0" from "/dev/hidraw0")
                hidraw_num = hidraw_path.replace("/dev/hidraw", "")

                # Read uevent file which contains HID_ID with vendor:product format
                uevent_path = f"/sys/class/hidraw/hidraw{hidraw_num}/device/uevent"

                try:
                    with open(uevent_path) as f:
                        uevent_content = f.read()

                    # Parse HID_ID line (format: HID_ID=0003:000005AC:00008242)
                    # Format is: bus:vendor:product
                    for line in uevent_content.split("\n"):
                        if line.startswith("HID_ID="):
                            hid_id = line.split("=", 1)[1]
                            parts = hid_id.split(":")
                            if len(parts) >= 3:
                                vid_hex = parts[1]
                                pid_hex = parts[2]

                                try:
                                    vid = int(vid_hex, 16)
                                    pid = int(pid_hex, 16)

                                    if vid == vendor_id and pid == product_id:
                                        return hidraw_path
                                except ValueError:
                                    continue
                except (OSError, FileNotFoundError):
                    continue
            except (OSError, ValueError):
                continue

        return None

    @classmethod
    def check_device_permissions(cls, device_path: str) -> bool:
        """Check if we have read/write permissions for the device.

        Args:
            device_path: Path to the HID device (USB path or /dev/hidraw*)

        Returns:
            True if we have permissions, False otherwise
        """
        # If it's already a /dev/hidraw* path, check it directly
        if device_path.startswith("/dev/hidraw"):
            try:
                return os.access(device_path, os.R_OK | os.W_OK)
            except OSError:
                return False

        # Otherwise, it's a USB device path - we need to find the hidraw device
        # But we don't have vendor/product ID here, so we can't map it
        # For now, try to check if the path exists (it won't for USB paths)
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
            readable = (
                bool(mode & stat.S_IRUSR) or bool(mode & stat.S_IRGRP) or bool(mode & stat.S_IROTH)
            )
            writable = (
                bool(mode & stat.S_IWUSR) or bool(mode & stat.S_IWGRP) or bool(mode & stat.S_IWOTH)
            )

            error_msg = (
                f"Cannot access device {device_path}.\n"
                f"Device permissions: {oct(mode)} owned by {user_name}:{group_name}\n"
                f"Current user: {current_user} (UID: {current_uid})\n"
                f"Device is readable: {readable}, writable: {writable}"
            )

            # Suggest fixes
            if not readable or not writable:
                error_msg += "\n\nSuggested fixes:\n"
                error_msg += (
                    "1. Add your user to the plugdev group: sudo usermod -a -G plugdev $USER\n"
                )
                error_msg += "2. Install UDEV rules for MuteMe devices\n"
                error_msg += "3. Run with sudo (not recommended for regular use)\n"
                error_msg += "4. Change device permissions: sudo chmod 666 " + device_path

            return error_msg

        except OSError as e:
            return f"Device {device_path} not found or inaccessible: {e}"
        except Exception as e:
            return f"Error checking device permissions for {device_path}: {e}"
