import cython

from .message cimport Message
from .service cimport ServiceInterface, _Method


cdef object MessageType
cdef object DBusError
cdef object MessageFlag

cdef object MESSAGE_TYPE_CALL
cdef object MESSAGE_TYPE_SIGNAL
cdef object NO_REPLY_EXPECTED_VALUE
cdef object assert_object_path_valid
cdef object assert_bus_name_valid

cdef _expects_reply(Message msg)

cdef class SendReply:

    cdef object _bus
    cdef object _msg

cdef class BaseMessageBus:

    cdef public object unique_name
    cdef public object _disconnected
    cdef public object _user_disconnect
    cdef public object _method_return_handlers
    cdef public object _serial
    cdef public object _path_exports
    cdef public cython.list _user_message_handlers
    cdef public object _name_owners
    cdef public object _bus_address
    cdef public object _name_owner_match_rule
    cdef public object _match_rules
    cdef public object _high_level_client_initialized
    cdef public object _ProxyObject
    cdef public object _machine_id
    cdef public object _negotiate_unix_fd
    cdef public object _sock
    cdef public object _stream
    cdef public object _fd

    cpdef _process_message(self, Message msg)

    @cython.locals(
        method=_Method,
        interface=ServiceInterface
    )
    cdef _find_message_handler(self, Message msg)
