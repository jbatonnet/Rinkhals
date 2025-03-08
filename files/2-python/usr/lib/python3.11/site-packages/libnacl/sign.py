# -*- coding: utf-8 -*-
'''
High level routines to maintain signing keys and to sign and verify messages
'''
# Import libancl libs
import libnacl
import libnacl.base
import libnacl.encode


class Signer(libnacl.base.BaseKey):
    '''
    The tools needed to sign messages
    '''
    def __init__(self, seed=None):
        '''
        Create a signing key, if not seed it supplied a keypair is generated
        '''
        if seed:
            if len(seed) != libnacl.crypto_sign_SEEDBYTES:
                raise ValueError('Invalid seed bytes')
            self.vk, self.sk = libnacl.crypto_sign_seed_keypair(seed)
        else:
            seed = libnacl.randombytes(libnacl.crypto_sign_SEEDBYTES)
            self.vk, self.sk = libnacl.crypto_sign_seed_keypair(seed)
        self.seed = seed
        super().__init__()

    def sign(self, msg):
        '''
        Sign the given message with this key
        '''
        return libnacl.crypto_sign(msg, self.sk)

    def signature(self, msg):
        '''
        Return just the signature for the message
        '''
        return libnacl.crypto_sign(msg, self.sk)[:libnacl.crypto_sign_BYTES]


class Verifier(libnacl.base.BaseKey):
    '''
    Verify signed messages
    '''
    def __init__(self, vk_hex):
        '''
        Create a verification key from a hex encoded vkey
        '''
        self.vk = libnacl.encode.hex_decode(vk_hex)
        super().__init__()

    def verify(self, msg):
        '''
        Verify the message with tis key
        '''
        return libnacl.crypto_sign_open(msg, self.vk)
