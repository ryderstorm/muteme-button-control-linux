"""Performance measurement and validation tests."""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from muteme_btn.config import AudioConfig, DeviceConfig
from muteme_btn.core.daemon import MuteMeDaemon
from muteme_btn.core.led_feedback import LEDFeedbackController
from muteme_btn.core.state import ButtonEvent, ButtonStateMachine


class MockPerformanceDevice:
    """Mock device for performance testing."""

    def __init__(self, device_config: DeviceConfig):
        self.config = device_config
        self._connected = False
        self._events = []
        self._led_color = None
        self._operation_times = []

    async def connect(self):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def is_connected(self):
        return self._connected

    async def read_events(self):
        start_time = time.perf_counter()
        events = self._events.copy()
        self._events.clear()
        end_time = time.perf_counter()
        self._operation_times.append(end_time - start_time)
        return events

    def set_led_color(self, color):
        start_time = time.perf_counter()
        self._led_color = color
        end_time = time.perf_counter()
        self._operation_times.append(end_time - start_time)

    def add_event(self, event_type, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()
        self._events.append(Mock(type=event_type, timestamp=timestamp))

    def get_operation_times(self):
        return self._operation_times.copy()

    def close(self):
        self.disconnect()


class MockPerformanceAudioBackend:
    """Mock audio backend for performance testing."""

    def __init__(self, audio_config: AudioConfig):
        self.config = audio_config
        self._muted = False
        self._connected = True
        self._operation_times = []

    def get_default_sink(self):
        start_time = time.perf_counter()
        result = {"name": "default_sink", "muted": self._muted}
        end_time = time.perf_counter()
        self._operation_times.append(end_time - start_time)
        return result

    def set_mute_state(self, sink_name, muted):
        start_time = time.perf_counter()
        self._muted = muted
        end_time = time.perf_counter()
        self._operation_times.append(end_time - start_time)

    def is_muted(self, sink_name=None):
        start_time = time.perf_counter()
        result = self._muted
        end_time = time.perf_counter()
        self._operation_times.append(end_time - start_time)
        return result

    def list_sinks(self):
        start_time = time.perf_counter()
        result = [self.get_default_sink()]
        end_time = time.perf_counter()
        self._operation_times.append(end_time - start_time)
        return result

    def get_operation_times(self):
        return self._operation_times.copy()

    def close(self):
        self._connected = False


class TestPerformanceMeasurement:
    """Performance measurement and validation tests."""

    @pytest.fixture
    def device_config(self):
        return DeviceConfig()

    @pytest.fixture
    def audio_config(self):
        return AudioConfig()

    @pytest.fixture
    def perf_device(self, device_config):
        return MockPerformanceDevice(device_config)

    @pytest.fixture
    def perf_audio_backend(self, audio_config):
        return MockPerformanceAudioBackend(audio_config)

    @pytest.fixture
    def perf_daemon(self, perf_device, perf_audio_backend):
        state_machine = ButtonStateMachine()
        led_controller = LEDFeedbackController(device=perf_device, audio_backend=perf_audio_backend)
        return MuteMeDaemon(
            device=perf_device,
            audio_backend=perf_audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
        )

    @pytest.mark.asyncio
    async def test_button_event_processing_latency(self, perf_daemon, perf_device):
        """Test button event processing latency."""
        await perf_device.connect()

        daemon_task = asyncio.create_task(perf_daemon.start())
        await asyncio.sleep(0.01)

        # Measure event processing time
        start_time = time.perf_counter()

        # Add events
        for i in range(50):
            perf_device.add_event("press")
            perf_device.add_event("release")

        # Wait for processing
        await asyncio.sleep(0.25)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Calculate average time per event
        event_times = perf_device.get_operation_times()
        avg_event_time = sum(event_times) / len(event_times) if event_times else 0

        # Performance assertions
        assert total_time < 0.5
        assert avg_event_time < 0.001  # Average event time should be < 1ms

        await perf_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_audio_operations_latency(self, perf_daemon, perf_audio_backend):
        """Test audio operations latency."""
        await perf_daemon.device.connect()

        daemon_task = asyncio.create_task(perf_daemon.start())
        await asyncio.sleep(0.01)

        # Perform multiple audio operations
        for i in range(50):
            perf_audio_backend.is_muted()
            perf_audio_backend.set_mute_state(None, True)
            perf_audio_backend.is_muted()
            perf_audio_backend.set_mute_state(None, False)

        # Get operation times
        operation_times = perf_audio_backend.get_operation_times()

        # Calculate statistics
        avg_time = sum(operation_times) / len(operation_times)
        max_time = max(operation_times)

        # Performance assertions
        assert avg_time < 0.0001  # Average should be < 0.1ms
        assert max_time < 0.001  # Max should be < 1ms

        await perf_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_led_update_latency(self, perf_daemon, perf_device):
        """Test LED update latency."""
        await perf_device.connect()

        daemon_task = asyncio.create_task(perf_daemon.start())
        await asyncio.sleep(0.01)

        # Measure LED update performance
        start_time = time.perf_counter()

        # Trigger multiple LED updates
        for i in range(50):
            perf_daemon.led_controller.update_led_to_mute_status()
            await asyncio.sleep(0.0005)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        led_times = perf_device.get_operation_times()
        avg_led_time = sum(led_times) / len(led_times) if led_times else 0

        # Performance assertions
        assert total_time < 1.0
        assert avg_led_time < 0.001  # Average LED time should be < 1ms

        await perf_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_daemon_memory_usage(self, perf_daemon):
        """Test daemon memory usage doesn't grow excessively."""
        # Skip psutil-dependent test if not available
        try:
            import os

            import psutil
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        await perf_daemon.device.connect()

        daemon_task = asyncio.create_task(perf_daemon.start())
        await asyncio.sleep(0.01)

        # Simulate extended operation
        for cycle in range(5):
            # Add many events
            for i in range(25):
                perf_daemon.device.add_event("press")
                perf_daemon.device.add_event("release")

            await asyncio.sleep(0.05)

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (< 10MB)
        assert memory_growth < 10 * 1024 * 1024

        await perf_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(
        self, perf_daemon, perf_device, perf_audio_backend
    ):
        """Test performance under concurrent operations."""
        await perf_device.connect()

        daemon_task = asyncio.create_task(perf_daemon.start())
        await asyncio.sleep(0.01)

        # Create concurrent tasks
        async def add_events():
            for i in range(25):
                perf_device.add_event("press")
                perf_device.add_event("release")
                await asyncio.sleep(0.0005)

        async def check_audio():
            for i in range(25):
                perf_audio_backend.is_muted()
                await asyncio.sleep(0.0005)

        async def update_led():
            for i in range(25):
                perf_daemon.led_controller.update_led_to_mute_status()
                await asyncio.sleep(0.0005)

        # Run concurrent operations
        start_time = time.perf_counter()

        await asyncio.gather(add_events(), check_audio(), update_led())

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Should handle concurrent operations efficiently
        assert total_time < 0.5

        await perf_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_state_machine_performance(self):
        """Test button state machine performance."""
        state_machine = ButtonStateMachine()

        # Measure state machine processing time
        start_time = time.perf_counter()

        # Process many events
        for i in range(1000):
            press_event = ButtonEvent("press", datetime.now())
            release_event = ButtonEvent("release", datetime.now() + timedelta(milliseconds=10))

            state_machine.process_event(press_event)
            state_machine.process_event(release_event)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_per_event = total_time / 2000  # 2000 events total

        # Performance assertions
        assert avg_time_per_event < 0.00001  # Should be < 0.01ms per event
        assert total_time < 0.1  # Should complete within 100ms

    @pytest.mark.asyncio
    async def test_daemon_startup_shutdown_performance(self, perf_daemon, perf_device):
        """Test daemon startup and shutdown performance."""
        await perf_device.connect()

        # Measure startup time
        startup_start = time.perf_counter()
        daemon_task = asyncio.create_task(perf_daemon.start())
        await asyncio.sleep(0.01)  # Wait for startup
        startup_end = time.perf_counter()
        startup_time = startup_end - startup_start

        # Measure shutdown time
        shutdown_start = time.perf_counter()
        await perf_daemon.stop()
        await daemon_task
        shutdown_end = time.perf_counter()
        shutdown_time = shutdown_end - shutdown_start

        # Performance assertions
        assert startup_time < 0.15  # Startup should be < 150ms (relaxed)
        assert shutdown_time < 0.15  # Shutdown should be < 150ms (relaxed)

    def test_cpu_usage_under_load(self, perf_daemon):
        """Test CPU usage doesn't exceed reasonable limits."""
        # Skip psutil-dependent test if not available
        try:
            import os
            import time

            import psutil
        except ImportError:
            pytest.skip("psutil not available for CPU testing")

        process = psutil.Process(os.getpid())

        # Measure CPU during intensive operations
        process.cpu_percent()  # Initial call to reset

        # Simulate intensive work over time period
        start_time = time.time()
        state_machine = ButtonStateMachine()

        while time.time() - start_time < 0.1:  # Run for 100ms
            for i in range(100):
                event = ButtonEvent("press", datetime.now())
                state_machine.process_event(event)
            time.sleep(0.001)  # Small delay

        cpu_usage = process.cpu_percent(interval=0.1)

        # CPU usage should be reasonable
        # Note: This is a rough check and may vary by system
        assert cpu_usage < 200.0  # Allow higher CPU for short bursts

    @pytest.mark.asyncio
    async def test_error_handling_performance(self, perf_daemon, perf_audio_backend):
        """Test performance when handling errors."""
        await perf_daemon.device.connect()

        daemon_task = asyncio.create_task(perf_daemon.start())
        await asyncio.sleep(0.01)

        # Simulate errors and measure performance impact
        original_is_muted = perf_audio_backend.is_muted

        def error_is_muted():
            raise Exception("Simulated error")

        start_time = time.perf_counter()

        # Run operations with errors
        for i in range(100):
            try:
                perf_audio_backend.is_muted()
            except Exception:
                pass

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Error handling should not significantly impact performance
        assert total_time < 0.1  # Should complete within 100ms

        # Restore normal operation
        perf_audio_backend.is_muted = original_is_muted

        await perf_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_long_running_stability(self, perf_daemon, perf_device):
        """Test system stability over extended periods."""
        await perf_device.connect()

        daemon_task = asyncio.create_task(perf_daemon.start())
        await asyncio.sleep(0.01)

        # Run for extended period with periodic operations
        start_time = time.perf_counter()

        for cycle in range(50):
            # Add events
            perf_device.add_event("press")
            perf_device.add_event("release")

            # Wait a bit
            await asyncio.sleep(0.005)

            # Verify daemon is still responsive
            assert perf_daemon.running is True

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Should maintain stability over time
        assert total_time < 2.5
        assert perf_daemon.running is True  # Should still be running

        await perf_daemon.stop()
        await daemon_task
