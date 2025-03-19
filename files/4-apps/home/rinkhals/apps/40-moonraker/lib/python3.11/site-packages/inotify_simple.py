from sys import version_info, getfilesystemencoding
import os
from enum import Enum, IntEnum
from collections import namedtuple
from struct import unpack_from, calcsize
from select import poll
from time import sleep
from ctypes import CDLL, get_errno, c_int
from ctypes.util import find_library
from errno import EINTR
from termios import FIONREAD
from fcntl import ioctl
from io import FileIO

PY2 = version_info.major < 3
if PY2:
    fsencode = lambda s: s if isinstance(s, str) else s.encode(getfilesystemencoding())
    # In 32-bit Python < 3 the inotify constants don't fit in an IntEnum:
    IntEnum = type('IntEnum', (long, Enum), {})
else:
    from os import fsencode, fsdecode


__version__ = '1.3.5'

__all__ = ['Event', 'INotify', 'flags', 'masks', 'parse_events']

_libc = None


def _libc_call(function, *args):
    """Wrapper which raises errors and retries on EINTR."""
    while True:
        rc = function(*args)
        if rc != -1:
            return rc
        errno = get_errno()
        if errno != EINTR:
            raise OSError(errno, os.strerror(errno))


#: A ``namedtuple`` (wd, mask, cookie, name) for an inotify event. On Python 3 the
#: :attr:`~inotify_simple.Event.name`  field is a ``str`` decoded with
#: ``os.fsdecode()``, on Python 2 it is ``bytes``.
Event = namedtuple('Event', ['wd', 'mask', 'cookie', 'name'])

_EVENT_FMT = 'iIII'
_EVENT_SIZE = calcsize(_EVENT_FMT)


class INotify(FileIO):

    #: The inotify file descriptor returned by ``inotify_init()``. You are
    #: free to use it directly with ``os.read`` if you'd prefer not to call
    #: :func:`~inotify_simple.INotify.read` for some reason. Also available as
    #: :func:`~inotify_simple.INotify.fileno`
    fd = property(FileIO.fileno)

    def __init__(self, inheritable=False, nonblocking=False):
        """File-like object wrapping ``inotify_init1()``. Raises ``OSError`` on failure.
        :func:`~inotify_simple.INotify.close` should be called when no longer needed.
        Can be used as a context manager to ensure it is closed, and can be used
        directly by functions expecting a file-like object, such as ``select``, or with
        functions expecting a file descriptor via
        :func:`~inotify_simple.INotify.fileno`.

        Args:
            inheritable (bool): whether the inotify file descriptor will be inherited by
                child processes. The default,``False``, corresponds to passing the
                ``IN_CLOEXEC`` flag to ``inotify_init1()``. Setting this flag when
                opening filedescriptors is the default behaviour of Python standard
                library functions since PEP 446. On Python < 3.3, the file descriptor
                will be inheritable and this argument has no effect, one must instead
                use fcntl to set FD_CLOEXEC to make it non-inheritable.

            nonblocking (bool): whether to open the inotify file descriptor in
                nonblocking mode, corresponding to passing the ``IN_NONBLOCK`` flag to
                ``inotify_init1()``. This does not affect the normal behaviour of
                :func:`~inotify_simple.INotify.read`, which uses ``poll()`` to control
                blocking behaviour according to the given timeout, but will cause other
                reads of the file descriptor (for example if the application reads data
                manually with ``os.read(fd)``) to raise ``BlockingIOError`` if no data
                is available."""
        try:
            libc_so = find_library('c')
        except RuntimeError: # Python on Synology NASs raises a RuntimeError
            libc_so = None
        global _libc; _libc = _libc or CDLL(libc_so or 'libc.so.6', use_errno=True)
        O_CLOEXEC = getattr(os, 'O_CLOEXEC', 0) # Only defined in Python 3.3+
        flags = (not inheritable) * O_CLOEXEC | bool(nonblocking) * os.O_NONBLOCK 
        FileIO.__init__(self, _libc_call(_libc.inotify_init1, flags), mode='rb')
        self._poller = poll()
        self._poller.register(self.fileno())

    def add_watch(self, path, mask):
        """Wrapper around ``inotify_add_watch()``. Returns the watch
        descriptor or raises an ``OSError`` on failure.

        Args:
            path (str, bytes, or PathLike): The path to watch. Will be encoded with
                ``os.fsencode()`` before being passed to ``inotify_add_watch()``.

            mask (int): The mask of events to watch for. Can be constructed by
                bitwise-ORing :class:`~inotify_simple.flags` together.

        Returns:
            int: watch descriptor"""
        # Explicit conversion of Path to str required on Python < 3.6
        path = str(path) if hasattr(path, 'parts') else path
        return _libc_call(_libc.inotify_add_watch, self.fileno(), fsencode(path), mask)

    def rm_watch(self, wd):
        """Wrapper around ``inotify_rm_watch()``. Raises ``OSError`` on failure.

        Args:
            wd (int): The watch descriptor to remove"""
        _libc_call(_libc.inotify_rm_watch, self.fileno(), wd)

    def read(self, timeout=None, read_delay=None):
        """Read the inotify file descriptor and return the resulting
        :attr:`~inotify_simple.Event` namedtuples (wd, mask, cookie, name).

        Args:
            timeout (int): The time in milliseconds to wait for events if there are
                none. If negative or ``None``, block until there are events. If zero,
                return immediately if there are no events to be read.

            read_delay (int): If there are no events immediately available for reading,
                then this is the time in milliseconds to wait after the first event
                arrives before reading the file descriptor. This allows further events
                to accumulate before reading, which allows the kernel to coalesce like
                events and can decrease the number of events the application needs to
                process. However, this also increases the risk that the event queue will
                overflow due to not being emptied fast enough.

        Returns:
            generator: generator producing :attr:`~inotify_simple.Event` namedtuples

        .. warning::
            If the same inotify file descriptor is being read by multiple threads
            simultaneously, this method may attempt to read the file descriptor when no
            data is available. It may return zero events, or block until more events
            arrive (regardless of the requested timeout), or in the case that the
            :func:`~inotify_simple.INotify` object was instantiated with
            ``nonblocking=True``, raise ``BlockingIOError``.
        """
        data = self._readall()
        if not data and timeout != 0 and self._poller.poll(timeout):
            if read_delay is not None:
                sleep(read_delay / 1000.0)
            data = self._readall()
        return parse_events(data)

    def _readall(self):
        bytes_avail = c_int()
        ioctl(self, FIONREAD, bytes_avail)
        if not bytes_avail.value:
            return b''
        return os.read(self.fileno(), bytes_avail.value)


