# --------------------------------------------------------------------------
# Gather everything into a single, convenient namespace.
# --------------------------------------------------------------------------

# The superfluous "import name as name" syntax is here to satisfy mypy's attrs-defined rule.
# Alternatively all exported objects can be listed in __all__.

from . import (
    ecodes as ecodes,
    ff as ff,
)

from .device import (
    AbsInfo as AbsInfo,
    DeviceInfo as DeviceInfo,
    EvdevError as EvdevError,
    InputDevice as InputDevice,
)

from .events import (
    AbsEvent as AbsEvent,
    InputEvent as InputEvent,
    KeyEvent as KeyEvent,
    RelEvent as RelEvent,
    SynEvent as SynEvent,
    event_factory as event_factory,
)

from .uinput import (
    UInput as UInput,
    UInputError as UInputError,
)

from .util import (
    categorize as categorize,
    list_devices as list_devices,
    resolve_ecodes as resolve_ecodes,
    resolve_ecodes_dict as resolve_ecodes_dict,
)
