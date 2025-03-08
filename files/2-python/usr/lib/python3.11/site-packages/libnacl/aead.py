# -*- coding: utf-8 -*-
'''
Utilities to make secret box encryption simple
'''
# Import libnacl
import libnacl
import libnacl.utils
import libnacl.base


class AEAD(libnacl.base.BaseKey):
    '''
    Manage AEAD encryption using the IETF ChaCha20-Poly1305(default) or AES-GCM algorithm
    '''

    def __init__(self, key=None):
        if key is None:
            key = libnacl.utils.aead_key()
        if len(key) != libnacl.crypto_aead_chacha20poly1305_ietf_KEYBYTES:  # same size for both
            raise ValueError('Invalid key')
        self.sk = key
        self.usingAES = False
        self.usingXCHACHA = False
        super().__init__()

    def useAESGCM(self):
        self.usingAES = True
        return self

    def useXCHACHA(self):
        self.usingXCHACHA = True
        return self

    def encrypt(self, msg, aad, nonce=None, pack_nonce_aad=True):
        '''
        Encrypt the given message. If a nonce is not given it will be
        generated via the rand_nonce function
        '''
        if nonce is None:
            if self.usingXCHACHA:
                nonce = libnacl.utils.rand_aead_xchacha_nonce()
            else:
                nonce = libnacl.utils.rand_aead_nonce()
        if self.usingXCHACHA:
            if len(nonce) != libnacl.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES:
                raise ValueError('Invalid nonce')
        else:
            if len(nonce) != libnacl.crypto_aead_aes256gcm_NPUBBYTES:
                raise ValueError('Invalid nonce')
        if self.usingXCHACHA:
            ctxt = libnacl.crypto_aead_xchacha20poly1305_ietf_encrypt(msg, aad, nonce, self.sk)
        elif self.usingAES:
            ctxt = libnacl.crypto_aead_aes256gcm_encrypt(msg, aad, nonce, self.sk)
        else:
            ctxt = libnacl.crypto_aead_chacha20poly1305_ietf_encrypt(msg, aad, nonce, self.sk)

        if pack_nonce_aad:
            return aad + nonce + ctxt
        else:
            return aad, nonce, ctxt

    def decrypt(self, ctxt, aadLen):
        '''
        Decrypt the given message, if no nonce or aad are given they will be
        extracted from the message
        '''
        aad = ctxt[:aadLen]
        if self.usingXCHACHA:
            nonce = ctxt[aadLen:aadLen+libnacl.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES]
            ctxt = ctxt[aadLen+libnacl.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES:]
            if len(nonce) != libnacl.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES:
                raise ValueError('Invalid nonce')
        else:
            nonce = ctxt[aadLen:aadLen+libnacl.crypto_aead_aes256gcm_NPUBBYTES]
            ctxt = ctxt[aadLen+libnacl.crypto_aead_aes256gcm_NPUBBYTES:]
            if len(nonce) != libnacl.crypto_aead_aes256gcm_NPUBBYTES:
                raise ValueError('Invalid nonce')
        if self.usingXCHACHA:
            return libnacl.crypto_aead_xchacha20poly1305_ietf_decrypt(ctxt, aad, nonce, self.sk)
        if self.usingAES:
            return libnacl.crypto_aead_aes256gcm_decrypt(ctxt, aad, nonce, self.sk)
        return libnacl.crypto_aead_chacha20poly1305_ietf_decrypt(ctxt, aad, nonce, self.sk)

    def decrypt_unpacked(self, aad, nonce, ctxt):
        '''
        Decrypt the given message, if no nonce or aad are given they will be
        extracted from the message
        '''
        if len(nonce) != libnacl.crypto_aead_aes256gcm_NPUBBYTES:
            raise ValueError('Invalid nonce')
        if self.usingAES:
            return libnacl.crypto_aead_aes256gcm_decrypt(ctxt, aad, nonce, self.sk)
        return libnacl.crypto_aead_chacha20poly1305_ietf_decrypt(ctxt, aad, nonce, self.sk)


class AEAD_AESGCM(AEAD):
    def __init__(self, key=None):
        super().__init__(key)
        self.useAESGCM()


class AEAD_XCHACHA(AEAD):
    def __init__(self, key=None):
        super().__init__(key)
        self.useXCHACHA()


class AEAD_CHACHA(AEAD):
    def __init__(self, key=None):
        super().__init__(key)
