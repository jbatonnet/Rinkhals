"""cdefs for signature.py"""

import cython


cdef class SignatureType:

    cdef public str token
    cdef public list children
    cdef str _signature


cdef class SignatureTree:

    cdef public str signature
    cdef public list types


cdef class Variant:

    cdef public object type
    cdef public object signature
    cdef public object value
