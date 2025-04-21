# Example Component
#
# Copyright (C) 2021  Eric Callahan <arksine.code@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os
import uuid
import json
import re
import time
import logging
import subprocess
import logging
import traceback
import shlex
import ast
import http.client
import asyncio

from ..confighelper import ConfigHelper
from ..server import Server
from .kobra import Kobra

from dataclasses import dataclass, asdict
from enum import Enum
from types import NoneType

from typing import (
    TYPE_CHECKING,
    Any,
    Union,
    Optional,
    Dict,
    List,
    TypeVar,
    Mapping,
    Callable,
    Coroutine
)

if TYPE_CHECKING:
    FlexCallback = Callable[..., Optional[Coroutine]]
    SubCallback = Callable[[Dict[str, Dict[str, Any]], float], Optional[Coroutine]]
    _T = TypeVar("_T")
else:
    _T = Any
    FlexCallback = Any
    SubCallback = Any

from ..utils import Sentinel
from .http_client import HttpClient, HttpResponse
from .klippy_apis import KlippyAPI

@dataclass
class ActiveFilamentStatus:
    empty: str

@dataclass
class MmuEncoderStatus:
    encoder_pos: int
    enabled: bool
    desired_headroom: int
    detection_length: int
    detection_mode: int
    flow_rate: int

@dataclass
class MmuUnitStatus:
    name: str
    vendor: str
    version: str
    num_gates: int
    first_gate: int
    selector_type: str
    variable_rotation_distances: bool
    variable_bowden_lengths: bool
    require_bowden_move: bool
    filament_always_gripped: bool
    has_bypass: bool
    multi_gear: bool

@dataclass
class MmuMachineStatus:
    num_units: int
    unit_0: MmuUnitStatus
    unit_1: MmuUnitStatus

@dataclass
class MmuToolStatus:
    material: str
    temp: int
    name: str
    in_use: bool

@dataclass
class MmuSlicerToolMapStatus:
    tools: List[MmuToolStatus]

@dataclass
class MmuStatus:
    enabled: bool
    encoder: MmuEncoderStatus
    num_gates: int
    print_state: str
    is_paused: bool
    is_homed: bool
    unit: int
    gate: int
    tool: int
    active_filament: ActiveFilamentStatus
    num_toolchanges: int
    last_tool: int
    next_tool: int
    toolchange_purge_volume: int
    last_toolchange: str
    operation: str
    filament: str
    filament_position: int
    filament_pos: int
    filament_direction: int
    ttg_map: List[int]
    endless_spool_groups: List[int]
    gate_status: List[int]
    gate_filament_name: List[str]
    gate_material: List[str]
    gate_color: List[str]
    gate_temperature: List[int]
    gate_spool_id: List[int]
    gate_speed_override: List[int]
    slicer_tool_map: MmuSlicerToolMapStatus
    action: str
    has_bypass: bool
    sync_drive: bool
    sync_feedback_enabled: bool
    clog_detection_enabled: bool
    endless_spool_enabled: bool
    reason_for_pause: str
    extruder_filament_remaining: int
    spoolman_support: str
    sensors: Dict[str, bool]
    espooler_active: str
    servo: str
    grip: str

@dataclass
class MmuAceStatus:
    mmu: MmuStatus
    mmu_machine: MmuMachineStatus

GATE_UNKNOWN = -1
GATE_EMPTY = 0
GATE_AVAILABLE = 1 # Available to load from either buffer or spool
GATE_AVAILABLE_FROM_BUFFER = 2

class MmuAceGate:
    status: int = GATE_EMPTY
    filament_name: str = "Unknown"
    material: str = "Unknown"
    color: List[int] | None = None # rgba [0, 0, 0, 0]
    temperature: int = -1
    spool_id: int = -1
    speed_override: int = -1
    rfid: int = -1
    source: int = -1

class MmuAceUnit:
    name: str
    gates: List[MmuAceGate]

    def __init__(self, _name: str):
        self.name = _name
        self.gates = [
            MmuAceGate(),
            MmuAceGate(),
            MmuAceGate(),
            MmuAceGate()
        ]

    def get_gates(self):
        return  self.gates

class MmuAceTool:
    material: str = "Unknown"
    temp: int = -1
    name: str = "Unknown"
    in_use: bool = False

class MmuAcePrintState(Enum):
    UNKNOWN = 'unknown'
    STARTED = 'started'
    PRINTING = 'printing'
    PAUSE_LOCKED = 'pause_locked'
    PAUSED = 'paused'

