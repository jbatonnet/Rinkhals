"""cdefs for marshaller.py"""

import cython

from ..signature cimport SignatureTree


cdef object PACK_UINT32

cdef bytes PACKED_UINT32_ZERO
cdef bytes PACKED_BOOL_TRUE
cdef bytes PACKED_BOOL_FALSE

cdef get_signature_tree

cdef class Marshaller:

    cdef SignatureTree signature_tree
    cdef bytearray _buf
    cdef cython.list body

    cdef _buffer(self)

    cpdef align(self, unsigned int n)

    @cython.locals(
        offset=cython.ulong,
    )
    cdef unsigned int _align(self, unsigned int n)

    cpdef write_boolean(self, object boolean, object _type)

    @cython.locals(
        written=cython.uint,
    )
    cdef unsigned int _write_boolean(self, object boolean)

    cpdef write_string(self, object value, object _type)

    @cython.locals(
        value_len=cython.uint,
        signature_len=cython.uint,
        written=cython.uint,
    )
    cdef unsigned int _write_string(self, object value)

    @cython.locals(
        signature_len=cython.uint,
    )
    cdef unsigned int _write_signature(self, bytes signature_bytes)

    cpdef write_array(self, object array, object type)

    @cython.locals(
        array_len=cython.uint,
        buf=cython.bytearray,
        written=cython.uint,
        token=cython.str,
        array_len_packed=cython.bytes,
        size=cython.uint,
        writer=cython.object,
        packer=cython.object,
        i=cython.uint,
    )
    cdef unsigned int _write_array(self, object array, object type)

    cpdef write_struct(self, object array, object type)

    @cython.locals(
        written=cython.uint,
        i=cython.uint,
    )
    cdef unsigned int _write_struct(self, object array, object type)

    cpdef write_variant(self, object variant, object type)

    @cython.locals(
        written=cython.uint,
        signature=cython.str,
        signature_bytes=cython.bytes,
    )
    cdef unsigned int _write_variant(self, object variant, object type)

    @cython.locals(
        written=cython.uint,
        size=cython.uint,
    )
    cdef unsigned int _write_single(self, object type_, object body)

    @cython.locals(
        written=cython.uint,
        t=cython.str,
    )
    cpdef write_dict_entry(self, object type_, object body)

    cpdef marshall(self)

    cdef _marshall(self)

    @cython.locals(
        offset=cython.ulong,
        t=cython.str,
        size=cython.uint,
        writer=cython.object,
        packer=cython.object,
    )
    cdef _construct_buffer(self)
