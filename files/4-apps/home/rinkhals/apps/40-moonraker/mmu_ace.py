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

from collections import OrderedDict
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
    Type,
    Tuple
)

# Import at runtime for actual use
from ..common import WebRequest, APITransport, RequestType

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

@dataclass
class ActiveFilamentStatus:
    empty: bool  # True if no filament loaded, False if loaded
    vendor: str = ""
    manufacturer: str = ""  # Alias for vendor (Fluidd might read this)
    material: str = ""
    color: str = ""

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
    # Dryer Status
    dryer_status: str = "stop"  # "stop", "drying", "heater_err"
    dryer_temp: int = 0
    dryer_target_temp: int = 0
    dryer_remaining: int = 0  # minutes
    dryer_humidity: int = 0

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
    encoder: Optional[MmuEncoderStatus]
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
    gate_temperature_min: List[int]  # Min safe temperature per gate from RFID
    gate_temperature_max: List[int]  # Max recommended temperature per gate from RFID
    gate_spool_id: List[int]
    gate_speed_override: List[int]
    gate_vendor: List[str]
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
    temperature: int = -1  # Default/display temperature (uses min from RFID or material default)
    temperature_min: int = -1  # Minimum safe temperature from RFID
    temperature_max: int = -1  # Maximum recommended temperature from RFID
    spool_id: int = -1
    speed_override: int = -1
    rfid: int = 1 # 1 = no rfid 2 = rfid, if rfid = 2 not update possible
    source: int = -1
    # Parsed SKU information
    sku: str = ""
    vendor: str = ""
    series: str = ""
    color_name: str = ""

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

# Maximum tools for memory management (prevents unbounded list growth)
MAX_TOOLS = 32  # Reasonable limit for multi-material printing

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
    is_homed: bool = True  # ACE selector is virtual - always "homed" to enable manual load/unload buttons
    gate: int = TOOL_GATE_UNKNOWN
    tool: int = TOOL_GATE_UNKNOWN
    loaded_gate: int = TOOL_GATE_UNKNOWN  # Track which gate is physically loaded in extruder
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
        logging.debug(f"Sending {method} with params: {json.dumps(params)}")
        try:
            req = WebRequest(method, params, transport=transport or self)
            result = await self.klippy.request(req)
            logging.debug(f"Result of {method}: {json.dumps(result)}")
        except self.server.error:
            logging.warning(f"Error sending {method} with params: {json.dumps(params)}")
            if default is Sentinel.MISSING:
                raise
            result = default
        return result

    async def send_request(self, method: str,
                           params: Dict[str, Any],
                           default: Any = Sentinel.MISSING) -> Any:
        logging.debug(f"Sending {method} with params: {json.dumps(params)}")
        return await self._send_klippy_request(method, params, default)
        # return await self.klippy_apis._send_klippy_request(method, params, default)

    async def send_gcode(self, script: str) -> Any:
        """Send G-code script to GoKlipper"""
        logging.info(f"Sending G-code: {script}")
        return await self.send_request("gcode/script", {"script": script})

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
            logging.debug(f"Sending POST {name} with args: {json.dumps(args)}")
            response = await self.http_client.post(f"{self.host}/printer/{name}", body=args)
        else:
            logging.debug(f"Sending GET {name} with args: {json.dumps(args)}")
            response = await self.http_client.get(f"{self.host}/printer/{name}")

        logging.debug(f"Response: {response.status_code}")

        if response.has_error():
            raise ValueError(f"error {response.status_code}: {response.text}")

        result = response.json()

        if "result" in result:
            result = result["result"]

        logging.debug(f"Result: {json.dumps(result)}")

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

def get_material_temperature(material: str) -> int:
    """Get default printing temperature for material type"""
    temps = {
        "PLA": 210,
        "PETG": 240,
        "ABS": 250,
        "ASA": 250,
        "TPU": 230,
        "NYLON": 250,
        "PC": 270,
        "PP": 220,
    }
    return temps.get(material.upper(), 210)

def parse_anycubic_sku(sku: str) -> dict:
    """Parse Anycubic SKU code like AHPLBW-107

    Returns dict with:
    - vendor: "Anycubic" or ""
    - material_type: "PLA", "PETG", etc.
    - series: "Highspeed", "Basic", etc.
    - color_code: "BW", "BK", etc.
    - color_name: "White", "Black", etc.
    - serial: "107", "106", etc.
    """
    if not sku or len(sku) < 8:
        return {"vendor": "", "material_type": "", "series": "", "color_code": "", "color_name": "", "serial": ""}

    # Check if it starts with 'A' (Anycubic)
    vendor = "Anycubic" if sku.startswith("A") else ""

    # Extract parts: A-HPL-BW-107 or AHPLBW-107
    parts = sku.split("-")
    if len(parts) == 2:
        # Format: AHPLBW-107
        code_part = parts[0][1:]  # Remove 'A'
        serial = parts[1]
    else:
        return {"vendor": vendor, "material_type": "", "series": "", "color_code": "", "color_name": "", "serial": ""}

    # Material type mapping
    material_map = {
        "HPL": ("PLA", "Highspeed"),
        "PLA": ("PLA", "Basic"),
        "HPETG": ("PETG", "Highspeed"),
        "PETG": ("PETG", "Basic"),
        "HABS": ("ABS", "Highspeed"),
        "ABS": ("ABS", "Basic"),
        "TPU": ("TPU", "Basic"),
    }

    # Color code mapping
    color_map = {
        "BW": "White",
        "BK": "Black",
        "RD": "Red",
        "BL": "Blue",
        "GR": "Green",
        "YL": "Yellow",
        "OR": "Orange",
        "PK": "Pink",
        "GY": "Gray",
        "PR": "Purple",
        "BR": "Brown",
    }

    # Try to extract material and color
    material_type = ""
    series = ""
    color_code = ""
    color_name = ""

    # Try longest material codes first
    for mat_code, (mat_type, mat_series) in sorted(material_map.items(), key=lambda x: -len(x[0])):
        if code_part.startswith(mat_code):
            material_type = mat_type
            series = mat_series
            remaining = code_part[len(mat_code):]

            # Check if remaining part is a color code
            if remaining in color_map:
                color_code = remaining
                color_name = color_map[remaining]
            break

    return {
        "vendor": vendor,
        "material_type": material_type,
        "series": series,
        "color_code": color_code,
        "color_name": color_name,
        "serial": serial
    }

