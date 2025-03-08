# -*- coding: utf-8 -*-
'''
High level classes and routines around public key encryption and decryption
'''
# import libnacl libs
import libnacl
import libnacl.utils
import libnacl.encode
import libnacl.dual
import libnacl.base


class PublicKey(libnacl.base.BaseKey):
    '''
    This class is used to manage public keys
    '''
    def __init__(self, pk):
        if len(pk) == libnacl.crypto_box_PUBLICKEYBYTES:
            self.pk = pk
        else:
            raise ValueError('Passed in invalid public key')
        super().__init__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.pk == other.pk
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.pk)


class SecretKey(libnacl.base.BaseKey):
    '''
    This class is used to manage keypairs
    '''
    def __init__(self, sk=None):
        '''
        If a secret key is not passed in then it will be generated
        '''
        if sk is None:
            self.pk, self.sk = libnacl.crypto_box_keypair()
        elif len(sk) == libnacl.crypto_box_SECRETKEYBYTES:
            self.sk = sk
            self.pk = libnacl.crypto_scalarmult_base(sk)
        else:
            raise ValueError('Passed in invalid secret key')
        super().__init__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.sk == other.sk and self.pk == other.pk
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.sk, self.pk))


class Box(object):
    '''
    TheBox class is used to create cryptographic boxes and unpack
    cryptographic boxes
    '''
    def __init__(self, sk, pk):
        if isinstance(sk, (SecretKey, libnacl.dual.DualSecret)):
            sk = sk.sk
        if isinstance(pk, (SecretKey, libnacl.dual.DualSecret)):
            raise ValueError('Passed in secret key as public key')
        if isinstance(pk, PublicKey):
            pk = pk.pk
        if pk and sk:
            self._k = libnacl.crypto_box_beforenm(pk, sk)

    def encrypt(self, msg, nonce=None, pack_nonce=True):
        '''
        Encrypt the given message with the given nonce, if the nonce is not
        provided it will be generated from the libnacl.utils.rand_nonce
        function
        '''
        if nonce is None:
            nonce = libnacl.utils.rand_nonce()
        elif len(nonce) != libnacl.crypto_box_NONCEBYTES:
            raise ValueError('Invalid nonce size')
        ctxt = libnacl.crypto_box_afternm(msg, nonce, self._k)
        if pack_nonce:
            return nonce + ctxt
        else:
            return nonce, ctxt

    def decrypt(self, ctxt, nonce=None):
        '''
        Decrypt the given message, if a nonce is passed in attempt to decrypt
        it with the given nonce, otherwise assum that the nonce is attached
        to the message
        '''
        if nonce is None:
            nonce = ctxt[:libnacl.crypto_box_NONCEBYTES]
            ctxt = ctxt[libnacl.crypto_box_NONCEBYTES:]
        elif len(nonce) != libnacl.crypto_box_NONCEBYTES:
            raise ValueError('Invalid nonce')
        msg = libnacl.crypto_box_open_afternm(ctxt, nonce, self._k)
        return msg