def parse_events(data):
    """Unpack data read from an inotify file descriptor into 
    :attr:`~inotify_simple.Event` namedtuples (wd, mask, cookie, name). This function
    can be used if the application has read raw data from the inotify file
    descriptor rather than calling :func:`~inotify_simple.INotify.read`.

    Args:
        data (bytes): A bytestring as read from an inotify file descriptor.
        
    Returns:
        list: list of :attr:`~inotify_simple.Event` namedtuples"""
    pos = 0
    events = []
    while pos < len(data):
        wd, mask, cookie, namesize = unpack_from(_EVENT_FMT, data, pos)
        pos += _EVENT_SIZE + namesize
        name = data[pos - namesize : pos].split(b'\x00', 1)[0]
        events.append(Event(wd, mask, cookie, name if PY2 else fsdecode(name)))
    return events


class flags(IntEnum):
    """Inotify flags as defined in ``inotify.h`` but with ``IN_`` prefix omitted.
    Includes a convenience method :func:`~inotify_simple.flags.from_mask` for extracting
    flags from a mask."""
    ACCESS = 0x00000001  #: File was accessed
    MODIFY = 0x00000002  #: File was modified
    ATTRIB = 0x00000004  #: Metadata changed
    CLOSE_WRITE = 0x00000008  #: Writable file was closed
    CLOSE_NOWRITE = 0x00000010  #: Unwritable file closed
    OPEN = 0x00000020  #: File was opened
    MOVED_FROM = 0x00000040  #: File was moved from X
    MOVED_TO = 0x00000080  #: File was moved to Y
    CREATE = 0x00000100  #: Subfile was created
    DELETE = 0x00000200  #: Subfile was deleted
    DELETE_SELF = 0x00000400  #: Self was deleted
    MOVE_SELF = 0x00000800  #: Self was moved

    UNMOUNT = 0x00002000  #: Backing fs was unmounted
    Q_OVERFLOW = 0x00004000  #: Event queue overflowed
    IGNORED = 0x00008000  #: File was ignored

    ONLYDIR = 0x01000000  #: only watch the path if it is a directory
    DONT_FOLLOW = 0x02000000  #: don't follow a sym link
    EXCL_UNLINK = 0x04000000  #: exclude events on unlinked objects
    MASK_ADD = 0x20000000  #: add to the mask of an already existing watch
    ISDIR = 0x40000000  #: event occurred against dir
    ONESHOT = 0x80000000  #: only send event once

    @classmethod
    def from_mask(cls, mask):
        """Convenience method that returns a list of every flag in a mask."""
        return [flag for flag in cls.__members__.values() if flag & mask]


class masks(IntEnum):
    """Convenience masks as defined in ``inotify.h`` but with ``IN_`` prefix omitted."""
    #: helper event mask equal to ``flags.CLOSE_WRITE | flags.CLOSE_NOWRITE``
    CLOSE = flags.CLOSE_WRITE | flags.CLOSE_NOWRITE
    #: helper event mask equal to ``flags.MOVED_FROM | flags.MOVED_TO``
    MOVE = flags.MOVED_FROM | flags.MOVED_TO

    #: bitwise-OR of all the events that can be passed to
    #: :func:`~inotify_simple.INotify.add_watch`
    ALL_EVENTS  = (flags.ACCESS | flags.MODIFY | flags.ATTRIB | flags.CLOSE_WRITE |
        flags.CLOSE_NOWRITE | flags.OPEN | flags.MOVED_FROM | flags.MOVED_TO | 
        flags.CREATE | flags.DELETE| flags.DELETE_SELF | flags.MOVE_SELF)
