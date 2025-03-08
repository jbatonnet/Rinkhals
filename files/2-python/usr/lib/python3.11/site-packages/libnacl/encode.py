# -*- coding: utf-8 -*-
'''
Build in routines and classes to simplify encoding routines
'''
# Import python libs
import base64
import binascii


def hex_encode(data):
    '''
    Hex encode data
    '''
    return binascii.hexlify(data)


def hex_decode(data):
    '''
    Hex decode data
    '''
    return binascii.unhexlify(data)


def base16_encode(data):
    '''
    Base32 encode data
    '''
    return base64.b16encode(data)


def base16_decode(data):
    '''
    Base16 decode data
    '''
    return base64.b16decode(data)


def base32_encode(data):
    '''
    Base16 encode data
    '''
    return base64.b32encode(data)


def base32_decode(data):
    '''
    Base32 decode data
    '''
    return base64.b32decode(data)


def base64_encode(data):
    '''
    Base16 encode data
    '''
    return base64.b64encode(data)


def base64_decode(data):
    '''
    Base32 decode data
    '''
    return base64.b64decode(data)
