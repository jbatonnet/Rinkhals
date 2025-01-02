import types
import io as _io


def text_encoding(encoding, stacklevel=2):  # pragma: no cover
    """
    Stubbed version of io.text_encoding as found in Python 3.10
    """
    return encoding


def copy_module(mod, **defaults):
    copy = types.ModuleType(mod.__name__, doc=mod.__doc__)
    vars(copy).update(defaults)
    vars(copy).update(vars(mod))
    return copy


io = copy_module(_io, text_encoding=text_encoding)
