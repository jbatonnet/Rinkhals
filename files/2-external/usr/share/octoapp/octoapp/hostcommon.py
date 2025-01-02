import random
import string

# Common functions that the hosts might need to use.
class HostCommon:

    # The length the printer ID should be.
    # Note that the max length for a subdomain part (strings between . ) is 63 chars!
    # Making this a max of 60 chars allows for the service to use 3 chars prefixes for inter-service calls.
    c_OctoAppPrinterIdMaxLength = 60
    c_OctoAppPrinterIdMinLength = 40

    # Returns a new printer Id. This needs to be crypo-random to make sure it's not predictable.
    @staticmethod
    def GeneratePrinterId():
        return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(HostCommon.c_OctoAppPrinterIdMaxLength))

    @staticmethod
    def IsPrinterIdValid(printerId):
        return printerId is not None and len(printerId) >= HostCommon.c_OctoAppPrinterIdMinLength and len(printerId) <= HostCommon.c_OctoAppPrinterIdMaxLength