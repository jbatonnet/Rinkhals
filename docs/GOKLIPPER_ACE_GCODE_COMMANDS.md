# GoKlipper ACE G-Code Commands

This document lists all ACE-related G-code commands found in the GoKlipper binary through reverse engineering.

**Source**: gklib reverse engineering (gklib_analysis_report.txt)
**Date**: 2025-11-26

---

## Filament Operations

### FEED_FILAMENT
**Function**: Load/feed filament into ACE gate

**Usage**:
```gcode
FEED_FILAMENT INDEX=<0-3> LENGTH=<mm> SPEED=<mm/s>
```

**Parameters**:
- `INDEX`: Local gate index (0-3, not global gate 0-7)
- `LENGTH`: Amount of filament to feed in mm
- `SPEED`: Feed speed in mm/s

**Requirements**:
- Extruder must be heated above `min_extrude_temp`

**Example**:
```gcode
FEED_FILAMENT INDEX=1 LENGTH=100 SPEED=25
```

**Rinkhals Mapping**:
- Wrapped by `MMU_LOAD GATE=<0-7>` which converts global gate to local INDEX

---

### UNWIND_FILAMENT
**Function**: Unload/unwind filament from ACE gate

**Usage**:
```gcode
UNWIND_FILAMENT INDEX=<0-3> LENGTH=<mm> SPEED=<mm/s>
```

**Parameters**:
- `INDEX`: Local gate index (0-3, not global gate 0-7)
- `LENGTH`: Amount of filament to unwind in mm
- `SPEED`: Unwind speed in mm/s

**Requirements**:
- Extruder must be heated above `min_extrude_temp`

**Example**:
```gcode
UNWIND_FILAMENT INDEX=2 LENGTH=50 SPEED=20
```

**Rinkhals Mapping**:
- Wrapped by `MMU_UNLOAD GATE=<0-7>` which converts global gate to local INDEX
- Wrapped by `MMU_EJECT GATE=<0-7>` with longer default LENGTH (500mm)

---

### UNWIND_ALL_FILAMENT
**Function**: Unload all filament from all gates

**Internal Name**: `Cmd_UNWIND_ALL_FILAMENT`

**Status**: Not tested, parameters unknown

---

### EXTRUDE_FILAMENT
**Function**: Extrude filament (likely through nozzle)

**Internal Name**: `Cmd_EXTRUDE_FILAMENT`

**Status**: Not tested, parameters unknown

**Note**: Probably requires active tool/gate selection first

---

### REFILL_FILAMENT
**Function**: Refill operation for filament change

**Internal Name**: `Cmd_REFILL_FILAMENT`

**Status**: Not tested, parameters unknown

**Note**: Likely used for Endless Spool feature

---

### SET_CURRENT_FILAMENT
**Function**: Set the currently active filament

**Internal Name**: `Cmd_SET_CURRENT_FILAMENT`

**Status**: Not tested, parameters unknown

---

## Status & Info Commands

### ACE_INFO
**Function**: Get ACE hardware information

**Internal Name**: `Cmd_ACE_INFO`

**Status**: Not tested, parameters unknown

**Expected Output**: ACE unit details, version, serial number

---

### ACE_STATUS
**Function**: Get ACE status

**Internal Name**: `Cmd_ACE_STATUS`

**Status**: Not tested, parameters unknown

**Expected Output**: Current gate status, temperatures, dryer status

---

### TEST_HUB
**Function**: Test ACE hub communication

**Internal Name**: `Cmd_TEST_HUB`

**Status**: Not tested, parameters unknown

---

## Cutter/Knife Operations

### CUT_FILAMENT
**Function**: Cut filament at cutter position

**Internal Name**: `Cmd_CUT_FILAMENT`

**Status**: Not tested, parameters unknown

**Note**: ACE has integrated filament cutter

---

### CUT_FILAMENT_TEST
**Function**: Test cutter functionality

**Internal Name**: `Cmd_CUT_FILAMENT_TEST`

**Status**: Not tested, parameters unknown

---

### UNWIND_CUT_FILAMENT
**Function**: Unwind and cut filament

**Internal Name**: `Cmd_UNWIND_CUT_FILAMENT`

**Status**: Not tested, parameters unknown

---

### SET_KNIFE_POSITION
**Function**: Set cutter knife position

**Internal Name**: `Cmd_SET_KNIFE_POSITION`

**Status**: Not tested, parameters unknown

---

## Calibration Commands

### CALI_KNIFE_POSITION
**Function**: Calibrate knife/cutter position

