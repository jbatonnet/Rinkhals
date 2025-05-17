# Example Component
#
# Copyright (C) 2021  Eric Callahan <arksine.code@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import argparse
import filecmp
import json
import ast
import logging
import os
import re
import asyncio
import shutil
import sys
import time
import traceback
import tempfile

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
    Coroutine,
    Type
)

if TYPE_CHECKING:
    FlexCallback = Callable[..., Optional[Coroutine]]
    SubCallback = Callable[[Dict[str, Dict[str, Any]], float], Optional[Coroutine]]
    _T = TypeVar("_T")


    from ..utils import Sentinel
    from ..confighelper import ConfigHelper
    from ..server import Server
    from .kobra import Kobra
    from .http_client import HttpClient, HttpResponse
    from .klippy_apis import KlippyAPI
    from .klippy_connection import KlippyConnection
    from ..common import WebRequest, APITransport, RequestType
else:
    _T = Any
    FlexCallback = Any
    SubCallback = Any

    class Sentinel(Enum):
        MISSING = object()
    
    ConfigHelper = Any
    Server = Any
    Kobra = Any
    HttpClient = Any
    HttpResponse = Any
    KlippyAPI = Any
    KlippyConnection = Any
    WebRequest = Any
    APITransport = Any
    RequestType = Any

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
    index: int
    status: int = GATE_EMPTY
    filament_name: str = "Unknown"
    material: str = "Unknown"
    color: List[int] | None = None # rgba [0, 0, 0, 0]
    temperature: int = -1
    spool_id: int = -1
    speed_override: int = -1
    rfid: int = 1 # 1 = no rfid 2 = rfid, if rfid = 2 not update possible
    source: int = -1

class MmuAceUnit:
    id: int
    name: str
    status: str
    temp: int
    dryer: dict
    gates: List[MmuAceGate]

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
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
            MmuAceUnit(0, "ACE 1")
        ]

        self.tools = []

