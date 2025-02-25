"""cdefs for service.py"""

import cython


cdef class _Method:

    cdef public object name
    cdef public object fn
    cdef public object disabled
    cdef public object introspection
    cdef public object in_signature
    cdef public object out_signature
    cdef public object in_signature_tree
    cdef public object out_signature_tree

cdef class ServiceInterface:

    cdef public object name
    cdef list __methods
    cdef list __properties
    cdef list __signals
    cdef set __buses
    cdef dict __handlers