UNIT_UNKNOWN = -1

TOOL_GATE_UNKNOWN = -1
TOOL_GATE_BYPASS = -2

FILAMENT_POS_UNKNOWN = -1
FILAMENT_POS_UNLOADED = 0 # Parked in gate
FILAMENT_POS_HOMED_GATE = 1 # Homed at either gate or gear sensor (currently assumed mutually exclusive sensors)
FILAMENT_POS_START_BOWDEN = 2 # Point of fast load portion
FILAMENT_POS_IN_BOWDEN = 3 # Some unknown position in the bowden
FILAMENT_POS_END_BOWDEN = 4 # End of fast load portion
FILAMENT_POS_HOMED_ENTRY = 5 # Homed at entry sensor
FILAMENT_POS_HOMED_EXTRUDER = 6 # Collision homing case at extruder gear entry
FILAMENT_POS_EXTRUDER_ENTRY = 7 # Past extruder gear entry
FILAMENT_POS_HOMED_TS = 8 # Homed at toolhead sensor
FILAMENT_POS_IN_EXTRUDER = 9 # In extruder past toolhead sensor
FILAMENT_POS_LOADED = 10 # Homed to nozzle

DIRECTION_LOAD = 1
DIRECTION_UNKNOWN = 0
DIRECTION_UNLOAD = -1

ACTION_IDLE = 'Idle'
ACTION_LOADING = 'Loading'
ACTION_LOADING_EXTRUDER = 'Loading Ext'
ACTION_UNLOADING = 'Unloading'
ACTION_UNLOADING_EXTRUDER = 'Unloading Ext'
ACTION_FORMING_TIP = 'Forming Tip'
ACTION_CUTTING_TIP = 'Cutting Tip'
ACTION_HEATING = 'Heating'
ACTION_CHECKING = 'Checking'
ACTION_HOMING = 'Homing'
ACTION_SELECTING = 'Selecting'
ACTION_CUTTING_FILAMENT = 'Cutting Filament'
ACTION_PURGING = 'Purging'

class MmuAceFilament:
    name: str = "Filament"
    position: int = 0
    pos: int = FILAMENT_POS_UNKNOWN
    direction: int = DIRECTION_UNKNOWN

class MmuAce:
    enabled: bool = True
    units: List[MmuAceUnit] = []
    tools: List[MmuAceTool] = []
    unit: int = UNIT_UNKNOWN
    print_state: MmuAcePrintState = MmuAcePrintState.UNKNOWN
    is_paused: bool = False
    is_homed: bool = False
    gate: int = TOOL_GATE_UNKNOWN
    tool: int = TOOL_GATE_UNKNOWN
    ttg_map: List[int] = []
    num_toolchanges: int = 0
    last_tool: int = TOOL_GATE_UNKNOWN
    next_tool: int = TOOL_GATE_UNKNOWN
    operation: str = ""
    filament: MmuAceFilament = MmuAceFilament()
    endless_spool_groups: List[int] = []
    action: str = ACTION_IDLE

    def __init__(self):
        self.units = [
            MmuAceUnit("ACE 1")
        ]

        self.tools = []

class PrinterController:
    # async def send_event(self, name: str, args: dict | None = None) -> dict:
    #     pass

    async def query_objects(self,
                            objects: Mapping[str, Optional[List[str]]],
                            default: Union[Sentinel, _T] = Sentinel.MISSING
                            ) -> Union[_T, Dict[str, Any]]:
        pass

    async def subscribe_objects(
            self,
            objects: Mapping[str, Optional[List[str]]],
            callback: Optional[SubCallback] = None,
            default: Union[Sentinel, _T] = Sentinel.MISSING
    ) -> Union[_T, Dict[str, Any]]:
        pass


class KlippyPrinterController(PrinterController):
    def __init__(self, _server):
        self.server = _server
        self.klippy_apis: KlippyAPI = self.server.lookup_component("klippy_apis")

    async def query_objects(self,
                            objects: Mapping[str, Optional[List[str]]],
                            default: Union[Sentinel, _T] = Sentinel.MISSING
                            ) -> Union[_T, Dict[str, Any]]:
        return await self.klippy_apis.query_objects(objects, default)

    async def subscribe_objects(
            self,
            objects: Mapping[str, Optional[List[str]]],
            callback: Optional[SubCallback] = None,
            default: Union[Sentinel, _T] = Sentinel.MISSING
    ) -> Union[_T, Dict[str, Any]]:
        return await self.klippy_apis.subscribe_objects(objects, callback, default)