class MmuAceController:
    ace: MmuAce
    server: Any

    printer: PrinterController

    def __init__(self, server: Server, host: str | None):
        self.server = server
        self.eventloop = self.server.get_event_loop()
        self._last_status_update = 0.0
        self._status_update_task: Optional[asyncio.Task] = None
        self._status_update_delay = 0.2  # 200ms debounce for rapid commands
        self._throttle_delay = 0.3  # 300ms minimum delay between updates (max 3/sec)
        self._pending_update = False  # Flag to track if update is needed

        # LRU Cache for filament temperature info (key: "unit_id-gate_index-sku")
        # Limit to 16 entries (2x max gates) to prevent memory leak
        self._filament_temp_cache: OrderedDict = OrderedDict()
        self._max_cache_size = 16  # 2x max gates (8 gates * 2)

        # Cache for gate lookups (key: gate_index, value: (unit, gate))
        # Also LRU with same size limit to prevent unbounded growth
        self._gate_lookup_cache: OrderedDict = OrderedDict()
        self._max_gate_cache_size = 16  # Match temp cache size

        if host is None:
            self.printer = KlippyPrinterController(self.server)
        else:
            self.printer = RemotePrinterController(self.server, host)

        # Start periodic cache cleanup task (runs every 60 seconds)
        # Removes expired temperature cache entries to prevent slow memory leak
        asyncio.create_task(self._periodic_cache_cleanup())

    def _handle_status_update(self, force: bool = False, throttle: bool = False):
        """Send status update notification with debouncing or throttling.

        Args:
            force: If True, send full update immediately (bypass all delays).
            throttle: If True, throttle updates (max 1 per 300ms).
                     Multiple rapid calls result in only ONE update with latest state.
            If False, debounce updates (only last update sent after 200ms).
        """
        if force:
            # Cancel any pending update
            if self._status_update_task is not None and not self._status_update_task.done():
                self._status_update_task.cancel()
            self._pending_update = False

            # Send immediately
            self._send_status_update()
        elif throttle:
            # Mark that an update is needed
            self._pending_update = True

            # If no task is running, start throttle timer
            if self._status_update_task is None or self._status_update_task.done():
                self._status_update_task = self.eventloop.create_task(
                    self._throttled_status_update()
                )
            # If task is already running, it will pick up the pending flag
        else:
            # Debounce: cancel previous task and schedule new one
            if self._status_update_task is not None and not self._status_update_task.done():
                self._status_update_task.cancel()

            self._status_update_task = self.eventloop.create_task(
                self._debounced_status_update()
            )

    async def _throttled_status_update(self):
        """Throttled status update - sends at most every 300ms with cleanup"""
        max_iterations = 100  # Prevent infinite loops
        iterations = 0

        try:
            while self._pending_update and iterations < max_iterations:
                # Clear the pending flag
                self._pending_update = False

                # Send the current state
                self._send_status_update()

                # Wait minimum delay
                await asyncio.sleep(self._throttle_delay)
                iterations += 1

            if iterations >= max_iterations:
                logging.warning(f"Status update throttle reached max iterations ({max_iterations})")
        except asyncio.CancelledError:
            pass  # Task was cancelled, that's fine
        finally:
            # Cleanup: Set task reference to None to allow garbage collection
            self._status_update_task = None

    async def _debounced_status_update(self):
        """Debounced status update - waits before sending with cleanup"""
        try:
            await asyncio.sleep(self._status_update_delay)
            self._send_status_update()
        except asyncio.CancelledError:
            pass  # Task was cancelled, that's fine
        finally:
            # Cleanup: Set task reference to None to allow garbage collection
            self._status_update_task = None

    def _send_status_update(self):
        """Send full status update"""
        try:
            status = self.get_status()
            self.server.send_event("mmu_ace:status_update", asdict(status))
            self._last_status_update = time.time()
        except Exception as e:
            logging.error(f"Error sending status update: {e}")

    def _get_gate_by_index(self, gate_index: int) -> Optional[Tuple[MmuAceUnit, MmuAceGate]]:
        """Get gate by global index with caching for performance.

        Args:
            gate_index: Global gate index (0-7 for 2 units with 4 gates each)

        Returns:
            Tuple of (unit, gate) or None if not found
        """
        # Check cache first
        if gate_index in self._gate_lookup_cache:
            # Move to end (most recently used)
            self._gate_lookup_cache.move_to_end(gate_index)
            return self._gate_lookup_cache[gate_index]

        # Linear search through units
        current_gate_index = gate_index
        for unit in self.ace.units:
            if current_gate_index < len(unit.gates):
                result = (unit, unit.gates[current_gate_index])

                # Cache the result with LRU eviction
                if len(self._gate_lookup_cache) >= self._max_gate_cache_size:
                    # Remove oldest entry (FIFO/LRU)
                    self._gate_lookup_cache.popitem(last=False)

                self._gate_lookup_cache[gate_index] = result
                return result
            current_gate_index -= len(unit.gates)

        return None

    def _invalidate_gate_cache(self):
        """Invalidate gate lookup cache when units change."""
        self._gate_lookup_cache.clear()

    def _cleanup_expired_cache_entries(self):
        """Remove expired entries from temperature cache.

        Reduces cache timeout from 60s to 30s for RAM-constrained systems.
        Prevents accumulation of stale entries over time.
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._filament_temp_cache.items()
            if current_time - timestamp > 30  # 30s for RAM-constrained systems (was 60s)
        ]
        for key in expired_keys:
            del self._filament_temp_cache[key]

        if expired_keys:
            logging.debug(f"Cache cleanup: Removed {len(expired_keys)} expired temperature entries")

    async def _periodic_cache_cleanup(self):
        """Periodically clean up expired cache entries.

        Runs every 60 seconds to remove stale entries from temperature cache.
        Prevents slow memory leak from expired but retained cache entries.
        """
        while True:
            await asyncio.sleep(60)  # Run every 60 seconds
            try:
                self._cleanup_expired_cache_entries()
            except Exception as e:
                logging.error(f"Cache cleanup failed: {e}")

    def _send_fast_update(self):
        """Send full status update immediately (no throttling for fast path)"""
        try:
            # Send complete status for Fluidd compatibility, but immediately
            status = self.get_status()
            self.server.send_event("mmu_ace:status_update", asdict(status))
            self._last_fast_update = time.time()
            logging.info(f"Fast update sent: gate={self.ace.gate}, tool={self.ace.tool}")
        except Exception as e:
            logging.error(f"Error sending fast update: {e}")

    async def _fast_update_cooldown_handler(self):
        """Wait for cooldown period, then send full status update"""
        try:
            await asyncio.sleep(self._fast_update_cooldown)
            # After cooldown, send full update
            self._send_status_update()
            logging.info("Fast path cooldown complete, full status sent")
        except asyncio.CancelledError:
            # Another fast update came in, this is fine
            pass

    def set_ace(self, ace: MmuAce):
        self.ace = ace
        self._handle_status_update(force=True)

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

        self._handle_status_update(force=True)

    async def _load_mmu_ace_config(self):
        result = await self.printer.query_objects({ "filament_hub": None })
        logging.debug(f"mmu ace config: {json.dumps(result)}")

    async def _subscribe_mmu_ace_status_update(self):
        result = await self.printer.subscribe_objects({ "filament_hub": None }, self._handle_mmu_ace_status_update)

        logging.debug(f"mmu ace status subscribe: {json.dumps(result)}")

        filament_hub = result["filament_hub"]

        # Fetch temperature info for all gates with material (initial load)
        # Collect all temperature fetch tasks for parallel execution
        temp_tasks = []
        task_metadata = []  # Store (hub, slot) references to apply results later

        for hub in filament_hub["filament_hubs"]:
            hub_id = hub["id"]
            for slot in hub["slots"]:
                gate_index = slot["index"]
                sku = slot.get("sku", "")
                source = slot.get("source", 3)

                # Only query for gates with material (source=1 RFID or source=2 user-edited)
                # Skip empty gates (source=3)
                if source in [1, 2]:
                    task = self._get_filament_temperature_info(hub_id, gate_index, sku)
                    temp_tasks.append(task)
                    task_metadata.append((hub, slot))

        # Execute all temperature fetches in parallel (8x faster startup)
        if temp_tasks:
            logging.info(f"Fetching temperature data for {len(temp_tasks)} gates in parallel...")
            results = await asyncio.gather(*temp_tasks, return_exceptions=True)

            # Apply results back to slots
            for i, temp_data in enumerate(results):
                hub, slot = task_metadata[i]
                if isinstance(temp_data, Exception):
                    logging.warning(f"Failed to fetch temperature for gate {slot['index']}: {temp_data}")
                elif temp_data:
                    slot["temperature"] = temp_data

        self._set_ace_status(filament_hub)

    async def _handle_mmu_ace_status_update(self, status: Dict[str, Any], _: float):
        if "filament_hub" in status:
            filament_hub = status["filament_hub"]
            logging.debug(f"mmu ace status update: {json.dumps(filament_hub)}")

            # Fetch temperature info for all gates with material
            # Collect all temperature fetch tasks for parallel execution
            temp_tasks = []
            task_metadata = []  # Store (hub, slot) references to apply results later

            for hub in filament_hub["filament_hubs"]:
                hub_id = hub["id"]
                for slot in hub["slots"]:
                    gate_index = slot["index"]
                    sku = slot.get("sku", "")
                    source = slot.get("source", 3)

                    # Only query for gates with material (source=1 RFID or source=2 user-edited)
                    # Skip empty gates (source=3)
                    if source in [1, 2]:
                        task = self._get_filament_temperature_info(hub_id, gate_index, sku)
                        temp_tasks.append(task)
                        task_metadata.append((hub, slot))

            # Execute all temperature fetches in parallel
            if temp_tasks:
                results = await asyncio.gather(*temp_tasks, return_exceptions=True)

                # Apply results back to slots
                for i, temp_data in enumerate(results):
                    hub, slot = task_metadata[i]
                    if isinstance(temp_data, Exception):
                        logging.warning(f"Failed to fetch temperature for gate {slot['index']}: {temp_data}")
                    elif temp_data:
                        slot["temperature"] = temp_data

            self._set_ace_status(filament_hub)

    async def _get_filament_temperature_info(self, unit_id: int, gate_index: int, sku: str) -> Optional[Dict[str, Any]]:
        """Get filament temperature info from ACE hardware with time-based caching.

        Cache expires after 60 seconds to allow detection of RFID tag changes.

        Args:
            unit_id: ACE unit ID (0 or 1)
            gate_index: Local gate index (0-3)
            sku: SKU code for cache key

        Returns:
            Dict with 'min' and 'max' temperature, or None if not available
        """
        # Create cache key from unit, gate, and SKU
        cache_key = f"{unit_id}-{gate_index}-{sku}"

        # Check if cached data is still valid (< 60 seconds old)
        if cache_key in self._filament_temp_cache:
            cached_data, timestamp = self._filament_temp_cache[cache_key]
            age = time.time() - timestamp
            if age < 60:  # Cache valid for 60 seconds
                logging.debug(f"Using cached temperature for unit {unit_id} gate {gate_index} (age: {age:.1f}s)")
                return cached_data
            else:
                logging.info(f"Cache expired for unit {unit_id} gate {gate_index} (age: {age:.1f}s), refreshing...")

        # Query ACE hardware for filament info
        try:
            result = await self.printer.send_request(
                "filament_hub/filament_info",
                {"id": unit_id, "index": gate_index}
            )

            # Extract temperature data
            if result and "extruder_temp" in result:
                temp_data = result["extruder_temp"]
                if isinstance(temp_data, dict) and "min" in temp_data and "max" in temp_data:
                    # Cache the result with timestamp
                    self._filament_temp_cache[cache_key] = (temp_data, time.time())

                    # LRU eviction: remove oldest entry if cache is full
                    if len(self._filament_temp_cache) > self._max_cache_size:
                        oldest_key = next(iter(self._filament_temp_cache))
                        self._filament_temp_cache.pop(oldest_key)
                        logging.debug(f"Evicted oldest cache entry: {oldest_key}")

                    logging.info(f"Cached temperature for unit {unit_id} gate {gate_index} (SKU: {sku}): {temp_data}")
                    return temp_data

            logging.warning(f"No temperature data in filament_info for unit {unit_id} gate {gate_index}")
            return None

        except Exception as e:
            logging.warning(f"Failed to get filament_info for unit {unit_id} gate {gate_index}: {e}")
            return None

    def _set_ace_status(self, filament_hub):
        # set units
        ace = self.ace
        ace.units = []
        ace.tools = []
        ace.ttg_map = []

        # Invalidate gate lookup cache when units change
        self._invalidate_gate_cache()

        # Track global gate index across all units for tool mapping
        global_gate_index = 0

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
                sku: str = slot["sku"] if "sku" in slot else ""
                type: str = slot["type"] if "type" in slot else None
                color: list[int] = slot["color"] if "color" in slot else None
                rfid: int = slot["rfid"] if "rfid" in slot else None
                source: int = slot["source"] if "source" in slot else None
                temp_data: dict = slot["temperature"] if "temperature" in slot else None

                gate = MmuAceGate()
                gate.index = index
                gate.material = type
                gate.filament_name = type
                gate.color = rgb_to_rgba(color)
                gate.rfid = rfid
                gate.source = source
                gate.status = GATE_AVAILABLE if status == "ready" else GATE_EMPTY if status == "empty" or status == "runout" else GATE_UNKNOWN

                # Set temperature from RFID tag if available, otherwise use material default
                if temp_data and isinstance(temp_data, dict) and "min" in temp_data:
                    # Store both min and max from RFID tag
                    gate.temperature_min = temp_data.get("min", -1)
                    gate.temperature_max = temp_data.get("max", -1)
                    # Use min temperature as default (more conservative)
                    gate.temperature = gate.temperature_min
                    logging.info(f"Gate {index}: Using RFID temperatures min={gate.temperature_min}°C, max={gate.temperature_max}°C")
                elif type:
                    # Fallback to material-based default (no min/max range for defaults)
                    gate.temperature = get_material_temperature(type)
                    gate.temperature_min = -1
                    gate.temperature_max = -1
                    logging.info(f"Gate {index}: Using material default temperature {gate.temperature}°C for {type}")

                # Parse SKU for additional information
                gate.sku = sku
                if sku:
                    sku_info = parse_anycubic_sku(sku)
                    gate.vendor = sku_info["vendor"]
                    gate.series = sku_info["series"]
                    gate.color_name = sku_info["color_name"]
                    # Use serial number as spool_id if available
                    try:
                        gate.spool_id = int(sku_info["serial"]) if sku_info["serial"] else abs(hash(sku)) % (2**31)
                    except:
                        gate.spool_id = abs(hash(sku)) % (2**31)

                    # Update filament_name with full description if parsed
                    if sku_info["vendor"] and sku_info["series"]:
                        parts = [sku_info["vendor"], sku_info["series"], sku_info["material_type"]]
                        if sku_info["color_name"]:
                            parts.append(sku_info["color_name"])
                        gate.filament_name = " ".join(parts)
                else:
                    gate.spool_id = 0

                unit.gates.append(gate)

                # Create tool with global index (spans across all units)
                # Tool 0 = Unit 0 Gate 0, Tool 4 = Unit 1 Gate 0, etc.
                tool = MmuAceTool()
                tool.name = f"T{global_gate_index}"
                self.ace.tools.append(tool)
                self.ace.ttg_map.append(global_gate_index)

                global_gate_index += 1

            self.ace.units.append(unit)

        # Sync MMU status with ACE Hub current_filament state
        # Only sync if MMU thinks filament is loaded (pos == LOADED) but ACE Hub disagrees
        current_filament = filament_hub.get("current_filament", "")

        # If MMU thinks filament is LOADED but ACE Hub says nothing loaded -> sync (reset)
        if self.ace.filament.pos == FILAMENT_POS_LOADED and (not current_filament or current_filament == ""):
            logging.info(f"_set_ace_status: MMU thinks loaded but ACE Hub current_filament is empty, resetting MMU status")
            self.ace.gate = -1
            self.ace.tool = -1
            self.ace.filament.pos = FILAMENT_POS_UNLOADED
        # If ACE Hub says filament loaded but MMU doesn't know -> sync (set loaded)
        elif current_filament and current_filament != "" and self.ace.filament.pos != FILAMENT_POS_LOADED:
            # Parse current_filament (format: "unit_id-gate_index" like "0-1")
            try:
                parts = current_filament.split("-")
                if len(parts) == 2:
                    unit_id = int(parts[0])
                    local_gate = int(parts[1])
                    # Calculate global gate index
                    global_gate = (unit_id * 4) + local_gate
                    logging.info(f"_set_ace_status: ACE Hub current_filament='{current_filament}', setting MMU gate={global_gate}")
                    self.ace.gate = global_gate
                    self.ace.tool = global_gate  # Tool = Gate for ACE
                    self.ace.filament.pos = FILAMENT_POS_LOADED
            except Exception as e:
                logging.error(f"_set_ace_status: Failed to parse current_filament '{current_filament}': {e}")
        # Otherwise: MMU status and ACE Hub agree, or MMU is in selection state (gate >= 0 but not loaded) - don't interfere

        self._handle_status_update(force=True)

    def get_status(self) -> MmuAceStatus:

        gates = [gate for gates in [unit.gates for unit in self.ace.units] for gate in gates]
        num_gates = len(gates)
        gate_status = [gate.status for gate in gates]
        gate_filament_name = [gate.filament_name if gate.filament_name else "" for gate in gates]
        gate_material = [gate.material if gate.material else "" for gate in gates]
        gate_color = [rgba_to_hex(gate.color) if gate.color is not None else "000000FF" for gate in gates]
        gate_temperature = [gate.temperature if gate.temperature >= 0 else 0 for gate in gates]
        gate_temperature_min = [gate.temperature_min if hasattr(gate, 'temperature_min') and gate.temperature_min >= 0 else 0 for gate in gates]
        gate_temperature_max = [gate.temperature_max if hasattr(gate, 'temperature_max') and gate.temperature_max >= 0 else 0 for gate in gates]
        gate_spool_id = [gate.spool_id if gate.spool_id >= 0 else 0 for gate in gates]
        gate_speed_override = [gate.speed_override if gate.speed_override >= 0 else 100 for gate in gates]
        gate_vendor = [gate.vendor if hasattr(gate, 'vendor') and gate.vendor else "" for gate in gates]

        # Determine filament_pos based on loaded_gate vs selected gate
        # This controls Load/Unload button visibility in Happy Hare GUI
        if self.ace.loaded_gate != TOOL_GATE_UNKNOWN and self.ace.loaded_gate == self.ace.gate:
            # Currently selected gate is the one that's loaded -> show LOADED (Unload button)
            filament_pos = FILAMENT_POS_LOADED
        else:
            # Either no gate loaded, or different gate selected -> show UNLOADED (Load button)
            filament_pos = FILAMENT_POS_UNLOADED

        filament_name = "Unknown"
        filament_vendor = ""
        filament_material = ""
        filament_color = ""

        # Set filament info based on currently selected gate
        if self.ace.gate >= 0 and self.ace.gate < len(gates):
            current_gate = gates[self.ace.gate]
            if current_gate.status == GATE_AVAILABLE or current_gate.status == GATE_AVAILABLE_FROM_BUFFER:
                # Gate has filament - show its info
                filament_name = current_gate.filament_name if current_gate.filament_name else current_gate.material
                filament_vendor = current_gate.vendor if hasattr(current_gate, 'vendor') and current_gate.vendor else ""
                filament_material = current_gate.material if current_gate.material else ""
                filament_color = rgba_to_hex(current_gate.color) if current_gate.color else "000000FF"
            elif current_gate.status == GATE_EMPTY:
                # Gate is empty
                filament_name = "Empty"

        # Create active_filament status with proper structure
        # empty is True if no filament loaded, False if loaded
        active_filament_status = ActiveFilamentStatus(
            empty=(filament_pos != FILAMENT_POS_LOADED),
            vendor=filament_vendor,
            manufacturer=filament_vendor,  # Same as vendor (alias for Fluidd compatibility)
            material=filament_material,
            color=filament_color
        )

        # ACE has no encoder - return null to hide encoder UI completely
        # Fluidd expects null when no encoder is present, not a disabled encoder object
        encoder_status = None

        # Ensure endless_spool_groups has correct length (Fluidd expects array with num_gates entries)
        endless_spool_groups = self.ace.endless_spool_groups
        if len(endless_spool_groups) != num_gates:
            # Fill with zeros if empty or wrong length
            endless_spool_groups = [0] * num_gates

        return MmuAceStatus(
            mmu = MmuStatus(
                enabled = self.ace.enabled,
                encoder = encoder_status,
                num_gates = num_gates,
                print_state = self.ace.print_state.value,
                is_paused = self.ace.is_paused,
                is_homed = self.ace.is_homed,
                unit = self.ace.unit,
                gate = self.ace.gate,
                tool = self.ace.tool,
                active_filament = active_filament_status,
                num_toolchanges = self.ace.num_toolchanges,
                last_tool = self.ace.last_tool,
                next_tool = self.ace.next_tool,
                toolchange_purge_volume = 0,
                last_toolchange = "",
                operation = self.ace.operation,
                filament = filament_name,  # Calculated from current gate
                filament_position = self.ace.filament.position,
                filament_pos = filament_pos,  # Calculated based on gate status
                filament_direction = self.ace.filament.direction,
                ttg_map = self.ace.ttg_map,
                endless_spool_groups = endless_spool_groups,
                gate_status = gate_status,
                gate_filament_name = gate_filament_name,
                gate_material = gate_material,
                gate_color = gate_color,
                gate_temperature = gate_temperature,
                gate_temperature_min = gate_temperature_min,
                gate_temperature_max = gate_temperature_max,
                gate_spool_id = gate_spool_id,
                gate_speed_override = gate_speed_override,
                gate_vendor = gate_vendor,
                slicer_tool_map = self.get_tools_status(),
                action = self.ace.action,
                has_bypass = False,
                sync_drive = False,
                sync_feedback_enabled = False,
                clog_detection_enabled = False,
                endless_spool_enabled = True,  # Enable endless spool for backup roll functionality
                reason_for_pause = "",
                extruder_filament_remaining = -1,
                spoolman_support = "off",  # off/readonly/push/pull - we don't use spoolman
                sensors = {},
                espooler_active = "",
                servo = "",
                grip = "",
            ),
            mmu_machine = self.get_machine_status()
        )

    def get_machine_status(self):
        # Create dummy unit_1 if only 1 unit exists (Fluidd can't handle null)
        dummy_unit = MmuUnitStatus(
            name="",
            vendor="",
            version="",
            num_gates=0,
            first_gate=0,
            selector_type="",
            variable_rotation_distances=False,
            variable_bowden_lengths=False,
            require_bowden_move=False,
            filament_always_gripped=False,
            has_bypass=False,
            multi_gear=False,
            dryer_status="stop",
            dryer_temp=0,
            dryer_target_temp=0,
            dryer_remaining=0,
            dryer_humidity=0
        )

        return MmuMachineStatus(
            num_units = len(self.ace.units),
            unit_0 = self.get_unit_status(self.ace.units[0], 0) if len(self.ace.units) >= 1 else dummy_unit,
            unit_1 = self.get_unit_status(self.ace.units[1], 1) if len(self.ace.units) >= 2 else dummy_unit,
        )

    def get_unit_status(self, unit: MmuAceUnit, index: int):
        status = MmuUnitStatus(
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

        # Add dryer status if available
        if hasattr(unit, 'dryer') and unit.dryer:
            status.dryer_status = unit.dryer.get("status", "stop")
            status.dryer_temp = unit.dryer.get("temp", 0)
            status.dryer_target_temp = unit.dryer.get("target_temp", 0)
            status.dryer_remaining = unit.dryer.get("remaining_time", 0)
            status.dryer_humidity = unit.dryer.get("humidity", 0)

        return status

    def get_tools_status(self):
        return MmuSlicerToolMapStatus([self.get_tool_status(tool_index, tool) for tool_index, tool in enumerate(self.ace.tools)])

    def get_tool_status(self, tool_index: int, tool: MmuAceTool):
        # Get gate info from ttg_map
        gate_index = self.ace.ttg_map[tool_index] if tool_index < len(self.ace.ttg_map) else -1

        # Find the gate using cached lookup
        gate = None
        if gate_index >= 0:
            gate_lookup = self._get_gate_by_index(gate_index)
            if gate_lookup:
                unit, gate = gate_lookup

        # Use gate info if available, otherwise use tool defaults
        if gate and gate.status != GATE_EMPTY:
            # Gate has filament - use gate info
            temp = gate.temperature if gate.temperature > 0 else tool.temp
            if temp <= 0 and gate.material:
                temp = get_material_temperature(gate.material)

            return MmuToolStatus(
                material = gate.filament_name if gate.filament_name else tool.material,
                temp = temp,
                name = tool.name,
                in_use = tool.in_use,
            )
        else:
            # Gate is empty - show "Empty" instead of "Unknown"
            return MmuToolStatus(
                material = "Empty",
                temp = 0,  # No temperature for empty gates
                name = tool.name,
                in_use = tool.in_use,
            )

    def update_ttg_map(self, ttg_map: List[int]):
        self.ace.ttg_map = ttg_map
        self._handle_status_update(force=False)  # Debounce for UI edits

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
        # Use cached gate lookup
        gate_lookup = self._get_gate_by_index(gate_index)
        if not gate_lookup:
            logging.warning(f"update gate {gate_index} not found")
            return

        unit, gate = gate_lookup

        logging.debug(f"update gate {gate_index} actual values {json.dumps(gate.__dict__)}")

        if color is None:
            color = [0, 0, 0, 0]

        if gate.rfid == 2:
            logging.warning(f"update gate {gate_index} not allowed, RFID tag is locked")
            return

        logging.debug(f"updating gate {gate_index} (rfid={gate.rfid})")

        # Update local gate values immediately for UI responsiveness
        gate.status = status
        gate.filament_name = filament_name
        gate.material = material
        gate.color = color
        gate.temperature = temperature
        gate.spool_id = spool_id
        gate.speed_override = speed_override

        # Try to sync with GoKlipper (only works if gate has RFID tag)
        # {"method":"filament_hub/set_filament_info","params":{"color":{"B":65,"G":209,"R":254},"id":0,"index":2,"type":"PLA"},"id":34}
        params = {
            "color": {"R": color[0], "G": color[1], "B": color[2]},
            "id": unit.id, # ace id
            "index": gate.index, # slot index
            "type": material
        }

        try:
            result = await self.printer.send_request("filament_hub/set_filament_info", params)
            if result == "ok":
                logging.info(f"Gate {gate_index} synchronized with GoKlipper/ACE hardware")
            else:
                logging.info(f"Gate {gate_index} updated locally (no RFID tag, cannot sync to hardware)")
        except Exception as e:
            logging.info(f"Gate {gate_index} updated locally (no RFID tag, cannot sync to hardware): {e}")

        # Wait briefly for any pending subscription updates to complete
        await asyncio.sleep(0.1)

        # Trigger UI update with our local values
        self._handle_status_update(force=True)
        logging.debug(f"updated gate {gate_index}: {material} {filament_name}")

class MmuAcePatcher:

    ace: MmuAce
    ace_controller: MmuAceController
    kobra: Kobra
    _last_ttg_reset_time: float = 0.0

    def __init__(self, config: ConfigHelper):
        self.server = config.get_server()
        self.name = config.get_name()
        self.kobra = self.server.load_component(self.server.config, 'kobra')

        host = config.get("host", None)
        self.ace_controller = MmuAceController(self.server, host)

        self.reinit()

        # mmu test enpoints
        self.server.register_endpoint("/server/mmu-ace", ['GET'], self._handle_mmu_request)

        # Spoolman emulation removed - causes system freeze

        # dryer control endpoints
        self.server.register_endpoint("/server/filament_hub/start_drying", ['POST'], self._handle_start_drying)
        self.server.register_endpoint("/server/filament_hub/stop_drying", ['POST'], self._handle_stop_drying)
        self.server.register_endpoint("/server/filament_hub/set_fan_speed", ['POST'], self._handle_set_fan_speed)

        # mmu status update notification
        self.server.register_notification("mmu_ace:status_update")

        # gcode handlers
        self.register_gcode_handler("MMU_GATE_MAP", self._on_gcode_mmu_gate_map)
        self.register_gcode_handler("MMU_TTG_MAP", self._on_gcode_mmu_ttg_map)
        self.register_gcode_handler("MMU_ENDLESS_SPOOL", self._on_gcode_mmu_endless_spool)
        self.register_gcode_handler("MMU_SELECT", self._on_gcode_mmu_select)
        self.register_gcode_handler("MMU_SLICER_TOOL_MAP", self._on_gcode_mmu_slicer_tool_map)
        self.register_gcode_handler("MMU_LOAD", self._on_gcode_mmu_load)
        self.register_gcode_handler("MMU_UNLOAD", self._on_gcode_mmu_unload)
        self.register_gcode_handler("MMU_EJECT", self._on_gcode_mmu_eject)
        self.register_gcode_handler("MMU_HOME", self._on_gcode_mmu_home)
        self.register_gcode_handler("MMU_CHECK_GATE", self._on_gcode_mmu_check_gate)
        self.register_gcode_handler("MMU_CHECK_GATES", self._on_gcode_mmu_check_gates)
        self.register_gcode_handler("MMU_RECOVER", self._on_gcode_mmu_recover)
        self.register_gcode_handler("MMU_DRYER_START", self._on_gcode_dryer_start)
        self.register_gcode_handler("MMU_DRYER_STOP", self._on_gcode_dryer_stop)
        self.register_gcode_handler("MMU_DRYER_FAN_SPEED", self._on_gcode_dryer_fan_speed)

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

    def _get_gcode_arg_int(self, name: str, args: dict[str, str | None], default: int = None) -> int:
        """Get integer argument from G-code"""
        if name in args and args[name] is not None:
            try:
                return int(args[name])
            except ValueError:
                if default is not None:
                    return default
                raise ValueError(f"Invalid integer for {name}: {args[name]}")
        if default is not None:
            return default
        raise ValueError(f"Required parameter {name} not found")

    def _get_gcode_arg_float(self, name: str, args: dict[str, str | None], default: float = None) -> float:
        """Get float argument from G-code"""
        if name in args and args[name] is not None:
            try:
                return float(args[name])
            except ValueError:
                if default is not None:
                    return default
                raise ValueError(f"Invalid float for {name}: {args[name]}")
        if default is not None:
            return default
        raise ValueError(f"Required parameter {name} not found")

    async def _on_gcode_mmu_unknown(self, args: dict[str, str | None], delegate):
        pass

    async def _on_gcode_mmu_select(self, args: dict[str, str | None], delegate):
        """Select gate or tool (Happy Hare compatible)"""
        tool = self._get_gcode_arg_int("TOOL", args, default=-1)
        gate = self._get_gcode_arg_int("GATE", args, default=-1)
        bypass = self._get_gcode_arg_int("BYPASS", args, default=0)

        if bypass == 1:
            # ACE has no bypass - log warning
            logging.warning("MMU_SELECT BYPASS=1 not supported on ACE hardware")
            return

        if gate >= 0:
            # Direct gate selection
            num_gates = sum(len(unit.gates) for unit in self.ace.units)
            if gate < num_gates:
                self.ace.gate = gate

                # Find tool that maps to this gate (reverse TTG lookup)
                self.ace.tool = -1
                for tool_idx, gate_idx in enumerate(self.ace.ttg_map):
                    if gate_idx == gate:
                        self.ace.tool = tool_idx
                        break

                # Set filament_pos to UNLOADED (selection is not loading, just preparation)
                self.ace.filament.pos = FILAMENT_POS_UNLOADED

                self.ace_controller._handle_status_update(throttle=True)  # Throttle: max 3 updates/sec
                logging.info(f"Selected gate {gate}, tool {self.ace.tool}, filament_pos set to UNLOADED")
            else:
                logging.error(f"Invalid gate {gate}, total gates: {num_gates}")
        elif tool >= 0:
            # Resolve tool to gate via TTG map
            if tool < len(self.ace.ttg_map):
                self.ace.gate = self.ace.ttg_map[tool]
                self.ace.tool = tool

                # Set filament_pos to UNLOADED (selection is not loading, just preparation)
                self.ace.filament.pos = FILAMENT_POS_UNLOADED

                self.ace_controller._handle_status_update(throttle=True)  # Throttle: max 3 updates/sec
                logging.info(f"Selected tool {tool} -> gate {self.ace.gate}, filament_pos set to UNLOADED")
            else:
                logging.error(f"Invalid tool {tool}, total tools: {len(self.ace.ttg_map)}")

    async def _on_gcode_mmu_slicer_tool_map(self, args: dict[str, str | None], delegate):
        """Set slicer tool mapping (Happy Hare compatible)"""
        # Check if this is just a control command (SKIP_AUTOMAP without TOOL)
        if "TOOL" not in args and "SKIP_AUTOMAP" in args:
            logging.info("MMU_SLICER_TOOL_MAP: Skipping automap (control command)")
            return None

        tool = self._get_gcode_arg_int("TOOL", args)
        material = self._get_gcode_arg_str_def("MATERIAL", args, "Unknown")
        color = self._get_gcode_arg_str_def("COLOR", args, None)
        temp = self._get_gcode_arg_int("TEMP", args, default=-1)
        name = self._get_gcode_arg_str_def("NAME", args, f"Tool {tool}")
        used = self._get_gcode_arg_int("USED", args, default=1)

        # Check tool index against maximum limit (memory management)
        if tool >= MAX_TOOLS:
            logging.warning(f"Tool index {tool} exceeds maximum {MAX_TOOLS}, ignoring")
            return None

        # Ensure tool exists (with limit check)
        while len(self.ace.tools) <= tool:
            if len(self.ace.tools) >= MAX_TOOLS:
                logging.error(f"Cannot add tool {tool}, maximum {MAX_TOOLS} reached")
                return None
            new_tool = MmuAceTool()
            new_tool.name = f"T{len(self.ace.tools)}"
            self.ace.tools.append(new_tool)

        # Update tool properties
        self.ace.tools[tool].material = material
        self.ace.tools[tool].temp = temp
        self.ace.tools[tool].name = name
        self.ace.tools[tool].in_use = (used == 1)

        self.ace_controller._handle_status_update(force=False)  # Debounce for batch updates
        logging.info(f"Updated tool {tool}: {material} @ {temp}°C")

    async def _send_gcode_response(self, message: str):
        """Send a response message to the console via notification"""
        try:
            # Send as a gcode_response notification to show in Fluidd console
            self.server.send_event("server:gcode_response", message)
        except Exception as e:
            logging.error(f"Failed to send gcode response: {e}")

    async def _ensure_extruder_temp(self, gate: int, min_temp: int = 170) -> bool:
        """Ensure extruder is heated to proper temperature for filament operations.

        Args:
            gate: Gate index (0-7) to get target temperature from
            min_temp: Minimum extrusion temperature (default: 170°C)

        Returns:
            True if temperature is OK, False if error occurred
        """
        try:
            # Query current extruder state
            result = await self.ace_controller.printer.query_objects({
                "extruder": ["temperature", "target"]
            })

            current_temp = result["extruder"]["temperature"]
            target_temp = result["extruder"]["target"]

            # Get gate-specific temperature if available
            gate_temp = min_temp
            gate_lookup = self.ace_controller._get_gate_by_index(gate)
            if gate_lookup:
                unit, gate_obj = gate_lookup
                if gate_obj.temperature > 0:
                    gate_temp = gate_obj.temperature

            # Check if already hot enough (need gate_temp, not just min_temp)
            if current_temp >= gate_temp:
                message = f"Extruder temperature OK: {current_temp:.1f}°C (gate requires {gate_temp}°C)"
                logging.info(message)
                await self._send_gcode_response(message)
                return True

            # Set target temperature if not already set
            if target_temp < gate_temp:
                message = f"Heating extruder to {gate_temp}°C (gate {gate} requires {gate_temp}°C)..."
                logging.info(message)
                await self._send_gcode_response(message)

                # Send M104 to set temperature
                await self.ace_controller.printer.send_gcode(f"M104 S{gate_temp}")

            # Wait for temperature (with timeout) - wait for gate_temp, not min_temp
            message = f"Waiting for extruder to reach {gate_temp}°C (current: {current_temp:.1f}°C)..."
            logging.info(message)
            await self._send_gcode_response(message)

            # Poll temperature until gate_temp reached (max 5 minutes)
            # Adaptive polling: slower when far away, faster when close
            max_wait = 300  # 5 minutes
            elapsed = 0

            while elapsed < max_wait:
                # Check current temperature
                result = await self.ace_controller.printer.query_objects({
                    "extruder": ["temperature"]
                })
                current_temp = result["extruder"]["temperature"]

                if current_temp >= gate_temp:
                    message = f"Extruder ready: {current_temp:.1f}°C"
                    logging.info(message)
                    await self._send_gcode_response(message)
                    return True

                # Adaptive polling interval based on temperature difference
                temp_diff = gate_temp - current_temp
                if temp_diff > 50:
                    poll_interval = 5  # Far away: slow polling (reduces API calls)
                elif temp_diff > 10:
                    poll_interval = 2  # Medium distance: normal polling
                else:
                    poll_interval = 0.5  # Close to target: fast polling (quicker response)

                # Progress update every 10 seconds (independent of poll interval)
                if elapsed % 10 == 0:
                    message = f"Heating... {current_temp:.1f}°C / {gate_temp}°C ({elapsed}s elapsed)"
                    logging.info(message)
                    await self._send_gcode_response(message)

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            # Timeout
            message = f"ERROR: Extruder heating timeout after {max_wait}s (current: {current_temp:.1f}°C, target: {gate_temp}°C)"
            logging.error(message)
            await self._send_gcode_response(message)
            return False

        except Exception as e:
            message = f"ERROR: Failed to check/heat extruder: {e}"
            logging.error(message)
            await self._send_gcode_response(message)
            return False

    async def _on_gcode_mmu_load(self, args: dict[str, str | None], delegate):
        """Manual load filament: MMU_LOAD [GATE=0] [LENGTH=100] [SPEED=25]

        Uses GoKlipper's FEED_FILAMENT G-code command internally.
        Automatically heats extruder to proper temperature for selected gate.
        If GATE not specified, uses currently selected gate from MMU_SELECT.
        """
        gate = self._get_gcode_arg_int("GATE", args, -1)
        length = self._get_gcode_arg_float("LENGTH", args, default=100.0)
        speed = self._get_gcode_arg_float("SPEED", args, default=25.0)

        # Use currently selected gate if no GATE parameter provided
        if gate < 0:
            gate = self.ace.gate
            if gate < 0:
                message = "MMU_LOAD: No gate selected. Use MMU_SELECT GATE=X first or provide GATE parameter"
                logging.error(message)
                await self._send_gcode_response(message)
                return None
            logging.info(f"MMU_LOAD: Using currently selected gate {gate}")

        # Check if a different gate is already loaded - if so, unload it first
        if self.ace.loaded_gate != TOOL_GATE_UNKNOWN and self.ace.loaded_gate != gate:
            message = f"MMU_LOAD: Gate {self.ace.loaded_gate} is currently loaded. Unloading it first before loading gate {gate}..."
            logging.info(message)
            await self._send_gcode_response(message)

            # Call MMU_UNLOAD with the currently loaded gate
            await self._on_gcode_mmu_unload({"GATE": str(self.ace.loaded_gate)}, None)

            # After unload, continue with load of new gate
            message = f"MMU_LOAD: Unload complete. Now loading gate {gate}..."
            logging.info(message)
            await self._send_gcode_response(message)

        # Ensure extruder is heated to proper temperature
        if not await self._ensure_extruder_temp(gate):
            message = "MMU_LOAD: Extruder temperature check failed - aborting"
            logging.error(message)
            await self._send_gcode_response(message)
            return None

        # Determine local gate index (GoKlipper's FEED_FILAMENT uses INDEX 0-3, not global gate)
        local_index = gate % 4

        # Build G-code command for GoKlipper
        gcode = f"FEED_FILAMENT INDEX={local_index} LENGTH={int(length)} SPEED={int(speed)}"

        try:
            # Send directly to GoKlipper via G-code
            await self.ace_controller.printer.send_gcode(gcode)

            # Update MMU status after successful load
            self.ace.gate = gate
            self.ace.tool = gate  # Tool = Gate for ACE
            self.ace.loaded_gate = gate  # Track which gate is physically loaded
            self.ace.filament.pos = FILAMENT_POS_LOADED
            self.ace_controller._handle_status_update(force=True)

            message = f"MMU_LOAD: Loading {length}mm from gate {gate} (index {local_index}) at {speed}mm/s completed, MMU status updated"
            logging.info(message)
            await self._send_gcode_response(message)
        except Exception as e:
            message = f"MMU_LOAD failed: {e}"
            logging.error(message)
            await self._send_gcode_response(message)

        return None  # Don't execute original command

    async def _on_gcode_mmu_unload(self, args: dict[str, str | None], delegate):
        """Manual unload filament: MMU_UNLOAD [GATE=0] [LENGTH=100] [SPEED=20]

        Uses GoKlipper's UNWIND_FILAMENT or UNWIND_ALL_FILAMENT G-code command internally.
        Automatically heats extruder to min_extrude_temp if needed.
        If GATE not specified, uses UNWIND_ALL_FILAMENT to unload all gates.
        """
        gate = self._get_gcode_arg_int("GATE", args, -1)
        length = self._get_gcode_arg_float("LENGTH", args, default=100.0)
        speed = self._get_gcode_arg_float("SPEED", args, default=20.0)

        # If no gate specified, use UNWIND_ALL_FILAMENT
        if gate < 0:
            logging.info("MMU_UNLOAD: No GATE parameter, using UNWIND_ALL_FILAMENT")

            # Find highest minimum temperature among all loaded gates
            # Since Kobra 3 has no cutter and only unloads by heat, we need
            # the highest temperature to safely unload ALL filaments
            max_min_temp = 170  # Start with min_extrude_temp as fallback
            gates_with_temp = []

            for unit in self.ace.units:
                for gate_obj in unit.gates:
                    # Check if gate has filament loaded (status >= 1)
                    if gate_obj.status >= 1:
                        gate_min_temp = gate_obj.temperature_min if hasattr(gate_obj, 'temperature_min') and gate_obj.temperature_min > 0 else gate_obj.temperature
                        if gate_min_temp > 0:
                            max_min_temp = max(max_min_temp, gate_min_temp)
                            gates_with_temp.append((gate_obj.index, gate_min_temp))

            if gates_with_temp:
                logging.info(f"MMU_UNLOAD: Found loaded gates with temps: {gates_with_temp}, using max={max_min_temp}°C")
            else:
                logging.info(f"MMU_UNLOAD: No gates with temp data, using min_extrude_temp={max_min_temp}°C")

            # Heat to highest minimum temperature
            try:
                result = await self.ace_controller.printer.query_objects({
                    "extruder": ["temperature", "target"]
                })
                current_temp = result["extruder"]["temperature"]

                if current_temp < max_min_temp:
                    message = f"Heating extruder to {max_min_temp}°C (highest min temp of loaded filaments)..."
                    logging.info(message)
                    await self._send_gcode_response(message)
                    await self.ace_controller.printer.send_gcode(f"M104 S{max_min_temp}")

                    # Wait for temperature
                    message = f"Waiting for extruder to reach {max_min_temp}°C (current: {current_temp:.1f}°C)..."
                    logging.info(message)
                    await self._send_gcode_response(message)

                    max_wait = 300  # 5 minutes
                    elapsed = 0

                    while elapsed < max_wait:
                        result = await self.ace_controller.printer.query_objects({
                            "extruder": ["temperature"]
                        })
                        current_temp = result["extruder"]["temperature"]

                        if current_temp >= max_min_temp:
                            message = f"Extruder ready: {current_temp:.1f}°C"
                            logging.info(message)
                            await self._send_gcode_response(message)
                            break

                        # Adaptive polling interval
                        temp_diff = max_min_temp - current_temp
                        if temp_diff > 50:
                            poll_interval = 5
                        elif temp_diff > 10:
                            poll_interval = 2
                        else:
                            poll_interval = 0.5

                        if elapsed % 10 == 0:
                            message = f"Heating... {current_temp:.1f}°C / {max_min_temp}°C ({elapsed}s elapsed)"
                            logging.info(message)
                            await self._send_gcode_response(message)

                        await asyncio.sleep(poll_interval)
                        elapsed += poll_interval

                    if current_temp < max_min_temp:
                        message = f"ERROR: Heating timeout after {max_wait}s (current: {current_temp:.1f}°C, target: {max_min_temp}°C)"
                        logging.error(message)
                        await self._send_gcode_response(message)
                        return None
                else:
                    message = f"Extruder temperature OK: {current_temp:.1f}°C (>= {max_min_temp}°C)"
                    logging.info(message)
                    await self._send_gcode_response(message)

            except Exception as e:
                message = f"ERROR: Failed to check/heat extruder: {e}"
                logging.error(message)
                await self._send_gcode_response(message)
                return None

            try:
                # Unload all filaments
                await self.ace_controller.printer.send_gcode("UNWIND_ALL_FILAMENT")

                # Reset MMU status after unload
                self.ace.gate = -1
                self.ace.tool = -1
                self.ace.loaded_gate = TOOL_GATE_UNKNOWN  # No gate loaded anymore
                self.ace.filament.pos = FILAMENT_POS_UNLOADED
                self.ace_controller._handle_status_update(force=True)

                message = "MMU_UNLOAD: Unloading all filaments completed, MMU status reset"
                logging.info(message)
                await self._send_gcode_response(message)
            except Exception as e:
                message = f"MMU_UNLOAD failed: {e}"
                logging.error(message)
                await self._send_gcode_response(message)

            return None  # Don't execute original command

        # Ensure extruder is heated to gate-specific temperature
        if not await self._ensure_extruder_temp(gate):
            message = "MMU_UNLOAD: Extruder temperature check failed - aborting"
            logging.error(message)
            await self._send_gcode_response(message)
            return None

        # Determine local gate index (GoKlipper's UNWIND_FILAMENT uses INDEX 0-3, not global gate)
        local_index = gate % 4

        # Build G-code command for GoKlipper
        gcode = f"UNWIND_FILAMENT INDEX={local_index} LENGTH={int(length)} SPEED={int(speed)}"

        try:
            # Send directly to GoKlipper via G-code
            await self.ace_controller.printer.send_gcode(gcode)

            # Reset MMU status after unload
            self.ace.gate = -1
            self.ace.tool = -1
            self.ace.loaded_gate = TOOL_GATE_UNKNOWN  # No gate loaded anymore
            self.ace.filament.pos = FILAMENT_POS_UNLOADED
            self.ace_controller._handle_status_update(force=True)

            message = f"MMU_UNLOAD: Unloading {length}mm from gate {gate} (index {local_index}) at {speed}mm/s completed, MMU status reset"
            logging.info(message)
            await self._send_gcode_response(message)
        except Exception as e:
            message = f"MMU_UNLOAD failed: {e}"
            logging.error(message)
            await self._send_gcode_response(message)

        return None  # Don't execute original command

    async def _on_gcode_mmu_eject(self, args: dict[str, str | None], delegate):
        """Manual eject filament: MMU_EJECT GATE=0 [LENGTH=500] [SPEED=20]

        Uses GoKlipper's UNWIND_FILAMENT G-code command internally with longer distance.
        Automatically heats extruder to min_extrude_temp if needed.
        """
        gate = self._get_gcode_arg_int("GATE", args, -1)
        length = self._get_gcode_arg_float("LENGTH", args, default=500.0)  # Eject more for full removal
        speed = self._get_gcode_arg_float("SPEED", args, default=20.0)

        if gate < 0:
            message = "MMU_EJECT: GATE parameter required (0-7)"
            logging.error(message)
            await self._send_gcode_response(message)
            return None

        # Ensure extruder is heated to minimum temperature for retraction
        if not await self._ensure_extruder_temp(gate):
            message = "MMU_EJECT: Extruder temperature check failed - aborting"
            logging.error(message)
            await self._send_gcode_response(message)
            return None

        # Determine local gate index (GoKlipper's UNWIND_FILAMENT uses INDEX 0-3, not global gate)
        local_index = gate % 4

        # Build G-code command for GoKlipper (EJECT is just UNWIND with longer distance)
        gcode = f"UNWIND_FILAMENT INDEX={local_index} LENGTH={int(length)} SPEED={int(speed)}"

        try:
            # Send directly to GoKlipper via G-code
            await self.ace_controller.printer.send_gcode(gcode)

            # Reset MMU status after eject
            self.ace.gate = -1
            self.ace.tool = -1
            self.ace.filament.pos = FILAMENT_POS_UNLOADED
            self.ace_controller._handle_status_update(force=True)

            message = f"MMU_EJECT: Ejecting {length}mm from gate {gate} (index {local_index}) at {speed}mm/s completed, MMU status reset"
            logging.info(message)
            await self._send_gcode_response(message)
        except Exception as e:
            message = f"MMU_EJECT failed: {e}"
            logging.error(message)
            await self._send_gcode_response(message)

        return None  # Don't execute original command

    async def _on_gcode_mmu_home(self, args: dict[str, str | None], delegate):
        """Homing not needed - ACE selector is virtual"""
        # Keep is_homed = False to disable manual load/unload buttons in Fluidd
        # ACE handles filament changes automatically during print
        message = "MMU_HOME: ACE selector is virtual - no homing needed"
        logging.info(message)
        await self._send_gcode_response(message)
        return None  # Don't execute original command

    async def _on_gcode_mmu_check_gate(self, args: dict[str, str | None], delegate):
        """Check a specific gate for filament - ACE detects via RFID automatically"""
        gate = self._get_gcode_arg_int("GATE", args, -1)

        # Trigger status update to refresh RFID data
        self.ace_controller._handle_status_update(force=True)

        # Build status message for the specific gate
        if gate >= 0 and gate < len(self.ace.units[0].gates):
            gate_obj = self.ace.units[0].gates[gate]
            if gate_obj.status == GATE_AVAILABLE or gate_obj.status == GATE_AVAILABLE_FROM_BUFFER:
                message = f"MMU_CHECK_GATE: Gate #{gate} - AVAILABLE ({gate_obj.filament_name})"
            elif gate_obj.status == GATE_EMPTY:
                message = f"MMU_CHECK_GATE: Gate #{gate} - EMPTY"
            else:
                message = f"MMU_CHECK_GATE: Gate #{gate} - UNKNOWN"
        else:
            message = f"MMU_CHECK_GATE: ACE detects gates automatically via RFID"

        logging.info(message)
        await self._send_gcode_response(message)
        return None  # Don't execute original command

    async def _on_gcode_mmu_check_gates(self, args: dict[str, str | None], delegate):
        """Check all gates for filament - ACE detects via RFID automatically"""

        # Trigger status update to refresh RFID data
        self.ace_controller._handle_status_update(force=True)

        # Build status summary for all gates
        gates_status = []
        for i, gate in enumerate(self.ace.units[0].gates):
            if gate.status == GATE_AVAILABLE or gate.status == GATE_AVAILABLE_FROM_BUFFER:
                gates_status.append(f"Gate #{i}: AVAILABLE ({gate.filament_name})")
            elif gate.status == GATE_EMPTY:
                gates_status.append(f"Gate #{i}: EMPTY")
            else:
                gates_status.append(f"Gate #{i}: UNKNOWN")

        message = f"MMU_CHECK_GATES: ACE RFID Detection - {' | '.join(gates_status)}"
        logging.info(message)
        await self._send_gcode_response(message)
        return None  # Don't execute original command

    async def _on_gcode_mmu_recover(self, args: dict[str, str | None], delegate):
        """Recover MMU state - refresh ACE status and RFID data"""

        # Trigger full status update to refresh all ACE data
        self.ace_controller._handle_status_update(force=True)

        # Build recovery status message
        num_available = sum(1 for gate in self.ace.units[0].gates if gate.status in [GATE_AVAILABLE, GATE_AVAILABLE_FROM_BUFFER])
        num_empty = sum(1 for gate in self.ace.units[0].gates if gate.status == GATE_EMPTY)

        message = f"MMU_RECOVER: ACE status refreshed - {num_available} gates available, {num_empty} gates empty"
        logging.info(message)
        await self._send_gcode_response(message)
        return None  # Don't execute original command

    # Triggered on ToolToGate edit in ui
    async def _on_gcode_mmu_ttg_map(self, args: dict[str, str | None], delegate):
        logging.debug(f"handle mmu_ttg_map: {json.dumps(args)}")

        # Check if this is a reset command
        reset = self._get_gcode_arg_int("RESET", args, default=0)
        if reset == 1:
            # Reset to default: Tool 0 → Gate 0, Tool 1 → Gate 1, etc.
            num_gates = sum(len(unit.gates) for unit in self.ace.units)
            ttg_map = list(range(num_gates))
            logging.info(f"MMU_TTG_MAP: Reset to default {ttg_map}")
            self.ace_controller.update_ttg_map(ttg_map)
            # Block further MAP updates for 2 seconds to prevent Fluidd from re-applying old map
            self._last_ttg_reset_time = time.time()
            return None

        # Check if we're within cooldown period after a reset
        cooldown_period = 2.0  # seconds
        time_since_reset = time.time() - self._last_ttg_reset_time
        if time_since_reset < cooldown_period:
            logging.info(f"MMU_TTG_MAP: Ignoring MAP update within {cooldown_period}s cooldown after RESET (elapsed: {time_since_reset:.2f}s)")
            return None

        ttg_map_str = self._get_gcode_arg_str("MAP", args)
        ttg_map = [int(value) for value in ttg_map_str.split(",")]
        self.ace_controller.update_ttg_map(ttg_map)

    # Triggered on ToolToGate edit in ui
    async def _on_gcode_mmu_endless_spool(self, args: dict[str, str | None], delegate):
        """Configure endless spool groups (Happy Hare compatible)"""
        logging.debug(f"handle _on_gcode_mmu_endless_spool: {json.dumps(args)}")
        groups_str = self._get_gcode_arg_str("GROUPS", args)
        logging.debug(f"handle _on_gcode_mmu_endless_spool groups_str: {groups_str}")

        # Parse groups: "0,0,1,1" means gate 0+1 are group 0, gate 2+3 are group 1
        # Handle empty strings (e.g., ",,0" becomes [0, 0, 0])
        groups = [int(g) if g.strip() else 0 for g in groups_str.split(",")]

        # Validate
        num_gates = sum(len(unit.gates) for unit in self.ace.units)
        if len(groups) != num_gates:
            logging.error(f"GROUPS length {len(groups)} != num_gates {num_gates}")
            return

        self.ace.endless_spool_groups = groups
        self.ace_controller._handle_status_update(force=False)  # Debounce

        logging.info(f"Endless spool groups updated: {groups}")

    # Triggered on spool edit in ui
    async def _on_gcode_mmu_gate_map(self, args: dict[str, str | None], delegate):
        logging.debug(f"handle mmu_gate_map: {json.dumps(args)}")
        gate_map_str = self._get_gcode_arg_str("MAP", args)
        logging.debug(f"handle mmu_gate_map gate_map_str: {gate_map_str}")
        gate_map = ast.literal_eval(gate_map_str)
        logging.debug(f"handle mmu_gate_map gate_map: {json.dumps(gate_map)}")

        for key, value in gate_map.items():
            gate_index = int(key)

            logging.debug(f"try update gate {key}: {json.dumps(value)}")

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

    async def _on_gcode_dryer_start(self, args: dict[str, str | None], delegate):
        """Start dryer: MMU_DRYER_START UNIT=0 DURATION=120 [TEMP=45] [FAN_SPEED=0]

        TEMP is optional and defaults to 45°C (suitable for PLA).
        Use 55°C for PETG, 65°C for ABS.
        """
        unit = self._get_gcode_arg_int("UNIT", args, default=0)
        duration = self._get_gcode_arg_int("DURATION", args)  # minutes
        temp = self._get_gcode_arg_int("TEMP", args, default=45)  # Temperature °C (default: PLA)
        fan_speed = self._get_gcode_arg_int("FAN_SPEED", args, default=0)  # Fan speed

        params = {
            "id": unit,
            "duration": duration,
            "temp": temp,
            "fan_speed": fan_speed
        }

        try:
            await self.ace_controller.printer.send_request(
                "filament_hub/start_drying",
                params
            )
            logging.info(f"Started dryer on unit {unit} for {duration} minutes")
        except Exception as e:
            logging.error(f"Dryer start failed: {e}")

    async def _on_gcode_dryer_stop(self, args: dict[str, str | None], delegate):
        """Stop dryer: MMU_DRYER_STOP UNIT=0"""
        unit = self._get_gcode_arg_int("UNIT", args, default=0)

        try:
            await self.ace_controller.printer.send_request(
                "filament_hub/stop_drying",
                {"id": unit}
            )
            logging.info(f"Stopped dryer on unit {unit}")
        except Exception as e:
            logging.error(f"Dryer stop failed: {e}")

    async def _on_gcode_dryer_fan_speed(self, args: dict[str, str | None], delegate):
        """Adjust fan: MMU_DRYER_FAN_SPEED UNIT=0 SPEED=4000"""
        unit = self._get_gcode_arg_int("UNIT", args, default=0)
        speed = self._get_gcode_arg_int("SPEED", args)

        try:
            await self.ace_controller.printer.send_request(
                "filament_hub/set_fan_speed",
                {"id": unit, "fan_speed": speed}
            )
            logging.info(f"Set dryer fan speed to {speed} RPM on unit {unit}")
        except Exception as e:
            logging.error(f"Fan speed change failed: {e}")

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
            paint_index = 0  # paint_index counts the order of colors in the object (starts at 0)

            for tool_index, tool in enumerate(self.ace.tools):
                gate_index = self.ace.ttg_map[tool_index]

                # Multi-unit support: find correct unit and gate
                current_gate_index = gate_index
                unit = None
                gate = None

                for u in self.ace.units:
                    num_gates = len(u.gates)
                    if current_gate_index < num_gates:
                        unit = u
                        gate = u.gates[current_gate_index]
                        break
                    current_gate_index -= num_gates

                if not gate:
                    logging.error(f"Invalid gate_index {gate_index} for tool {tool_index}")
                    continue

                # Only add mapping for gates with filament (status >= 1)
                # Empty gates (status == 0) should not be in the mapping to prevent GoKlipper errors
                if gate.status < 1:
                    logging.info(f"Skipping empty gate {gate_index} (tool {tool_index}) in ams_box_mapping")
                    continue

                # Add primary gate mapping
                # paint_index = order of colors in object (0, 1, 2, ...)
                # ams_index = physical gate number (can be any gate)
                mapping.append({
                    "paint_index": paint_index,
                    "ams_index": gate_index,
                    "paint_color": gate.color,
                    "ams_color": gate.color,
                    "material_type": gate.material
                })

                logging.info(f"Mapping: paint_index {paint_index} (T{tool_index}) → ams_index {gate_index} ({gate.filament_name})")

                # Add backup gates from endless spool groups
                if gate_index < len(self.ace.endless_spool_groups):
                    endless_spool_group = self.ace.endless_spool_groups[gate_index]

                    # Find all other gates in the same endless spool group
                    for backup_gate_index, backup_group in enumerate(self.ace.endless_spool_groups):
                        if backup_gate_index != gate_index and backup_group == endless_spool_group and endless_spool_group > 0:
                            # Find backup gate info
                            backup_current_gate_index = backup_gate_index
                            backup_gate = None
                            for u in self.ace.units:
                                num_gates = len(u.gates)
                                if backup_current_gate_index < num_gates:
                                    backup_gate = u.gates[backup_current_gate_index]
                                    break
                                backup_current_gate_index -= num_gates

                            if backup_gate:
                                # Add backup gate with same paint_index (same color) but different ams_index (gate)
                                mapping.append({
                                    "paint_index": paint_index,
                                    "ams_index": backup_gate_index,
                                    "paint_color": backup_gate.color,
                                    "ams_color": backup_gate.color,
                                    "material_type": backup_gate.material
                                })
                                logging.info(f"Endless Spool: paint_index {paint_index} (T{tool_index}) can use Gate {backup_gate_index} as backup for Gate {gate_index} (group {endless_spool_group})")

                # Increment paint_index for the next color in the object
                paint_index += 1

            print_data["ams_settings"] = {
                "use_ams": True,
                "ams_box_mapping": mapping
            }

            logging.debug(f"mmu_ace: patch_print_data: {json.dumps(print_data)}")

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

    async def _handle_start_drying(self, web_request):
        """Start ACE dryer (Anycubic N033 protocol)"""
        hub_id = web_request.get_int("id")  # 0 or 1
        fan_speed = web_request.get_int("fan_speed", 0)  # Fan speed, default 0
        duration = web_request.get_int("duration")  # minutes
        temp = web_request.get_int("temp")  # Temperature in °C (required)

        params = {
            "id": hub_id,
            "duration": duration,
            "temp": temp,
            "fan_speed": fan_speed
        }

        try:
            result = await self.ace_controller.printer.send_request(
                "filament_hub/start_drying",
                params
            )
            return {"result": "ok", "data": result}
        except Exception as e:
            logging.error(f"Failed to start dryer: {e}")
            raise self.server.error(f"Dryer start failed: {e}")

    async def _handle_stop_drying(self, web_request):
        """Stop ACE dryer"""
        hub_id = web_request.get_int("id")

        try:
            result = await self.ace_controller.printer.send_request(
                "filament_hub/stop_drying",
                {"id": hub_id}
            )
            return {"result": "ok"}
        except Exception as e:
            logging.error(f"Failed to stop dryer: {e}")
            raise self.server.error(f"Dryer stop failed: {e}")

    async def _handle_set_fan_speed(self, web_request):
        """Adjust ACE dryer fan speed during operation"""
        hub_id = web_request.get_int("id")
        fan_speed = web_request.get_int("fan_speed")  # RPM

        try:
            result = await self.ace_controller.printer.send_request(
                "filament_hub/set_fan_speed",
                {"id": hub_id, "fan_speed": fan_speed}
            )
            return {"result": "ok"}
        except Exception as e:
            logging.error(f"Failed to set fan speed: {e}")
            raise self.server.error(f"Fan speed change failed: {e}")

    async def _handle_mmu_request(self, web_request):
        return {
            "status": self.get_status()
        }

    async def _handle_get_spool_id(self):
        """Return active spool ID (currently selected gate's spool_id)"""
        if self.ace.gate >= 0 and self.ace.gate < len(self.ace.units[0].gates):
            return {"spool_id": self.ace.units[0].gates[self.ace.gate].spool_id}
        return {"spool_id": None}

    async def _handle_spoolman_proxy_ws(self, request_method: str, path: str, query: str = "", body=None, use_v2_response: bool = False):
        """Handle WebSocket spoolman proxy requests from Fluidd"""

        # Handle GET /v1/spools - return all ACE spools
        if request_method == "GET" and path == "/v1/spools":
            spools = []

            for unit in self.ace.units:
                for gate in unit.gates:
                    # Only include gates with RFID data
                    if gate.spool_id > 0 and gate.sku:
                        sku_info = parse_anycubic_sku(gate.sku)
                        vendor_name = sku_info.get("vendor", "Unknown")

                        # Build filament name
                        parts = [vendor_name, sku_info.get("series", ""), gate.material]
                        if sku_info.get("color_name"):
                            parts.append(sku_info.get("color_name"))
                        filament_name = " ".join([p for p in parts if p])

                        # Convert color from RGBA to hex
                        color_hex = None
                        if gate.color and len(gate.color) >= 3:
                            color_hex = '{:02X}{:02X}{:02X}'.format(gate.color[0], gate.color[1], gate.color[2])

                        spool = {
                            "id": gate.spool_id,
                            "registered": "2024-01-01T00:00:00Z",
                            "filament": {
                                "id": gate.spool_id,
                                "registered": "2024-01-01T00:00:00Z",
                                "density": 1.24,
                                "diameter": 1.75,
                                "name": filament_name or gate.material,
                                "vendor": {
                                    "id": 1,
                                    "registered": "2024-01-01T00:00:00Z",
                                    "name": vendor_name
                                } if vendor_name else None,
                                "material": gate.material or "Unknown",
                                "color_hex": color_hex,
                                "settings_extruder_temp": gate.temperature if gate.temperature > 0 else None
                            },
                            "archived": False
                        }
                        spools.append(spool)

            if use_v2_response:
                return {"response": spools, "error": None}
            return spools

        # Handle GET /v1/info - return spoolman info
        if request_method == "GET" and path == "/v1/info":
            info = {
                "version": "0.20.0",
                "debug_mode": False,
                "automatic_backups": False,
                "data_dir": "/data"
            }
            if use_v2_response:
                return {"response": info, "error": None}
            return info

        # For other paths, return empty response
        if use_v2_response:
            return {"response": None, "error": None}
        return None

    async def _handle_spoolman_proxy(self, web_request):
        """Emulate Spoolman proxy endpoint for Fluidd

        Fluidd calls /server/spoolman/proxy with path=/v1/spools to get all spools.
        We intercept this and return ACE RFID data in Spoolman format.
        """
        try:
            path = web_request.get_str("path")
        except:
            # If path not provided, return empty response
            return {"response": None, "error": None}

        # Handle GET /v1/spools - return all ACE spools
        if path == "/v1/spools":
            spools = []

            for unit in self.ace.units:
                for gate in unit.gates:
                    # Only include gates with RFID data
                    if gate.spool_id > 0 and gate.sku:
                        sku_info = parse_anycubic_sku(gate.sku)
                        vendor_name = sku_info.get("vendor", "Unknown")

                        # Build filament name
                        parts = [vendor_name, sku_info.get("series", ""), gate.material]
                        if sku_info.get("color_name"):
                            parts.append(sku_info.get("color_name"))
                        filament_name = " ".join([p for p in parts if p])

                        # Convert color from RGBA to hex
                        color_hex = None
                        if gate.color and len(gate.color) >= 3:
                            color_hex = '{:02X}{:02X}{:02X}'.format(gate.color[0], gate.color[1], gate.color[2])

                        spool = {
                            "id": gate.spool_id,
                            "registered": "2024-01-01T00:00:00Z",
                            "filament": {
                                "id": gate.spool_id,
                                "registered": "2024-01-01T00:00:00Z",
                                "density": 1.24,
                                "diameter": 1.75,
                                "name": filament_name or gate.material,
                                "vendor": {
                                    "id": 1,
                                    "registered": "2024-01-01T00:00:00Z",
                                    "name": vendor_name
                                } if vendor_name else None,
                                "material": gate.material or "Unknown",
                                "color_hex": color_hex,
                                "settings_extruder_temp": gate.temperature if gate.temperature > 0 else None
                            },
                            "archived": False
                        }
                        spools.append(spool)

            return {"response": spools, "error": None}

        # For other paths, return empty response
        return {"response": None, "error": None}

    async def _handle_spoolman_spool(self, web_request):
        """Emulate Spoolman API for Fluidd compatibility

        Fluidd reads vendor from Spoolman API, not from MMU status.
        This translates ACE RFID data into Spoolman format.
        """
        # Extract spool_id from URL path: /server/spoolman/spool_id/107
        try:
            request_path = web_request.get_endpoint()
            spool_id = int(request_path.split('/')[-1])
        except (ValueError, IndexError, AttributeError):
            raise self.server.error("Invalid spool_id in URL path")

        # Find gate with matching spool_id across all units
        gate = None
        for unit in self.ace.units:
            for g in unit.gates:
                if g.spool_id == spool_id:
                    gate = g
                    break
            if gate:
                break

        if not gate:
            raise self.server.error(f"Spool ID {spool_id} not found in ACE units")

        # Parse SKU to get vendor info
        sku_info = parse_anycubic_sku(gate.sku) if gate.sku else {}
        vendor_name = sku_info.get("vendor", "Unknown")

        # Build filament name
        parts = [vendor_name, sku_info.get("series", ""), gate.material]
        if sku_info.get("color_name"):
            parts.append(sku_info.get("color_name"))
        filament_name = " ".join([p for p in parts if p])

        # Convert color from RGBA to hex (remove alpha for Spoolman)
        color_hex = None
        if gate.color and len(gate.color) >= 3:
            color_hex = '{:02X}{:02X}{:02X}'.format(gate.color[0], gate.color[1], gate.color[2])

        # Return Spoolman-compatible structure
        return {
            "id": spool_id,
            "registered": "2024-01-01T00:00:00Z",
            "filament": {
                "id": spool_id,
                "registered": "2024-01-01T00:00:00Z",
                "density": 1.24,  # Standard PLA density
                "diameter": 1.75,
                "name": filament_name or gate.material,
                "vendor": {
                    "id": 1,
                    "registered": "2024-01-01T00:00:00Z",
                    "name": vendor_name
                } if vendor_name else None,
                "material": gate.material or "Unknown",
                "color_hex": color_hex,
                "settings_extruder_temp": gate.temperature if gate.temperature > 0 else None
            },
            "archived": False
        }

# Add support for anycubic slicer
    def setup_anycubic_slicer(self):
        logging.debug("setup_anycubic_slicer")
        from .file_manager import file_manager
        
        # Seperate the metadata script out to fix a `ImportError: attempted relative import with no known parent package` error
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_manager.METADATA_SCRIPT = os.path.join(current_dir, "mmu_ace_metadata.py")
        
        logging.debug(f"setup_anycubic_slicer METADATA_SCRIPT: {file_manager.METADATA_SCRIPT}")


def load_component(config):
    return MmuAcePatcher(config)
