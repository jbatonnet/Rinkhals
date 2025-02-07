# From a Windows machine:
#   docker run --rm -it -v .\files:/files ghcr.io/jbatonnet/rinkhals/build python3 /files/4-rinkhals/opt/rinkhals/ui/create-patch.py

import os

from pwn import *


def patchK3SysUi(binaryPath):

    k3sysui = ELF(binaryPath)


    ################
    # Patch MainWindow::AcSupportRefresh()
    # - Make it return 0

    acSupportRefresh = k3sysui.symbols['_ZN10MainWindow16AcSupportRefreshEv']
    if acSupportRefresh:
        k3sysui.asm(acSupportRefresh + 0, 'mov pc, lr')

    freeSpace = acSupportRefresh + 4


    ################
    # Find customer support page callback in MainWindow::AcSettingPageUiInit()::lambda()
    
    settingPageUi_touchCallback = k3sysui.symbols['_ZN9QtPrivate18QFunctorSlotObjectIZN10MainWindow19AcSettingPageUiInitEvEUlvE_Li0ENS_4ListIJEEEvE4implEiPNS_15QSlotObjectBaseEP7QObjectPPvPb']

    bytes = k3sysui.read(settingPageUi_touchCallback, 0x1000)

    case_asm = b'\x00\x00\xea' # b
    cases = []
    n = 0

    for i in range(6):
        n = bytes.find(case_asm, n + 1)
        cases.append(settingPageUi_touchCallback + n - 1)

    case_4 = cases[-1]
    case_4_jmp = k3sysui.read(case_4, 1)

    case_4 = case_4 + case_4_jmp[0] * 4 + 8


    ################
    # Patch the callback to call our code instead
    # - Move case 4 (Customer Support) to free space in isCustomFirmware
    # - In free space, call system() and return

    rinkhalsUiPathBytes = b'/useremain/rinkhals/.current/opt/rinkhals/ui/rinkhals-ui.sh\x00'
    rinkhalsUiPath = freeSpace

    k3sysui.write(freeSpace, rinkhalsUiPathBytes)
    freeSpace += len(rinkhalsUiPathBytes)

    setCurrentIndex = k3sysui.symbols['_ZN14QStackedWidget15setCurrentIndexEi']
    system = k3sysui.symbols['system']

    k3sysui.asm(freeSpace,      f'bl 0x{setCurrentIndex:x}')
    k3sysui.asm(freeSpace + 4,  f'ldr r0,[pc,0x4]')
    k3sysui.asm(freeSpace + 12, f'b 0x{system:x}')
    k3sysui.write(freeSpace + 16, p32(rinkhalsUiPath))

    k3sysui.asm(case_4 + 28, 'b 0x{:x}'.format(freeSpace))


    ################
    # Replace "Customer Support" with "Rinkhals"

    customerSupport = next(k3sysui.search(b'Customer Support'))
    k3sysui.write(customerSupport, b'Rinkhals\x00')


    ################
    # Patch isCustomFirmware()
    # - Make it return 0

    isCustomFirmware = k3sysui.symbols['_ZN8GobalVar16isCustomFirmwareEPKc']
    if isCustomFirmware:
        k3sysui.asm(isCustomFirmware + 0, 'mov r0, #0')
        k3sysui.asm(isCustomFirmware + 4, 'mov pc, lr')


    ################
    # Save patched binary

    settingPageUi_touchCallback_code = k3sysui.disasm(settingPageUi_touchCallback, 1024)
    isCustomFirmware_code = k3sysui.disasm(isCustomFirmware, 1024)

    k3sysui.save(binaryPath + '.patch')

def main():

    context.update(arch='arm', bits=32, endian='little')

    RINKHALS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
    patchK3SysUi(RINKHALS_ROOT + '/opt/rinkhals/ui/K3SysUi.K3-2.3.5.3')
    
if __name__ == "__main__":
    main()