**Internal Name**: `Cmd_CALI_KNIFE_POSITION`

**Status**: Not tested, parameters unknown

---

### CALI_KNIFE_SENSOR_TEST
**Function**: Test knife sensor calibration

**Internal Name**: `Cmd_CALI_KNIFE_SENSOR_TEST`

**Status**: Not tested, parameters unknown

---

### CALI_KNIFE_TRI_MOVE_DIS
**Function**: Calibrate knife trigger move distance

**Internal Name**: `Cmd_CALI_KNIFE_TRI_MOVE_DIS`

**Status**: Not tested, parameters unknown

---

### FILAMENT_TRACKER_TEST
**Function**: Test filament tracking sensor

**Internal Name**: `Cmd_FILAMENT_TRACKER_TEST`

**Status**: Not tested, parameters unknown

---

## Pipe Operations

### CLEAN_PIPE
**Function**: Clean filament path/pipe

**Internal Name**: `Cmd_CLEAN_PIPE`

**Status**: Not tested, parameters unknown

**Note**: Likely performs purge/cleaning routine

---

## Error Handling

### RUNOUT_PAUSE
**Function**: Handle filament runout pause

**Internal Name**: `Cmd_RUNOUT_PAUSE`

**Status**: Not tested, parameters unknown

**Note**: Part of runout detection system

---

## Config Values from printer.cfg

These are configuration parameters that affect ACE behavior (not G-code commands):

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

- ✅ **Tested & Working**: Command tested successfully
- ⚠️ **Requires Heating**: Command requires heated extruder
- ❓ **Not Tested**: Command found but not tested
- 🔧 **Calibration**: Calibration/setup command

## Command Status Summary

| Command | Status | Requirements |
|---------|--------|--------------|
| FEED_FILAMENT | ✅ Tested | ⚠️ Heating required |
| UNWIND_FILAMENT | ✅ Tested | ⚠️ Heating required |
| ACE_INFO | ❓ Not tested | - |
| ACE_STATUS | ❓ Not tested | - |
| CUT_FILAMENT | ❓ Not tested | - |
| CLEAN_PIPE | ❓ Not tested | - |
| EXTRUDE_FILAMENT | ❓ Not tested | ⚠️ Likely needs heating |
| REFILL_FILAMENT | ❓ Not tested | - |
| SET_CURRENT_FILAMENT | ❓ Not tested | - |
| TEST_HUB | ❓ Not tested | - |
| UNWIND_ALL_FILAMENT | ❓ Not tested | - |
| CUT_FILAMENT_TEST | 🔧 Calibration | - |
| SET_KNIFE_POSITION | 🔧 Calibration | - |
| CALI_KNIFE_* | 🔧 Calibration | - |
| FILAMENT_TRACKER_TEST | 🔧 Test/Debug | - |
| RUNOUT_PAUSE | ❓ Not tested | - |

---

## Implementation Notes

### Gate Indexing
- **Global Gate** (Rinkhals/Happy Hare): 0-7 (across all ACE units)
  - Gate 0-3: ACE Unit 0
  - Gate 4-7: ACE Unit 1

- **Local INDEX** (GoKlipper Commands): 0-3 (per ACE unit)
  - Commands like `FEED_FILAMENT INDEX=1` always refer to local gate 1 of current unit

### Conversion Formula
```python
unit = global_gate // 4       # Which ACE unit (0 or 1)
local_index = global_gate % 4  # Local gate index (0-3)
```

### Safety Considerations
1. **Temperature Checks**: Many commands require heated extruder
2. **Cold Extrude Prevention**: GoKlipper enforces `min_extrude_temp` checks
3. **No Direct USB Access**: All commands go through GoKlipper to avoid conflicts
4. **State Validation**: Commands may fail if printer/ACE in wrong state

---

## Related Documentation

- **ACEResearch Protocol**: https://github.com/printers-for-people/ACEResearch/blob/main/PROTOCOL.md
- **N033 Protocol**: `/home/robertpeerenboom/rinkhals/Kobra3/klipper-go/docs/N033料盒通信协议.md`
- **Reverse Engineering Report**: `/tmp/rinkhals-acm-fix/gklib_analysis_report.txt`

---

## Contributing

If you test any of the undocumented commands, please update this file with:
- Confirmed parameters
- Expected behavior
- Requirements/prerequisites
- Example usage
- Any error conditions encountered

---

**Last Updated**: 2025-11-26
**GoKlipper Version**: Extracted from gklib binary via reverse engineering