# printer controller for test with remote printer
class RemotePrinterController(PrinterController):
    def __init__(self, server, _host):
        self.host = _host
        self.server = server
        self.http_client: HttpClient = self.server.lookup_component("http_client")

    async def _send_event(self, name: str, args: dict | None = None):
        name = name.strip("/").replace(".", "/")

        response: HttpResponse
        if args is not None:
            logging.warning(f"Sending POST {name} with args: {json.dumps(args)}")
            response = await self.http_client.post(f"{self.host}/printer/{name}", body=args)
        else:
            logging.warning(f"Sending GET {name} with args: {json.dumps(args)}")
            response = await self.http_client.get(f"{self.host}/printer/{name}")

        logging.warning(f"Response: {response.status_code}")

        if response.has_error():
            raise ValueError(f"error {response.status_code}: {response.text}")

        result = response.json()

        if "result" in result:
            result = result["result"]

        logging.warning(f"Result: {json.dumps(result)}")

        return result

    async def query_objects(self,
                            objects: Mapping[str, Optional[List[str]]],
                            default: Union[Sentinel, _T] = Sentinel.MISSING
                            ) -> Union[_T, Dict[str, Any]]:
        raise NotImplementedError("Remote printer does not support queries")

    async def subscribe_objects(
            self,
            objects: Mapping[str, Optional[List[str]]],
            callback: Optional[SubCallback] = None,
            default: Union[Sentinel, _T] = Sentinel.MISSING
    ) -> Union[_T, Dict[str, Any]]:
        raise NotImplementedError("Remote printer does not support subscriptions")

def rgb_to_rgba(rgb: List[int]) -> List[int]:
    return [rgb[0], rgb[1], rgb[2], 255]

def rgba_to_hex(rgba: List[int]) -> str:
    return '{:02X}{:02X}{:02X}{:02X}'.format(*rgba)

def hex_to_rgb(hex: str) -> List[int]:
    return [int(hex[i:i+2], 16) for i in (0, 2, 4)]

def hex_to_rgba(hex: str) -> List[int]:
    return [int(hex[i:i+2], 16) for i in (0, 2, 4, 6)]

