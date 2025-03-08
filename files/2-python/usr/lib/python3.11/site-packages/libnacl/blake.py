'''
Mimic very closely the python hashlib classes for blake2b

NOTE:
    This class does not yet implement streaming the msg into the
    hash function via the update method
'''

# Import python libs
import binascii

# Import libnacl libs
import libnacl


class Blake2b(object):
    '''
    Manage a Blake2b hash
    '''
    def __init__(self, msg, key=None):
        self.msg = msg
        self.key = key
        self.raw_digest = libnacl.crypto_generichash(msg, key)
        self.digest_size = len(self.raw_digest)

    def digest(self):
        '''
        Return the digest of the string
        '''
        return self.raw_digest

    def hexdigest(self):
        '''
        Return the hex digest of the string
        '''
        return binascii.hexlify(self.raw_digest)


def blake2b(msg, key=None):
    '''
    Create and return a Blake2b object to mimic the behavior of the python
    hashlib functions
    '''
    return Blake2b(msg, key)