class PrinterController:
    async def send_request(self, method: str, params: Dict[str, Any], default: Any = Sentinel.MISSING) -> Any:
        pass

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
        self.klippy: KlippyConnection = self.server.lookup_component("klippy_connection")

    async def _send_klippy_request(
            self,
            method: str,
            params: Dict[str, Any],
            default: Any = Sentinel.MISSING,
            transport: Optional[APITransport] = None
    ) -> Any:
        logging.warning(f"Sending {method} with params: {json.dumps(params)}")
        try:
            req = WebRequest(method, params, transport=transport or self)
            result = await self.klippy.request(req)
            logging.warning(f"Result of {method}: {json.dumps(result)}")
        except self.server.error:
            logging.warning(f"Error sending {method} with params: {json.dumps(params)}")
            if default is Sentinel.MISSING:
                raise
            result = default
        return result

    async def send_request(self, method: str,
                           params: Dict[str, Any],
                           default: Any = Sentinel.MISSING) -> Any:
        logging.warning(f"Sending {method} with params: {json.dumps(params)}")
        return await self._send_klippy_request(method, params, default)
        # return await self.klippy_apis._send_klippy_request(method, params, default)
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

        self._set_ace_status(filament_hub)

    async def _handle_mmu_ace_status_update(self, status: Dict[str, Any], _: float):
        if "filament_hub" in status:
            filament_hub = status["filament_hub"]
            logging.warning(f"mmu ace status update: {json.dumps(filament_hub)}")

            self._set_ace_status(filament_hub)

    def _set_ace_status(self, filament_hub):
        # set units
        ace = self.ace
        ace.units = []
        ace.tools = []
        ace.ttg_map = []

        for hub in filament_hub["filament_hubs"]:
            hub_id = hub["id"]
            unit = MmuAceUnit(hub_id, f"ACE {hub_id + 1}")

            unit.status = hub["status"] if "status" in hub else None
            unit.temp = hub["temp"] if "temp" in hub else None

            if "dryer_status" in hub:
                unit.dryer = hub["dryer_status"]

            unit.gates = []
            for i, slot in enumerate(hub["slots"]):
                index: int = slot["index"] if "index" in slot else None
                # preload ready shifting runout empty
                status: str = slot["status"] if "status" in slot else None
                sku: str = slot["sku"] if "sku" in slot else None
                type: str = slot["type"] if "type" in slot else None
                color: list[int] = slot["color"] if "color" in slot else None
                rfid: int = slot["rfid"] if "rfid" in slot else None
                source: int = slot["source"] if "source" in slot else None

                gate = MmuAceGate()
                gate.index = index
                gate.material = type
                gate.filament_name = type
                gate.color = rgb_to_rgba(color)
                gate.rfid = rfid
                gate.source = source
                gate.status = GATE_AVAILABLE if status == "ready" else GATE_EMPTY if status == "empty" or status == "runout" else GATE_UNKNOWN

                unit.gates.append(gate)

                tool = MmuAceTool()
                tool.name = f"T{i + 1}"
                self.ace.tools.append(tool)
                self.ace.ttg_map.append(i)

            self.ace.units.append(unit)

        self._handle_status_update()

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

    async def update_gate(self,
                          gate_index: int,
                          status: int = GATE_EMPTY,
                          filament_name: str = "Unknown",
                          material: str = "Unknown",
                          color: list[int] = None,
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

        if color is None:
            color = [0, 0, 0, 0]

        if gate is not None:
            if gate.rfid == 2:
                logging.warning(f"update gate {gate_index} not allowed, rfid is set")
                return
            
            logging.warning(f"updating gate {gate_index} with values {json.dumps(gate.__dict__)}")
            # {"method":"filament_hub/set_filament_info","params":{"color":{"B":65,"G":209,"R":254},"id":0,"index":2,"type":"PLA"},"id":34}
            # call gklib to update spool
            params = {
                "color": {"R": color[0], "G": color[1], "B": color[2]},
                "id": unit.id, # ace id
                "index": gate.index, # slot index
                "type": material
            }
            
            error = "unknown"
            result = None
            try:
                result = await self.printer.send_request("filament_hub/set_filament_info", params)
            except Exception as e:
                logging.error(f"Error contacting klippy: {e}")
                result = "error"
                error = e

            # gate.status = status
            # gate.filament_name = filament_name
            # gate.material = material
            # gate.color = color
            # gate.temperature = temperature
            # gate.spool_id = spool_id
            # gate.speed_override = speed_override
            # self._handle_status_update()

            if result == "ok":
                logging.warning(f"updated gate {gate_index} with values {json.dumps(gate.__dict__)}")
            else:
                logging.warning(f"update gate {gate_index} failed: {result} {error}")
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
        self.register_gcode_handler("MMU_ENDLESS_SPOOL", self._on_gcode_mmu_endless_spool) # todo
        self.register_gcode_handler("MMU_SELECT", self._on_gcode_mmu_unknown) # todo
        self.register_gcode_handler("MMU_SLICER_TOOL_MAP", self._on_gcode_mmu_unknown) # todo

        self.kobra.register_status_patcher(self.patch_status)

        self.kobra.register_print_data_patcher(self.patch_print_data)

        # Add AnycubicSlicerNext to supported slicers
        self.setup_anycubic_slicer()

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

    async def _on_gcode_mmu_unknown(self, args: dict[str, str | None], delegate):
        pass

    # Triggered on ToolToGate edit in ui
    async def _on_gcode_mmu_ttg_map(self, args: dict[str, str | None], delegate):
        logging.warning(f"handle mmu_ttg_map: {json.dumps(args)}")
        ttg_map_str = self._get_gcode_arg_str("MAP", args)
        ttg_map = [int(value) for value in ttg_map_str.split(",")]
        self.ace_controller.update_ttg_map(ttg_map)

    # Triggered on ToolToGate edit in ui
    async def _on_gcode_mmu_endless_spool(self, args: dict[str, str | None], delegate):
        logging.warning(f"handle _on_gcode_mmu_endless_spool: {json.dumps(args)}")
        groups_str = self._get_gcode_arg_str("GROUPS", args)
        logging.warning(f"handle _on_gcode_mmu_endless_spool groups_str: {groups_str}")
        # TODO

    # Triggered on spool edit in ui
    async def _on_gcode_mmu_gate_map(self, args: dict[str, str | None], delegate):
        logging.warning(f"handle mmu_gate_map: {json.dumps(args)}")
        gate_map_str = self._get_gcode_arg_str("MAP", args)
        logging.warning(f"handle mmu_gate_map gate_map_str: {gate_map_str}")
        gate_map = ast.literal_eval(gate_map_str)
        logging.warning(f"handle mmu_gate_map gate_map: {json.dumps(gate_map)}")

        for key, value in gate_map.items():
            gate_index = int(key)

            logging.warning(f"try update gate {key}: {json.dumps(value)}")

            await self.ace_controller.update_gate(
                gate_index = gate_index,
                status = value["status"],
                filament_name = value["name"],
                material = value["material"],
                color = hex_to_rgba(value["color"]),
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

    # Add support for anycubic slicer
    def setup_anycubic_slicer(self):
        logging.warning("setup_anycubic_slicer")
        from .file_manager import file_manager
        file_manager.METADATA_SCRIPT = os.path.abspath(__file__)
        logging.warning(f"setup_anycubic_slicer METADATA_SCRIPT: {file_manager.METADATA_SCRIPT}")


def load_component(config):
    return MmuAcePatcher(config)


##################################################################################
#
# Beyond this point this module acts like an extended file_manager/metadata module
#
AUTHORZIED_SLICERS = ['PrusaSlicer', 'SuperSlicer', 'OrcaSlicer', 'BambuStudio', 'AnycubicSlicerNext']

MMU_ACE_FINGERPRINT = "; processed by MmuAcePatcher"
MMU_REGEX = r"^" + MMU_ACE_FINGERPRINT
SLICER_REGEX = r"^;.*generated by ([a-z]*) .*$|^; (BambuStudio) .*$"

TOOL_DISCOVERY_REGEX = r"((^MMU_CHANGE_TOOL(_STANDALONE)? .*?TOOL=)|(^T))(?P<tool>\d{1,2})"

def gcode_processed_already(file_path):
    """Expects first line of gcode to be the HAPPY_HARE_FINGERPRINT '; processed by HappyHare'"""

    mmu_regex = re.compile(MMU_REGEX, re.IGNORECASE)

    with open(file_path, 'r') as in_file:
        line = in_file.readline()
        return mmu_regex.match(line)
    
def parse_gcode_file(file_path):
    slicer_regex = re.compile(SLICER_REGEX, re.IGNORECASE)
    slicer = None

    tools_used = set()
    total_toolchanges = 0
    
    with open(file_path, 'r') as in_file:
        for line in in_file:
            # Discover slicer
            if not slicer and line.startswith(";"):
                match = slicer_regex.match(line)
                if match:
                    slicer = match.group(1) or match.group(2)
    if slicer in AUTHORZIED_SLICERS:
        if isinstance(TOOL_DISCOVERY_REGEX, dict):
            tools_regex = re.compile(TOOL_DISCOVERY_REGEX[slicer], re.IGNORECASE)
        else:
            tools_regex = re.compile(TOOL_DISCOVERY_REGEX, re.IGNORECASE)

        with open(file_path, 'r') as in_file:
            for line in in_file:
                match = tools_regex.match(line)
                if match:
                    tool = match.group("tool")
                    tools_used.add(int(tool))
                    total_toolchanges += 1
    
    return {
        "slicer": slicer,
        "tools_used": sorted(tools_used),
        "total_toolchanges": total_toolchanges,
    }

def process_file(input_filename, output_filename, tools_used, total_toolchanges):
    with open(input_filename, 'r') as infile, open(output_filename, 'w') as outfile:
        outfile.write(f'{MMU_ACE_FINGERPRINT}\n')
        for line in infile:
            outfile.write(line)
        # Finally append "; referenced_tools =" as new metadata (why won't Prusa pick up my PR?)
        outfile.write("; referenced_tools = %s\n" % ",".join(map(str, tools_used)))
    
def main(config: Dict[str, Any], metadata) -> None:

    logging.warning("main setup_anycubic_slicer")
    
    path = config["gcode_dir"]
    filename = config["filename"]
    
    file_path = os.path.join(path, filename)
    if not os.path.isfile(file_path):
        metadata.logger.info(f"File Not Found: {file_path}")
        sys.exit(-1)

    try:
        metadata.logger.info(f"mmu_server: Pre-processing file: {file_path}")
        fname = os.path.basename(file_path)
        if fname.endswith(".gcode") and not gcode_processed_already(file_path):
            with tempfile.TemporaryDirectory() as tmp_dir_name:
                tmp_file = os.path.join(tmp_dir_name, fname)

                start = time.time()
                parse_result = parse_gcode_file(file_path)
                slicer = parse_result["slicer"]
                tools_used = parse_result["tools_used"]
                total_toolchanges = parse_result["total_toolchanges"]
                metadata.logger.info("Reading placeholders took %.2fs. Detected gcode by slicer: %s" % (time.time() - start, slicer))
                metadata.logger.info("Detected tools: %s" % tools_used)
                
                if tools_used is not None and len(tools_used) > 0:
                    process_file(file_path, tmp_file, tools_used, total_toolchanges)
                    
                    # Move temporary file back in place
                    if os.path.islink(file_path):
                        file_path = os.path.realpath(file_path)
                    if not filecmp.cmp(tmp_file, file_path):
                        shutil.move(tmp_file, file_path)
                    else:
                        metadata.logger.info(f"Files are the same, skipping replacement of: {file_path} by {tmp_file}")
                    
                
    except Exception:
        metadata.logger.info(traceback.format_exc())
        sys.exit(-1)
    
    class AnycubicSlicerNext(metadata.PrusaSlicer):
        def check_identity(self, data: str) -> bool:
            logging.warning("AnycubicSlicerNext checking identity")
            aliases = {
                'AnycubicSlicerNext': r"AnycubicSlicerNext\s(.*)\son",
            }
            for name, expr in aliases.items():
                match = re.search(expr, data)
                if match:
                    self.slicer_name = name
                    self.slicer_version = match.group(1)
                    logging.warning(f"AnycubicSlicerNext found {name} version {self.slicer_version}")
                    return True

            logging.warning("AnycubicSlicerNext no identity found")
            return False

    # log supported slicers
    logging.warning("Adding AnycubicSlicerNext to supported slicers")
    supported_slicers: List[Type[metadata.BaseSlicer]] = metadata.SUPPORTED_SLICERS
    logging.warning(f"Supported slicers before: {supported_slicers}")
    supported_slicers.append(AnycubicSlicerNext)
    logging.warning(f"Supported slicers after: {supported_slicers}")
    metadata.SUPPORTED_SLICERS = supported_slicers
    logging.warning(f"Supported slicers after metadata: {supported_slicers}")

    # process file to add referenced_tools metadata

    return metadata.main(config)

logger = logging.getLogger("mmu_ace_patcher")

if __name__ == "__main__":
    # Make it look like we are running in the file_manager directory
    directory = os.path.dirname(os.path.abspath(__file__))
    target_dir = directory + "/file_manager"
    os.chdir(target_dir)
    sys.path.insert(0, target_dir)

    import metadata
    logger = metadata.logger
    metadata.logger.info("mmu_server: Running MMU enhanced version of metadata")

    # Parse start arguments
    parser = argparse.ArgumentParser(
        description="GCode Metadata Extraction Utility")
    parser.add_argument(
        "-c", "--config", metavar='<config_file>', default=None,
        help="Optional json configuration file for metadata.py"
    )
    parser.add_argument(
        "-f", "--filename", metavar='<filename>', default=None,
        help="name gcode file to parse")
    parser.add_argument(
        "-p", "--path", metavar='<path>', default=None,
        help="optional path to folder containing the file"
    )
    parser.add_argument(
        "-u", "--ufp", metavar="<ufp file>", default=None,
        help="optional path of ufp file to extract"
    )
    parser.add_argument(
        "-o", "--check-objects", dest='check_objects', action='store_true',
        help="process gcode file for exclude opbject functionality")
    args = parser.parse_args()
    config: Dict[str, Any] = {}
    if args.config is None:
        if args.filename is None:
            logger.info(
                "The '--filename' (-f) option must be specified when "
                " --config is not set"
            )
            sys.exit(-1)
        config["filename"] = args.filename
        config["gcode_dir"] = args.path
        config["ufp_path"] = args.ufp
        config["check_objects"] = args.check_objects
    else:
        # Config file takes priority over command line options
        try:
            with open(args.config, "r") as f:
                config = (json.load(f))
        except Exception:
            logger.info(traceback.format_exc())
            sys.exit(-1)
        if config.get("filename") is None:
            logger.info("The 'filename' field must be present in the configuration")
            sys.exit(-1)
    if config.get("gcode_dir") is None:
        config["gcode_dir"] = os.path.abspath(os.path.dirname(__file__))
    
    main(config, metadata)