class MmuAceController:
    ace: MmuAce
    server: Any

    printer: PrinterController

    def __init__(self, server: Server, host: str | None):
        self.server = server
        self.eventloop = self.server.get_event_loop()

        if host is None:
            self.printer = KlippyPrinterController(self.server)
        else:
            self.printer = RemotePrinterController(self.server, host)

    def _handle_status_update(self):
        self.server.send_event("mmu_ace:status_update", asdict(self.get_status()))

    def set_ace(self, ace: MmuAce):
        self.ace = ace
        self._handle_status_update()

        self.eventloop.create_task(self._plan_load_ace())

    async def _plan_load_ace(self, retry=10, delay=2):
        for _ in range(retry):
            success = False
            try:
                # await self._load_mmu_ace_config()
                klippy_apis: KlippyAPI = self.server.lookup_component("klippy_apis")
                result = await klippy_apis.query_objects({ "filament_hub": None })
                success = True
            except Exception as e:
                logging.error(f"Error contacting moonraker: {e}")
                success = False
            if success:
                logging.info("Contacted moonraker")
                break
            logging.warning(f"Moonraker not available. {f'Retrying in {delay} seconds...' if retry > 1 else ''}")
            await asyncio.sleep(2)
        try:
            await self._load_ace()
        except Exception as e:
            logging.error(f"Error loading mmu ace: {e}")

    async def _load_ace(self):
        await self._load_mmu_ace_config()
        await self._subscribe_mmu_ace_status_update()

        self._handle_status_update()

    async def _load_mmu_ace_config(self):
        result = await self.printer.query_objects({ "filament_hub": None })
        logging.warning(f"mmu ace config: {json.dumps(result)}")

    async def _subscribe_mmu_ace_status_update(self):
        result = await self.printer.subscribe_objects({ "filament_hub": None }, self._handle_mmu_ace_status_update)

        logging.warning(f"mmu ace status subscribe: {json.dumps(result)}")

        filament_hub = result["filament_hub"]

        # set units
        self.ace.units = []
        self.ace.tools = []
        self.ace.ttg_map = []

        for hub in filament_hub["filament_hubs"]:
            hub_id = hub["id"] + 1
            unit = MmuAceUnit(f"ACE {hub_id}")
            unit.gates = []
            for i, slot in enumerate(hub["slots"]):
                index: int = slot["index"]
                status: str = slot["status"]
                sku: str = slot["sku"]
                type: str = slot["type"]
                color: list[int] = slot["color"]
                rfid: int = slot["rfid"]
                source: int = slot["source"]

                gate = MmuAceGate()
                gate.material = type
                gate.filament_name = type
                gate.color = rgb_to_rgba(color)
                gate.rfid = rfid
                gate.source = source
                gate.status = GATE_AVAILABLE if status == "ready" else GATE_EMPTY

                unit.gates.append(gate)

                tool = MmuAceTool()
                tool.name = f"T{i + 1}"
                self.ace.tools.append(tool)
                self.ace.ttg_map.append(i)

            self.ace.units.append(unit)

    async def _handle_mmu_ace_status_update(self, status: Dict[str, Any], _: float):
        logging.warning(f"mmu ace status update: {json.dumps(status)}")

        # if "filament_hub" in status:
        #     filament_hub = status["filament_hub"]
        #     for hub in filament_hub["filament_hubs"]:
        #         hub_id = hub["id"] + 1
        # 
        # filament_hub = status["filament_hub"]
        # 
        # # set units
        # self.ace.units = []
        # self.ace.tools = []
        # self.ace.ttg_map = []
        # 
        # for hub in filament_hub["filament_hubs"]:
        #     hub_id = hub["id"] + 1
        #     unit = MmuAceUnit(f"ACE {hub_id}")
        #     unit.gates = []
        #     for i, slot in enumerate(hub["slots"]):
        #         index: int = slot["index"]
        #         status: str = slot["status"] 
        #         sku: str = slot["sku"] 
        #         type: str = slot["type"] 
        #         color: list[int] = slot["color"] 
        #         rfid: int = slot["rfid"]
        #         source: int = slot["source"]
        #         
        #         gate = MmuAceGate()
        #         gate.material = type
        #         gate.filament_name = type
        #         gate.color = rgb_to_rgba(color)
        #         gate.rfid = rfid
        #         gate.source = source
        #         gate.status = GATE_AVAILABLE if status == "ready" else GATE_EMPTY
        #         
        #         unit.gates.append(gate)
        # 
        #         tool = MmuAceTool()
        #         tool.name = f"T{i + 1}"
        #         self.ace.tools.append(tool)
        #         self.ace.ttg_map.append(i)
        #         
        #     self.ace.units.append(unit)
        # 
        # self._handle_status_update()

    def get_status(self) -> MmuAceStatus:

        gates = [gate for gates in [unit.gates for unit in self.ace.units] for gate in gates]
        num_gates = len(gates)
        gate_status = [gate.status for gate in gates]
        gate_filament_name = [gate.filament_name for gate in gates]
        gate_material = [gate.material for gate in gates]
        gate_color = [rgba_to_hex(gate.color) if gate.color is not None else None for gate in gates]
        gate_temperature = [gate.temperature for gate in gates]
        gate_spool_id = [gate.spool_id for gate in gates]
        gate_speed_override = [gate.speed_override for gate in gates]

        return MmuAceStatus(
            mmu = MmuStatus(
                enabled = self.ace.enabled,
                encoder = None,
                num_gates = num_gates,
                print_state = self.ace.print_state.value,
                is_paused = self.ace.is_paused,
                is_homed = self.ace.is_homed,
                unit = self.ace.unit,
                gate = self.ace.gate,
                tool = self.ace.tool,
                active_filament = None,
                num_toolchanges = self.ace.num_toolchanges,
                last_tool = self.ace.last_tool,
                next_tool = self.ace.next_tool,
                toolchange_purge_volume = 0,
                last_toolchange = None,
                operation = self.ace.operation,
                filament = self.ace.filament.name,
                filament_position = self.ace.filament.position,
                filament_pos = self.ace.filament.pos,
                filament_direction = self.ace.filament.direction,
                ttg_map = self.ace.ttg_map,
                endless_spool_groups = self.ace.endless_spool_groups,
                gate_status = gate_status,
                gate_filament_name = gate_filament_name,
                gate_material = gate_material,
                gate_color = gate_color,
                gate_temperature = gate_temperature,
                gate_spool_id = gate_spool_id,
                gate_speed_override = gate_speed_override,
                slicer_tool_map = self.get_tools_status(),
                action = self.ace.action,
                has_bypass = False,
                sync_drive = False,
                sync_feedback_enabled = False,
                clog_detection_enabled = False,
                endless_spool_enabled = False,
                reason_for_pause = None,
                extruder_filament_remaining = -1,
                spoolman_support = False,
                sensors = {},
                espooler_active = None,
                servo = None,
                grip = None,
            ),
            mmu_machine = self.get_machine_status()
        )

    def get_machine_status(self):
        return MmuMachineStatus(
            num_units = len(self.ace.units),
            unit_0 = self.get_unit_status(self.ace.units[0], 0) if len(self.ace.units) >= 1 else None,
            unit_1 = self.get_unit_status(self.ace.units[1], 1) if len(self.ace.units) >= 2 else None,
        )

    def get_unit_status(self, unit: MmuAceUnit, index: int):
        return  MmuUnitStatus(
            name = unit.name,
            vendor = "Anycubic",
            version = "1.0",
            num_gates = len(unit.gates),
            first_gate = 0,
            selector_type = "VirtualSelector",
            variable_rotation_distances = False,
            variable_bowden_lengths = False,
            require_bowden_move = False,
            filament_always_gripped = False,
            has_bypass = False,
            multi_gear = False,
        )

    def get_tools_status(self):
        return MmuSlicerToolMapStatus([self.get_tool_status(tool) for tool in self.ace.tools])

    def get_tool_status(self, tool: MmuAceTool):
        return  MmuToolStatus(
            material = tool.material,
            temp = tool.temp,
            name = tool.name,
            in_use = tool.in_use,
        )

    def update_ttg_map(self, ttg_map: List[int]):
        self.ace.ttg_map = ttg_map
        self._handle_status_update()

    def update_gate(self,
                    gate_index: int,
                    status: int = GATE_EMPTY,
                    filament_name: str = "Unknown",
                    material: str = "Unknown",
                    color: str = "Unknown",
                    temperature: int = -1,
                    spool_id: int = -1,
                    speed_override: int = -1
                    ):
        gate: MmuAceGate | None = None
        unit: MmuAceUnit | None = None
        current_gate_index = gate_index
        for u in self.ace.units:
            num_gates = len(u.gates)
            if num_gates - 1 >= gate_index:
                unit = u
                gate = u.gates[current_gate_index]
                break
            current_gate_index = current_gate_index - num_gates

        logging.warning(f"update gate {gate_index} actual values {json.dumps(gate.__dict__)}")

        if gate is not None:
            gate.status = status
            gate.filament_name = filament_name
            gate.material = material
            gate.color = color
            gate.temperature = temperature
            gate.spool_id = spool_id
            gate.speed_override = speed_override
            self._handle_status_update()
            logging.warning(f"updated gate {gate_index} with values {json.dumps(gate.__dict__)}")
        else:
            logging.warning(f"update gate {gate_index} not found")

