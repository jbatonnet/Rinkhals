# GoKlipper ACE G-Code Commands

This document lists all ACE-related G-code commands found in the GoKlipper binary through reverse engineering and systematic testing.

**Source**: gklib reverse engineering (gklib_analysis_report.txt)
**Testing Date**: 2025-11-26
**GoKlipper Firmware**: V1.3.863
**Hardware**: Anycubic Color Engine Pro (4 slots)

---

## Table of Contents

1. [Filament Operations](#filament-operations)
2. [Status & Info Commands](#status--info-commands)
3. [Cutter/Knife Operations](#cutterknife-operations)
4. [Calibration Commands](#calibration-commands)
5. [Pipe Operations](#pipe-operations)
6. [Error Handling](#error-handling)
7. [Implementation Notes](#implementation-notes)
8. [Testing Results Summary](#testing-results-summary)

---

## Filament Operations

### FEED_FILAMENT ✅
**Function**: Load filament from ACE gate to nozzle + extrude

**Usage**:
```gcode
FEED_FILAMENT INDEX=<0-3> LENGTH=<mm> SPEED=<mm/s>
```

**Parameters**:
- `INDEX`: Local gate index (0-3, not global gate 0-7)
- `LENGTH`: Extrusion amount after loading (mm)
- `SPEED`: Feed speed in mm/s

**Requirements**:
- Extruder must be heated above `min_extrude_temp` (170°C)
- Use `SET_CURRENT_FILAMENT INDEX=X` after system restart
- Previous filament must be unloaded first (no automatic unload!)

**Behavior**:
1. Loads filament from ACE gate through entire Bowden tube (~300-400mm)
2. Feeds through extruder to nozzle
3. Extrudes LENGTH mm at purge position
4. **LENGTH Effect**:
   - `LENGTH=0-50`: Minimal standard extrusion (little visible difference)
   - `LENGTH=100+`: Proportionally more extrusion
5. Command is **synchronous/blocking** - returns "ok" when complete

**Example**:
```gcode
SET_CURRENT_FILAMENT INDEX=1
FEED_FILAMENT INDEX=1 LENGTH=100 SPEED=25
```

**Rinkhals Mapping**:
- Wrapped by `MMU_LOAD GATE=<0-7>` which converts global gate to local INDEX

**Critical Notes**:
- ⚠️ **Does NOT automatically unload previous filament!**
- Attempting FEED without UNLOAD first causes system blockage requiring restart
- Always use full sequence: `UNWIND → SET_CURRENT → FEED`

---

### UNWIND_FILAMENT ✅
**Function**: Unload filament from extruder to park position

**Usage**:
```gcode
UNWIND_FILAMENT INDEX=<0-3> LENGTH=<mm> SPEED=<mm/s>
```

**Parameters**:
- `INDEX`: Local gate index (0-3, not global gate 0-7)
- `LENGTH`: **IGNORED** - always unloads to park position
- `SPEED`: Unwind speed in mm/s

**Requirements**:
- Extruder must be heated above `min_extrude_temp` (170°C)
- Filament must be loaded in extruder

**Behavior**:
1. Retracts filament from nozzle
2. Pulls back through extruder
3. Parks ~5cm before extruder entrance
4. "Click" sound at start (possible automatic cut?)
5. LENGTH parameter has **no effect** - always parks at same position
6. Command is **synchronous/blocking**

**Example**:
```gcode
UNWIND_FILAMENT INDEX=2 LENGTH=100 SPEED=20
```

**Rinkhals Mapping**:
- Wrapped by `MMU_UNLOAD GATE=<0-7>` which converts global gate to local INDEX
- Wrapped by `MMU_EJECT GATE=<0-7>` with default LENGTH=500 (still ignored)

**Notes**:
- After unwind, filament is in "park position" - not fully ejected from gate
- Cannot unwind further from park position (additional UNWIND commands are ignored)
- From park position, only FEED_FILAMENT works (not manual G1 extrusion)

---

### UNWIND_ALL_FILAMENT ✅
**Function**: Unload all currently loaded filaments

**Usage**:
```gcode
UNWIND_ALL_FILAMENT
```

**Parameters**: None

**Requirements**:
- Extruder must be heated above `min_extrude_temp` if any filament is in extruder
- Without heating: Error 10409 (abnormal state)

**Behavior**:
- Unloads ALL filaments that are currently loaded (not just active one)
- Useful after system errors when multiple filaments are stuck
- Perfect for "reset everything" scenarios

**Example**:
```gcode
M104 S200  # Heat first
UNWIND_ALL_FILAMENT
```

**Notes**:
- In test: Successfully unloaded both white and black filament after blockage error
- Does NOT unload from park position - only from extruder

---

### EXTRUDE_FILAMENT ✅
**Function**: Extrude loaded filament at purge position

**Usage**:
```gcode
EXTRUDE_FILAMENT [LENGTH=<mm>] [SPEED=<mm/s>]
```

**Parameters**:
- `LENGTH`: Amount to extrude (optional, defaults to ~20mm)
- `SPEED`: Extrusion speed in mm/s (default: 5)

**Requirements**:
- Extruder must be heated above `min_extrude_temp`
- Filament must already be loaded (use FEED_FILAMENT first)

**Behavior**:
1. Moves to purge position (sweep_position)
2. Extrudes specified LENGTH
3. For large amounts, extrudes in multiple "piles":
   - `LENGTH=0`: No extrusion
   - `LENGTH=20`: ~20mm single extrusion
   - `LENGTH=100`: ~100mm single extrusion
   - `LENGTH=500`: 3 separate extrusion cycles (~167mm each)
4. Command is **synchronous/blocking**

**Example**:
```gcode
FEED_FILAMENT INDEX=1 LENGTH=20 SPEED=25
EXTRUDE_FILAMENT LENGTH=50 SPEED=5  # Purge/prime
```

**Notes**:
- Unlike FEED_FILAMENT, LENGTH=0 truly does nothing (no minimum extrusion)
- Large LENGTH values split into multiple piles (system automatically manages)
- Use for purging, priming, or manual filament testing

---

### REFILL_FILAMENT ⚠️
**Function**: Refill filament during Endless Spool operation

**Usage**:
```gcode
REFILL_FILAMENT INDEX=<0-3>
```

**Parameters**:
- `INDEX`: Gate index to refill from (0-3)

**Requirements**:
- Extruder must be heated
- Axes must be homed (Error 10011600: "Must home axis first")
- **Active print with filament runout condition**

**Behavior**:
- Moves to dump position
- Attempts to refill from specified gate
- Without active print:
  - Error 10011720 "Filament is runout"
  - Takes very long time to execute
  - Sets printer to "Pause" state in Mainsail/Fluidd

**Example**:
```gcode
# Only works during print when filament runs out
# System automatically calls during Endless Spool
REFILL_FILAMENT INDEX=2
```

**Notes**:
- ⚠️ **Only functional during active print with runout condition**
- Part of Endless Spool/backup roll feature
- Not for manual filament loading - use FEED_FILAMENT instead

---

### SET_CURRENT_FILAMENT ✅
**Function**: Set internal status of currently active filament

**Usage**:
```gcode
SET_CURRENT_FILAMENT INDEX=<0-3>
```

**Parameters**:
- `INDEX`: Gate index to mark as active (0-3)

**Requirements**: None

**Behavior**:
- Updates internal state only
- **Does NOT load or move any filament**
- **Does NOT enable direct G1 extrusion** (still requires FEED_FILAMENT)
- Prevents "unknown filament in extruder" error after restart

**Example**:
```gcode
# After system restart, before FEED/UNWIND:
SET_CURRENT_FILAMENT INDEX=2
FEED_FILAMENT INDEX=2 LENGTH=20 SPEED=25
```

**Notes**:
- Required after printer restart before FEED/UNWIND commands
- Does not physically change loaded filament
- Cannot switch filaments with this alone - need full UNWIND→SET_CURRENT→FEED sequence

---

## Status & Info Commands

### ACE_INFO ✅
**Function**: Get ACE hardware information

**Usage**:
```gcode
ACE_INFO
```

**Parameters**: None

**Requirements**: None

**Output** (JSON in Fluidd console):
```json
{
  "id": 0,
  "slots": 4,
  "SN": "",
  "date": "",
  "model": "Anycubic Color Engine Pro",
  "firmware": "V1.3.863",
  "structure_version": "0"
}
```

**Example**:
```gcode
ACE_INFO
```

**Notes**:
- Useful for diagnostics and version checking
- Output appears in Fluidd/Mainsail console

---

### ACE_STATUS ✅
**Function**: Get detailed ACE status

**Usage**:
```gcode
ACE_STATUS
```

**Parameters**: None

**Requirements**: None

**Output** (JSON in Fluidd console):
```json
{
  "auto_refill": 0,
  "current_filament": "0-1",
  "cutter_state": 0,
  "ext_spool": 0,
  "ext_spool_status": "ready",
  "filament_hubs": [{
    "id": 0,
    "status": "ready",
    "dryer_status": {
      "status": "stop",
      "target_temp": 0,
      "duration": 0,
      "remain_time": 0
    },
    "temp": 28,
    "slots": [
      {
        "index": 0,
        "status": "empty",
        "sku": "",
        "type": "PLA",
        "color": [0,0,0],
        "source": 3,
        "rfid": 1
      },
      {
        "index": 1,
        "status": "ready",
        "sku": "AHPLBW-107",
        "type": "PLA",
        "color": [239,240,241],
        "rfid": 2,
        "source": 1
      }
      ...
    ]
  }]
}
```

**Example**:
```gcode
ACE_STATUS
```

**Notes**:
- Very detailed status including:
  - Current active filament
  - Cutter state
  - Dryer status and temperature
  - All gate states (empty/ready)
  - RFID information
  - SKU codes
  - Filament colors
- Perfect for diagnostics and automation

---

### TEST_HUB ✅
**Function**: Test ACE hub communication and reset system

**Usage**:
```gcode
TEST_HUB
```

**Parameters**: None

**Requirements**: None

**Behavior**:
- Tests communication with ACE hardware
- Resets system to safe state:
  - Returns to home position
  - Turns off extruder heater
  - Clears any stuck states

**Example**:
```gcode
TEST_HUB
```

**Notes**:
- ⚠️ **Turns off heater!** - reheat before further operations
- Useful for recovery from error states
- System goes to "dump" position after test

---

## Cutter/Knife Operations

### CUT_FILAMENT ✅
**Function**: Prepare cutter/move to dump position

**Usage**:
```gcode
CUT_FILAMENT
```

**Parameters**: None

**Requirements**: None

**Behavior**:
- Moves to dump/purge position
- **Does NOT audibly cut filament alone**
- Part of cut sequence with UNWIND

**Example**:
```gcode
# Recommended sequence:
FEED_FILAMENT INDEX=1 LENGTH=20 SPEED=25
CUT_FILAMENT
UNWIND_FILAMENT INDEX=1 LENGTH=100 SPEED=20  # Runs cleanly after CUT
```

**Notes**:
- CUT_FILAMENT + UNWIND_FILAMENT sequence runs smoothly
- UNWIND alone also works (may have automatic cutting)
- "Click" sound during UNWIND suggests integrated cutting

---

### CUT_FILAMENT_TEST ✅
**Function**: Test cutter mechanism movement

**Usage**:
```gcode
CUT_FILAMENT_TEST
```

**Parameters**: None

**Requirements**: None

**Behavior**:
- Movement test sequence:
  1. Move to bed center
  2. Lower to bed (tap)
  3. Return to home
  4. Move to center again
- Tests cutter mechanics, not actual cutting

**Example**:
```gcode
CUT_FILAMENT_TEST
```

**Notes**:
- Diagnostic/calibration tool
- Does not cut filament
- Tests mechanical movement only

---

### UNWIND_CUT_FILAMENT ⚠️
**Function**: Combined unwind and cut operation

**Usage**:
```gcode
UNWIND_CUT_FILAMENT INDEX=<0-3> LENGTH=<mm> SPEED=<mm/s>
```

**Parameters**:
- `INDEX`: Local gate index (0-3)
- `LENGTH`: Unwind length (may be ignored like UNWIND_FILAMENT)
- `SPEED`: Unwind speed in mm/s

**Requirements**:
- Extruder heated
- Filament loaded

**Behavior**:
- In testing: **Did nothing** - filament remained loaded
- Moves to dump position
- Purpose unclear from testing

**Example**:
```gcode
UNWIND_CUT_FILAMENT INDEX=2 LENGTH=100 SPEED=20
```

**Notes**:
- ⚠️ **Not functional in tests**
- Prefer CUT_FILAMENT + UNWIND_FILAMENT sequence
- May require specific conditions not met in testing

---

### SET_KNIFE_POSITION ❓
**Function**: Set cutter knife position

**Status**: Not tested - calibration command

**Usage**: Unknown

---

## Calibration Commands

### CALI_KNIFE_POSITION ❓
**Function**: Calibrate knife/cutter position

**Status**: Not tested - advanced calibration

---

### CALI_KNIFE_SENSOR_TEST ❓
**Function**: Test knife sensor calibration

**Status**: Not tested - advanced calibration

---

### CALI_KNIFE_TRI_MOVE_DIS ❓
**Function**: Calibrate knife trigger move distance

**Status**: Not tested - advanced calibration

---

### FILAMENT_TRACKER_TEST ✅
**Function**: Test filament tracking sensors

**Usage**:
```gcode
FILAMENT_TRACKER_TEST
```

**Parameters**: None

**Requirements**: None

**Output** (console):
```
has_filament_count=0, no_filament_count=2
```

**Behavior**:
- ACE unit performs sensor test
- Reports how many gates have/lack filament
- Diagnostic tool for RFID/sensor issues

**Example**:
```gcode
FILAMENT_TRACKER_TEST
# Output: has_filament_count=0, no_filament_count=2
```

**Notes**:
- Useful for diagnosing sensor problems
- Verifies RFID detection working
- Output appears in console

---

## Pipe Operations

### CLEAN_PIPE ❌
**Function**: Clean filament path/pipe

**Usage**:
```gcode
CLEAN_PIPE
```

**Status**: **GoKlipper Bug** - Cannot execute

**Error**:
```
interface conversion: interface {} is func() error, not func(interface {}) error
```

**Notes**:
- ❌ **Not functional** - internal GoKlipper error
- Command exists but has implementation bug
- Cannot be used until GoKlipper firmware update

---

## Error Handling

### RUNOUT_PAUSE ⚠️
**Function**: Handle filament runout pause

**Usage**:
```gcode
RUNOUT_PAUSE
```

**Parameters**: None

**Requirements**:
- Active print in progress
- Filament runout condition detected

**Behavior**:
- Part of runout detection system
- In testing without active print: **Does nothing**

**Example**:
```gcode
# Automatically called by system during print
RUNOUT_PAUSE
```

**Notes**:
- ⚠️ **Only functional during active print**
- Part of Endless Spool feature
- Not for manual use

---

## Implementation Notes

### Gate Indexing

**Global Gate** (Rinkhals/Happy Hare): 0-7 (across all ACE units)
- Gate 0-3: ACE Unit 0
- Gate 4-7: ACE Unit 1

**Local INDEX** (GoKlipper Commands): 0-3 (per ACE unit)
- Commands like `FEED_FILAMENT INDEX=1` always refer to local gate 1 of current unit

**Conversion Formula**:
```python
unit = global_gate // 4       # Which ACE unit (0 or 1)
local_index = global_gate % 4  # Local gate index (0-3)
```

---

### Command Execution Model

**Synchronous/Blocking**:
- All commands are **synchronous** - return "ok" only when complete
- No need to poll for completion
- Can take several seconds for FEED/UNWIND operations

Example:
```python
# Python example
response = send_gcode("FEED_FILAMENT INDEX=1 LENGTH=100 SPEED=25")
# Response arrives AFTER complete load sequence (5-10 seconds)
print(response)  # "ok"
```

---

### Required Filament Change Sequence

**Correct sequence for changing filament**:
```gcode
# 1. Unload old filament
UNWIND_FILAMENT INDEX=<old_gate> LENGTH=100 SPEED=20

# 2. Update internal state
SET_CURRENT_FILAMENT INDEX=<new_gate>

# 3. Load new filament
FEED_FILAMENT INDEX=<new_gate> LENGTH=100 SPEED=25
```

**Critical**: Skipping UNWIND causes system blockage requiring restart!

---

### Temperature Requirements

**Commands requiring heated extruder** (min_extrude_temp = 170°C):
- FEED_FILAMENT
- UNWIND_FILAMENT
- EXTRUDE_FILAMENT
- UNWIND_ALL_FILAMENT (if filament in extruder)
- REFILL_FILAMENT

**Error if not heated**:
```
Extruder must heat up first
```

**Heating command**:
```gcode
M104 S200  # Set target 200°C
# Wait for temperature...
```

---

### State After Restart

After printer restart/reboot:
1. System loses track of loaded filament
2. FEED/UNWIND commands fail with: `unknown filament in extruder`
3. **Solution**: Use `SET_CURRENT_FILAMENT INDEX=X` before FEED/UNWIND

Example:
```gcode
# After restart:
M104 S200
SET_CURRENT_FILAMENT INDEX=2  # Tell system black is loaded
UNWIND_FILAMENT INDEX=2 LENGTH=100 SPEED=20
```

---

### Home Positions

Three distinct positions identified:

1. **G28 Home**: Bed center (standard Klipper homing)
2. **Print Start Home**: Where prints begin
3. **Dump/Purge Position**: Where EXTRUDE_FILAMENT purges (sweep_position)

Commands like CUT_FILAMENT, EXTRUDE_FILAMENT, TEST_HUB move to dump position.

---

### Safety Considerations

1. **Temperature Checks**: Many commands require heated extruder
2. **Cold Extrude Prevention**: GoKlipper enforces `min_extrude_temp` checks
3. **No Direct USB Access**: All commands go through GoKlipper to avoid conflicts
4. **State Validation**: Commands may fail if printer/ACE in wrong state
5. **Blockage Prevention**: Always UNWIND before FEED to prevent filament collision

---

## Testing Results Summary

### ✅ Fully Tested & Working

| Command | Function | Key Finding |
|---------|----------|-------------|
| FEED_FILAMENT | Load + extrude | LENGTH only affects final extrusion, not load distance |
| UNWIND_FILAMENT | Unload to park | LENGTH parameter ignored |
| EXTRUDE_FILAMENT | Purge at dump | LENGTH=0 does nothing, large values split into piles |
| SET_CURRENT_FILAMENT | Update status | No physical movement, required after restart |
| UNWIND_ALL_FILAMENT | Emergency unload | Unloads ALL loaded filaments |
| ACE_INFO | Hardware info | Returns JSON with model, firmware, slots |
| ACE_STATUS | Detailed status | Returns JSON with gates, dryer, RFID data |
| TEST_HUB | System test/reset | Homes and turns off heater |
| CUT_FILAMENT | Cut preparation | Works in sequence with UNWIND |
| CUT_FILAMENT_TEST | Cutter movement test | Movement test only, no cutting |
| FILAMENT_TRACKER_TEST | Sensor test | Returns filament detection counts |

### ⚠️ Requires Specific Conditions

| Command | Status | Condition Required |
|---------|--------|-------------------|
| REFILL_FILAMENT | Tested | Active print with runout |
| RUNOUT_PAUSE | Tested | Active print |

### ❌ Not Functional

| Command | Issue |
|---------|-------|
| CLEAN_PIPE | GoKlipper bug - interface conversion error |
| UNWIND_CUT_FILAMENT | Did nothing in tests |

### ❓ Not Tested

| Command | Reason |
|---------|--------|
| SET_KNIFE_POSITION | Calibration - avoid unless necessary |
| CALI_KNIFE_* | Calibration - could affect hardware |

---

## Config Values from printer.cfg

Configuration parameters that affect ACE behavior:

```ini
[filament_hub]
sweep_position: 271.5          # Purge position X coordinate
sweep_after_move_e: 30.0       # Amount to purge in mm
flush_volume_min: 107          # Minimum flush volume
flush_volume_max: 800          # Maximum flush volume
flush_multiplier: 1.0          # Purge multiplier (0.0 to disable)
default_feed_speed: 25         # Default feed speed mm/s
default_unwind_speed: 15       # Default unwind speed mm/s
```

---

## Testing Status Legend

- ✅ **Tested & Working**: Command tested successfully with known behavior
- ⚠️ **Requires Heating**: Command requires heated extruder
- ⚠️ **Context Required**: Only works in specific conditions (print, runout, etc.)
- ❌ **Not Functional**: Command has bugs or doesn't work
- ❓ **Not Tested**: Command found but not tested (calibration, risk)
- 🔧 **Calibration**: Calibration/setup command (use with caution)

---

## Related Documentation

- **ACEResearch Protocol**: https://github.com/printers-for-people/ACEResearch/blob/main/PROTOCOL.md
- **N033 Protocol**: `/home/robertpeerenboom/rinkhals/Kobra3/klipper-go/docs/N033料盒通信协议.md`
- **Reverse Engineering Report**: `/tmp/rinkhals-acm-fix/gklib_analysis_report.txt`
- **Rinkhals MMU Integration**: `/home/robertpeerenboom/rinkhals/rinkhals-repo/files/4-apps/home/rinkhals/apps/40-moonraker/mmu_ace.py`

---

## Contributing

If you test any undocumented commands or discover new behavior, please update this file with:
- Confirmed parameters
- Expected behavior
- Requirements/prerequisites
- Example usage
- Any error conditions encountered
- Testing conditions (firmware version, hardware setup)

---

**Last Updated**: 2025-11-26
**GoKlipper Firmware**: V1.3.863
**Hardware**: Anycubic Color Engine Pro (4 slots)
**Testing**: Systematic testing completed on Kobra 3 with ACE unit
