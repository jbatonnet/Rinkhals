import importlib.util
import sys
import types
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "files/4-apps/home/rinkhals/apps/40-moonraker/mmu_ace.py"
)
MODULE_NAME = "testsupport.moonraker.components.mmu_ace"
COMMON_NAME = "testsupport.moonraker.common"


class DummyTask:
    def __init__(self, coro):
        self._coro = coro
        coro.close()

    def cancel(self):
        return None

    def done(self):
        return True


class DummyEventLoop:
    def create_task(self, coro):
        return DummyTask(coro)


class DummyKlippyApis:
    async def query_objects(self, *args, **kwargs):
        return {}


class DummyKlippyConnection:
    async def request(self, *args, **kwargs):
        return {}


class DummyServer:
    error = RuntimeError

    def __init__(self):
        self.events = []
        self._eventloop = DummyEventLoop()
        self._components = {
            "klippy_apis": DummyKlippyApis(),
            "klippy_connection": DummyKlippyConnection(),
        }

    def get_event_loop(self):
        return self._eventloop

    def lookup_component(self, name):
        return self._components[name]

    def send_event(self, name, payload):
        self.events.append((name, payload))


def _ensure_package(name: str):
    if name not in sys.modules:
        package = types.ModuleType(name)
        package.__path__ = []
        sys.modules[name] = package
    return sys.modules[name]


def load_mmu_ace_module():
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]

    _ensure_package("testsupport")
    _ensure_package("testsupport.moonraker")
    _ensure_package("testsupport.moonraker.components")

    common_module = types.ModuleType(COMMON_NAME)
    common_module.WebRequest = type("WebRequest", (), {})
    common_module.APITransport = type("APITransport", (), {})
    common_module.RequestType = type("RequestType", (), {})
    sys.modules[COMMON_NAME] = common_module

    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MmuAceControllerSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_mmu_ace_module()

    def setUp(self):
        self.original_create_task = self.module.asyncio.create_task
        self.module.asyncio.create_task = lambda coro: DummyTask(coro)
        self.server = DummyServer()
        self.controller = self.module.MmuAceController(self.server, host=None)
        self.controller.ace = self.module.MmuAce()
        self.controller._handle_status_update = lambda *args, **kwargs: None

    def tearDown(self):
        self.module.asyncio.create_task = self.original_create_task

    def _build_filament_hub(self, current_filament: str):
        return {
            "current_filament": current_filament,
            "filament_hubs": [
                {
                    "id": 0,
                    "status": "ready",
                    "temp": 25,
                    "slots": [
                        {"index": 0, "status": "empty", "sku": "", "type": "", "color": [0, 0, 0], "rfid": 1, "source": 3},
                        {"index": 1, "status": "ready", "sku": "", "type": "PLA", "color": [255, 255, 255], "rfid": 1, "source": 2},
                        {"index": 2, "status": "empty", "sku": "", "type": "", "color": [0, 0, 0], "rfid": 1, "source": 3},
                        {"index": 3, "status": "empty", "sku": "", "type": "", "color": [0, 0, 0], "rfid": 1, "source": 3},
                    ],
                }
            ],
        }

    def test_refresh_syncs_loaded_gate_and_widget_state(self):
        self.controller._set_ace_status(self._build_filament_hub("0-1"))

        self.assertEqual(self.controller.ace.loaded_gate, 1)
        self.assertEqual(self.controller.ace.gate, 1)
        self.assertEqual(self.controller.ace.tool, 1)
        self.assertEqual(self.controller.ace.filament.pos, self.module.FILAMENT_POS_LOADED)

        status = self.controller.get_status()
        self.assertEqual(status.mmu.gate, 1)
        self.assertEqual(status.mmu.tool, 1)
        self.assertEqual(status.mmu.filament_pos, self.module.FILAMENT_POS_LOADED)
        self.assertFalse(status.mmu.active_filament.empty)

    def test_refresh_clears_loaded_gate_when_hardware_reports_empty(self):
        self.controller.ace.loaded_gate = 1
        self.controller.ace.gate = 1
        self.controller.ace.tool = 1
        self.controller.ace.filament.pos = self.module.FILAMENT_POS_LOADED

        self.controller._set_ace_status(self._build_filament_hub(""))

        self.assertEqual(self.controller.ace.loaded_gate, self.module.TOOL_GATE_UNKNOWN)
        self.assertEqual(self.controller.ace.gate, self.module.TOOL_GATE_UNKNOWN)
        self.assertEqual(self.controller.ace.tool, self.module.TOOL_GATE_UNKNOWN)
        self.assertEqual(self.controller.ace.filament.pos, self.module.FILAMENT_POS_UNLOADED)

        status = self.controller.get_status()
        self.assertEqual(status.mmu.filament_pos, self.module.FILAMENT_POS_UNLOADED)
        self.assertTrue(status.mmu.active_filament.empty)


class MmuAcePartialUpdateTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_mmu_ace_module()

    def setUp(self):
        self.original_create_task = self.module.asyncio.create_task
        self.module.asyncio.create_task = lambda coro: DummyTask(coro)
        self.server = DummyServer()
        self.controller = self.module.MmuAceController(self.server, host=None)
        self.controller.ace = self.module.MmuAce()
        self.status_updates = []
        self.controller._handle_status_update = lambda *args, **kwargs: self.status_updates.append(kwargs)

    def tearDown(self):
        self.module.asyncio.create_task = self.original_create_task

    async def test_partial_current_filament_update_syncs_loaded_state(self):
        await self.controller._handle_mmu_ace_status_update(
            {"filament_hub": {"current_filament": "0-0"}},
            0.0,
        )

        self.assertEqual(self.controller.ace.loaded_gate, 0)
        self.assertEqual(self.controller.ace.gate, 0)
        self.assertEqual(self.controller.ace.tool, 0)
        self.assertEqual(self.controller.ace.filament.pos, self.module.FILAMENT_POS_LOADED)
        self.assertEqual(self.status_updates, [{"force": True}])

    async def test_partial_empty_current_filament_clears_loaded_state(self):
        self.controller.ace.loaded_gate = 1
        self.controller.ace.gate = 1
        self.controller.ace.tool = 1
        self.controller.ace.filament.pos = self.module.FILAMENT_POS_LOADED

        await self.controller._handle_mmu_ace_status_update(
            {"filament_hub": {"current_filament": ""}},
            0.0,
        )

        self.assertEqual(self.controller.ace.loaded_gate, self.module.TOOL_GATE_UNKNOWN)
        self.assertEqual(self.controller.ace.gate, self.module.TOOL_GATE_UNKNOWN)
        self.assertEqual(self.controller.ace.tool, self.module.TOOL_GATE_UNKNOWN)
        self.assertEqual(self.controller.ace.filament.pos, self.module.FILAMENT_POS_UNLOADED)
        self.assertEqual(self.status_updates, [{"force": True}])

    async def test_partial_empty_current_filament_preserves_unloaded_selection(self):
        self.controller.ace.loaded_gate = self.module.TOOL_GATE_UNKNOWN
        self.controller.ace.gate = 2
        self.controller.ace.tool = 2
        self.controller.ace.filament.pos = self.module.FILAMENT_POS_UNLOADED

        await self.controller._handle_mmu_ace_status_update(
            {"filament_hub": {"current_filament": ""}},
            0.0,
        )

        self.assertEqual(self.controller.ace.loaded_gate, self.module.TOOL_GATE_UNKNOWN)
        self.assertEqual(self.controller.ace.gate, 2)
        self.assertEqual(self.controller.ace.tool, 2)
        self.assertEqual(self.controller.ace.filament.pos, self.module.FILAMENT_POS_UNLOADED)
        self.assertEqual(self.status_updates, [{"force": True}])

    async def test_partial_update_without_current_filament_is_ignored(self):
        await self.controller._handle_mmu_ace_status_update(
            {"filament_hub": {"filament_present": 1}},
            0.0,
        )

        self.assertEqual(self.controller.ace.loaded_gate, self.module.TOOL_GATE_UNKNOWN)
        self.assertEqual(self.controller.ace.gate, self.module.TOOL_GATE_UNKNOWN)
        self.assertEqual(self.controller.ace.tool, self.module.TOOL_GATE_UNKNOWN)
        self.assertEqual(self.status_updates, [])


class MmuRecoverTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_mmu_ace_module()

    async def test_mmu_recover_rejects_unsupported_arguments(self):
        refresh_calls = []
        responses = []
        gate = types.SimpleNamespace(status=self.module.GATE_AVAILABLE, filament_name="PLA")
        patcher = self.module.MmuAcePatcher.__new__(self.module.MmuAcePatcher)
        patcher.ace_controller = types.SimpleNamespace(
            _handle_status_update=lambda **kwargs: refresh_calls.append(kwargs)
        )
        patcher.ace = types.SimpleNamespace(units=[types.SimpleNamespace(gates=[gate])])

        async def send_response(message):
            responses.append(message)

        patcher._send_gcode_response = send_response

        result = await self.module.MmuAcePatcher._on_gcode_mmu_recover(
            patcher,
            {"GATE": "1", "LOADED": "1", "TOOL": "1"},
            None,
        )

        self.assertIsNone(result)
        self.assertEqual(refresh_calls, [])
        self.assertEqual(len(responses), 1)
        self.assertIn("unsupported parameters", responses[0])

    async def test_mmu_recover_refreshes_without_arguments(self):
        refresh_calls = []
        responses = []
        gate_ready = types.SimpleNamespace(status=self.module.GATE_AVAILABLE, filament_name="PLA")
        gate_empty = types.SimpleNamespace(status=self.module.GATE_EMPTY, filament_name="")
        patcher = self.module.MmuAcePatcher.__new__(self.module.MmuAcePatcher)
        patcher.ace_controller = types.SimpleNamespace(
            _handle_status_update=lambda **kwargs: refresh_calls.append(kwargs)
        )
        patcher.ace = types.SimpleNamespace(units=[types.SimpleNamespace(gates=[gate_ready, gate_empty])])

        async def send_response(message):
            responses.append(message)

        patcher._send_gcode_response = send_response

        result = await self.module.MmuAcePatcher._on_gcode_mmu_recover(patcher, {}, None)

        self.assertIsNone(result)
        self.assertEqual(refresh_calls, [{"force": True}])
        self.assertEqual(len(responses), 1)
        self.assertIn("ACE status refreshed", responses[0])


if __name__ == "__main__":
    unittest.main()