class MmuAcePatcher:

    ace: MmuAce
    ace_controller: MmuAceController
    kobra: Kobra

    def __init__(self, config: ConfigHelper):
        self.server = config.get_server()
        self.name = config.get_name()
        self.kobra = self.server.load_component(self.server.config, 'kobra')

        host = config.get("host", None)
        self.ace_controller = MmuAceController(self.server, host)

        self.reinit()

        # mmu test enpoints
        self.server.register_endpoint("/server/mmu-ace", ['GET'], self._handle_mmu_request)

        # mmu status update notification
        self.server.register_notification("mmu_ace:status_update")

        # gcode handlers
        self.register_gcode_handler("MMU_GATE_MAP", self._on_gcode_mmu_gate_map)
        self.register_gcode_handler("MMU_TTG_MAP", self._on_gcode_mmu_ttg_map)
        self.register_gcode_handler("MMU_TTG_MAP", self._on_gcode_mmu_ttg_map)
        self.register_gcode_handler("MMU_SLICER_TOOL_MAP", self._on_gcode_mmu_ttg_map)

        self.kobra.register_status_patcher(self.patch_status)

        self.kobra.register_print_data_patcher(self.patch_print_data)

    def register_gcode_handler(self, cmd, callback: FlexCallback):
        self.kobra.register_gcode_handler(cmd, callback)

    def _get_gcode_arg_str(self, name: str, args: dict[str, str | None]):
        if name in args:
            return args[name]

        raise ValueError(f"param {name} not found on command")

    def _get_gcode_arg_str_def(self, name: str, args: dict[str, str | None], default):
        if name in args:
            return args[name]

        return default

    async def _on_gcode_mmu_ttg_map(self, args: dict[str, str | None], delegate):
        logging.warning(f"handle mmu_ttg_map: {json.dumps(args)}")
        ttg_map_str = self._get_gcode_arg_str("MAP", args)
        ttg_map = [int(value) for value in ttg_map_str.split(",")]
        self.ace_controller.update_ttg_map(ttg_map)

    async def _on_gcode_mmu_gate_map(self, args: dict[str, str | None], delegate):
        logging.warning(f"handle mmu_gate_map: {json.dumps(args)}")
        gate_map_str = self._get_gcode_arg_str("MAP", args)
        logging.warning(f"handle mmu_gate_map gate_map_str: {gate_map_str}")
        gate_map = ast.literal_eval(gate_map_str)
        logging.warning(f"handle mmu_gate_map gate_map: {json.dumps(gate_map)}")

        for key, value in gate_map.items():
            gate_index = int(key)

            logging.warning(f"try update gate {key}: {json.dumps(value)}")

            self.ace_controller.update_gate(
                gate_index = gate_index,
                status = value["status"],
                filament_name = value["name"],
                material = value["material"],
                color = value["color"],
                temperature = value["temp"],
                spool_id = value["spool_id"],
                speed_override = value["speed_override"],
            )

    def reinit(self):

        self.ace = MmuAce()
        self.ace_controller.set_ace(self.ace)

        # "configfile": {
        #     "config": {
        #         "mmu": {
        #             "gate_homing_endstop": "",
        #             "extruder_homing_endstop": "",
        #             "extruder_force_homing": False,
        #             "t_macro_color": "slicer",
        #         }
        #     }
        # },
        # "save_variables": {
        #     "vaariables": {
        #         "mmu_calibration_bowden_lengths": [],
        #         "mmu_state_filament_remaining": 0,
        #         "mmu_state_filament_remaining_color": ""
        #     }
        # }

        # Sub components
        # self.selector.reinit()

    def get_status(self) -> dict:
        return asdict(self.ace_controller.get_status())

    def patch_status(self, status: dict):

        mmu_status = self.get_status()

        for key, value in mmu_status.items():
            status[key] = value
        # status = self._combine(mmu_status, status)

        return status

    def patch_print_data(self, print_data: dict):

        # add gate mapping for multi color printing
        if self.ace.enabled and "ams_settings" not in print_data:

            mapping = []

            for tool_index, tool in enumerate(self.ace.tools):
                gate_index = self.ace.ttg_map[tool_index]
                # todo : implement multi units and check if gate_index is valid
                gate = self.ace.units[0].gates[gate_index]

                mapping.append({
                    "paint_index": tool_index,
                    "ams_index": gate_index,
                    "paint_color": gate.color, # todo
                    "ams_color": gate.color,
                    "material_type": gate.material
                })

            print_data["ams_settings"] = {
                "use_ams": True,
                "ams_box_mapping": mapping
            }

            logging.warning(f"mmu_ace: patch_print_data: {json.dumps(print_data)}")

        return print_data

    def _combine(self, sourceA, sourceB):
        result = {}
        self._merge(sourceA, result)
        self._merge(sourceB, result)
        return result

    def _merge(self, source, destination):
        for key, value in source.items():
            if isinstance(value, dict):
                # get node or create one
                node = destination.setdefault(key, {})
                self._merge(value, node)
            else:
                destination[key] = value

        return destination

    async def _handle_mmu_request(self, web_request):
        return {
            "status": self.get_status()
        }


def load_component(config):
    return MmuAcePatcher(config)

# {
#     "jsonrpc": "2.0",
#     "method": "printer.gcode.script",
#     "params": {
#         "script": "MMU_GATE_MAP MAP=\"{0: {'status':0,'spool_id':0,'material':'PLA','color':'FF0000FF','name':'A','temp':0,'speed_override':0},1: {'status':0,'spool_id':1,'material':'PETG','color':'008000FF','name':'B','temp':0,'speed_override':0},2: {'status':0,'spool_id':2,'material':'ABS','color':'0000FFFF','name':'C','temp':0,'speed_override':0},3: {'status':1,'spool_id':-1,'material':'TPUu','color':'6A1B9ABD','name':'D testname','temp':'200','speed_override':50}}\" QUIET=1"
#     },
#     "id": 29
# }
