# pylint: disable=undefined-variable
"""
This modules exposes the integer constants defined in ``linux/input.h`` and
``linux/input-event-codes.h``.

Exposed constants::

    KEY, ABS, REL, SW, MSC, LED, BTN, REP, SND, ID, EV,
    BUS, SYN, FF, FF_STATUS, INPUT_PROP

This module also provides reverse and forward mappings of the names and values
of the above mentioned constants::

    >>> evdev.ecodes.KEY_A
    30

    >>> evdev.ecodes.ecodes['KEY_A']
    30

    >>> evdev.ecodes.KEY[30]
    'KEY_A'

    >>> evdev.ecodes.REL[0]
    'REL_X'

    >>> evdev.ecodes.EV[evdev.ecodes.EV_KEY]
    'EV_KEY'

    >>> evdev.ecodes.bytype[evdev.ecodes.EV_REL][0]
    'REL_X'

Keep in mind that values in reverse mappings may point to one or more event
codes. For example::

    >>> evdev.ecodes.FF[80]
    ('FF_EFFECT_MIN', 'FF_RUMBLE')

    >>> evdev.ecodes.FF[81]
    'FF_PERIODIC'
"""

from inspect import getmembers

from . import _ecodes

#: Mapping of names to values.
ecodes = {}

prefixes = "KEY ABS REL SW MSC LED BTN REP SND ID EV BUS SYN FF_STATUS FF INPUT_PROP UI_FF".split()
prev_prefix = ""
g = globals()

# eg. code: 'REL_Z', val: 2
for code, val in getmembers(_ecodes):
    for prefix in prefixes:  # eg. 'REL'
        if code.startswith(prefix):
            ecodes[code] = val
            # FF_STATUS codes should not appear in the FF reverse mapping
            if not code.startswith(prev_prefix):
                d = g.setdefault(prefix, {})
                # codes that share the same value will be added to a list. eg:
                # >>> ecodes.FF_STATUS
                # {0: 'FF_STATUS_STOPPED', 1: ['FF_STATUS_MAX', 'FF_STATUS_PLAYING']}
                if val in d:
                    if isinstance(d[val], list):
                        d[val].append(code)
                    else:
                        d[val] = [d[val], code]
                else:
                    d[val] = code

        prev_prefix = prefix


# Convert lists to tuples.
k, v = None, None
for prefix in prefixes:
    for k, v in g[prefix].items():
        if isinstance(v, list):
            g[prefix][k] = tuple(v)


#: Keys are a combination of all BTN and KEY codes.
keys = {}
keys.update(BTN)
keys.update(KEY)

# make keys safe to use for the default list of uinput device
# capabilities
del keys[_ecodes.KEY_MAX]
del keys[_ecodes.KEY_CNT]

#: Mapping of event types to other value/name mappings.
bytype = {
    _ecodes.EV_KEY: keys,
    _ecodes.EV_ABS: ABS,
    _ecodes.EV_REL: REL,
    _ecodes.EV_SW: SW,
    _ecodes.EV_MSC: MSC,
    _ecodes.EV_LED: LED,
    _ecodes.EV_REP: REP,
    _ecodes.EV_SND: SND,
    _ecodes.EV_SYN: SYN,
    _ecodes.EV_FF: FF,
    _ecodes.EV_FF_STATUS: FF_STATUS,
}

from evdev._ecodes import *

# cheaper than whitelisting in an __all__
del code, val, prefix, getmembers, g, d, k, v, prefixes, prev_prefix
