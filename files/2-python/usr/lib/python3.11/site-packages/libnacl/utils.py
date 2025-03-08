# -*- coding: utf-8 -*-

import struct
import sys
import time

# Import nacl libs
import libnacl
import libnacl.encode
import libnacl.secret
import libnacl.public
import libnacl.sign
import libnacl.dual


def load_key(path_or_file, serial='json'):
    '''
    Read in a key from a file and return the applicable key object based on
    the contents of the file
    '''
    if hasattr(path_or_file, 'read'):
        stream = path_or_file
    else:
        if serial == 'json':
            stream = open(path_or_file, 'r')
        else:
            stream = open(path_or_file, 'rb')

    try:
        if serial == 'msgpack':
            import msgpack
            key_data = msgpack.load(stream)
        elif serial == 'json':
            import json
            if sys.version_info[0] >= 3:
                key_data = json.loads(stream.read())
            else:
                key_data = json.loads(stream.read(), encoding='UTF-8')
    finally:
        if stream != path_or_file:
            stream.close()

    if 'priv' in key_data and 'sign' in key_data and 'pub' in key_data:
        return libnacl.dual.DualSecret(
                libnacl.encode.hex_decode(key_data['priv']),
                libnacl.encode.hex_decode(key_data['sign']))
    elif 'priv' in key_data and 'pub' in key_data:
        return libnacl.public.SecretKey(
                libnacl.encode.hex_decode(key_data['priv']))
    elif 'kx_priv' in key_data and 'kx_pub' in key_data:
        return libnacl.kx.ExchangeKey(
                libnacl.encode.hex_decode(key_data['kx_priv']))
    elif 'sign' in key_data:
        return libnacl.sign.Signer(
                libnacl.encode.hex_decode(key_data['sign']))
    elif 'pub' in key_data:
        return libnacl.public.PublicKey(
                libnacl.encode.hex_decode(key_data['pub']))
    elif 'verify' in key_data:
        return libnacl.sign.Verifier(key_data['verify'])
    elif 'priv' in key_data:
        return libnacl.secret.SecretBox(
                libnacl.encode.hex_decode(key_data['priv']))
    raise ValueError('Found no key data')


def salsa_key():
    '''
    Generates a salsa2020 key
    '''
    return libnacl.randombytes(libnacl.crypto_secretbox_KEYBYTES)


def aead_key():
    '''
    Generates an AEAD key (both implementations use the same size)
    '''
    return libnacl.randombytes(libnacl.crypto_aead_aes256gcm_KEYBYTES)


def rand_aead_nonce():
    '''
    Generates and returns a random bytestring of the size defined in libsodium
    as crypto_aead_aes256gcm_NPUBBYTES and crypto_aead_chacha20poly1305_ietf_NPUBBYTES
    '''
    return libnacl.randombytes(libnacl.crypto_aead_aes256gcm_NPUBBYTES)


def rand_aead_xchacha_nonce():
    '''
    Generates and returns a random bytestring of the size defined in libsodium
    as crypto_aead_aes256gcm_NPUBBYTES and crypto_aead_chacha20poly1305_ietf_NPUBBYTES
    '''
    return libnacl.randombytes(libnacl.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES)


def rand_nonce():
    '''
    Generates and returns a random bytestring of the size defined in libsodium
    as crypto_box_NONCEBYTES
    '''
    return libnacl.randombytes(libnacl.crypto_box_NONCEBYTES)


def time_nonce():
    '''
    Generates and returns a nonce as in rand_nonce() but using a timestamp for the first 8 bytes.

    This function now exists mostly for backwards compatibility, as rand_nonce() is usually preferred.
    '''
    nonce = rand_nonce()
    return (struct.pack('=d', time.time()) + nonce)[:len(nonce)]
