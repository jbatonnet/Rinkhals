"""
Implementation of the X25519 Key Exchange function. These classes make executing a key
exchange simple.
"""
import libnacl
import libnacl.base
import libnacl.utils


class ExchangeKey(libnacl.base.BaseKey):
    """
    The class used to manage key exchange keys
    """
    def __init__(self, kx_sk=None, enc=None):
        if kx_sk is None:
            self.kx_pk, self.kx_sk = libnacl.crypto_kx_keypair()
        elif len(kx_sk) == libnacl.libnacl.crypto_kx_SECRETKEYBYTES:
            self.kx_sk = kx_sk
            self.kx_pk = libnacl.crypto_scalarmult_base(kx_sk)
        if enc is None:
            self.enc = "xchacha"
        elif enc in ("xchacha", "aesgcm", "chacha"):
            self.enc = enc
        else:
            raise ValueError(f"Invalid encryption type passed: {enc}")
    
    def get_crypt(self, key):
        return getattr(self, f"get_{self.enc}")(key)

    def get_xchacha(self, key):
        return libnacl.aead.AEAD_XCHACHA(key)

    def get_chacha(self, key):
        return libnacl.aead.AEAD_CHACHA(key)

    def get_aesgcm(self, key):
        return libnacl.aead.AEAD_AESGCM(key)

    def client_session_keys(self, remote_pk):
        """
        Takes a remote public key and derives the rx and tx session keys
        """
        return libnacl.crypto_kx_client_session_keys(self.kx_pk, self.kx_sk, remote_pk)

    def server_session_keys(self, remote_pk):
        """
        Takes a remote public key and derives the rx and tx session keys
        """
        return libnacl.crypto_kx_server_session_keys(self.kx_pk, self.kx_sk, remote_pk)

    def encrypt_client(self, remote_pk, msg, ad):
        """
        Encrypt the given message using the remote_sk
        """
        rx, tx, status = self.client_session_keys(remote_pk)

        crypter = self.get_crypt(tx)
        return crypter.encrypt(msg, ad)

    def encrypt_server(self, remote_pk, msg, ad):
        """
        Encrypt the given message using the remote_sk
        """
        rx, tx, status = self.server_session_keys(remote_pk)

        crypter = self.get_crypt(tx)
        return crypter.encrypt(msg, ad)

    def decrypt_client(self, remote_pk, ctxt, len_ad):
        rx, tx, status = self.client_session_keys(remote_pk)

        crypter = self.get_crypt(rx)
        clear = crypter.decrypt(ctxt, len_ad)
        #ad = ctxt[:len_ad]
        return clear

    def decrypt_server(self, remote_pk, ctxt, len_ad):
        rx, tx, status = self.server_session_keys(remote_pk)

        crypter = self.get_crypt(rx)
        clear = crypter.decrypt(ctxt, len_ad)
        #ad = ctxt[:len_ad]
        return clear
