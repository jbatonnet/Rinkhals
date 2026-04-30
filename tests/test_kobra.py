import importlib.util
import sys
import types
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "files/4-apps/home/rinkhals/apps/40-moonraker/kobra.py"
)
MODULE_NAME = "testsupport.moonraker.components.kobra"
COMMON_NAME = "testsupport.moonraker.common"
UTILS_NAME = "testsupport.moonraker.utils"
POWER_NAME = "testsupport.moonraker.components.power"
MACHINE_NAME = "testsupport.moonraker.components.machine"


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


class DummyServer:
    error = RuntimeError

    def __init__(self):
        self._eventloop = DummyEventLoop()
        self.config = object()

    def get_event_loop(self):
        return self._eventloop

    def load_component(self, *args, **kwargs):
        return None


class DummyWebRequest:
    def __init__(self, endpoint: str):
        self._endpoint = endpoint

    def get_endpoint(self):
        return self._endpoint


def _ensure_package(name: str):
    if name not in sys.modules:
        package = types.ModuleType(name)
        package.__path__ = []
        sys.modules[name] = package
    return sys.modules[name]


def _build_machine_module():
    machine_module = types.ModuleType(MACHINE_NAME)

    class Machine:
        def __init__(self):
            self.inside_container = False
            self.system_info = {"virtualization": {"virt_identifier": "none"}}
            self.server = DummyServer()
            self.original_calls = []

        async def _handle_machine_request(self, web_request):
            endpoint = web_request.get_endpoint()
            self.original_calls.append(endpoint)
            return f"original:{endpoint}"

    machine_module.Machine = Machine
    sys.modules[MACHINE_NAME] = machine_module
    return machine_module


def load_kobra_module():
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]

    _ensure_package("testsupport")
    _ensure_package("testsupport.moonraker")
    _ensure_package("testsupport.moonraker.components")
    _ensure_package("paho")
    _ensure_package("paho.mqtt")

    client_module = types.ModuleType("paho.mqtt.client")
    client_module.Client = type("Client", (), {})
    sys.modules["paho.mqtt.client"] = client_module

    common_module = types.ModuleType(COMMON_NAME)
    common_module.WebRequest = DummyWebRequest
    sys.modules[COMMON_NAME] = common_module

    utils_module = types.ModuleType(UTILS_NAME)
    utils_module.Sentinel = types.SimpleNamespace(MISSING=object())
    sys.modules[UTILS_NAME] = utils_module

    power_module = types.ModuleType(POWER_NAME)
    power_module.PowerDevice = type("PowerDevice", (), {})
    sys.modules[POWER_NAME] = power_module

    _build_machine_module()

    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class KobraMachineRebootPatchTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_kobra_module()

    def setUp(self):
        self.machine_module = _build_machine_module()
        self.kobra = self.module.Kobra.__new__(self.module.Kobra)
        self.kobra.server = DummyServer()
        self.kobra.patch_machine_power_actions()

    async def test_reboot_request_is_intercepted_and_scheduled(self):
        scheduled = []
        self.kobra._schedule_native_machine_action = lambda action: scheduled.append(action)

        machine = self.machine_module.Machine()
        result = await machine._handle_machine_request(DummyWebRequest("/machine/reboot"))

        self.assertEqual(result, "ok")
        self.assertEqual(scheduled, ["reboot"])
        self.assertEqual(machine.original_calls, [])

    async def test_shutdown_request_is_intercepted_and_scheduled(self):
        scheduled = []
        self.kobra._schedule_native_machine_action = lambda action: scheduled.append(action)

        machine = self.machine_module.Machine()
        result = await machine._handle_machine_request(DummyWebRequest("/machine/shutdown"))

        self.assertEqual(result, "ok")
        self.assertEqual(scheduled, ["poweroff"])
        self.assertEqual(machine.original_calls, [])

    async def test_non_power_request_falls_back_to_original_handler(self):
        scheduled = []
        self.kobra._schedule_native_machine_action = lambda action: scheduled.append(action)

        machine = self.machine_module.Machine()
        result = await machine._handle_machine_request(DummyWebRequest("/machine/restart"))

        self.assertEqual(result, "original:/machine/restart")
        self.assertEqual(scheduled, [])
        self.assertEqual(machine.original_calls, ["/machine/restart"])

    async def test_reboot_request_preserves_container_guard(self):
        scheduled = []
        self.kobra._schedule_native_machine_action = lambda action: scheduled.append(action)

        machine = self.machine_module.Machine()
        machine.inside_container = True
        machine.system_info["virtualization"]["virt_identifier"] = "docker"

        with self.assertRaisesRegex(RuntimeError, "Cannot reboot from within a docker container"):
            await machine._handle_machine_request(DummyWebRequest("/machine/reboot"))

        self.assertEqual(scheduled, [])
        self.assertEqual(machine.original_calls, [])


if __name__ == "__main__":
    unittest.main()