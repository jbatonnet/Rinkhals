# From a Windows machine:
#   docker run --rm -it -v .\files:/files ghcr.io/jbatonnet/rinkhals/build python3 /files/4-rinkhals/opt/rinkhals/ui/create-patch.py

import os

from pwn import *


def patchK3SysUi(binaryPath):

    k3sysui = ELF(binaryPath)


    ################
    # Replace "Non official firmware..." with "/useremain/rinkhals/.current/opt/rinkhals/ui/rinkhals-ui.sh"

    nonOfficialFirmware = next(k3sysui.search(b'Non official firmware'))
    k3sysui.write(nonOfficialFirmware, b'/useremain/rinkhals/.current/opt/rinkhals/ui/rinkhals-ui.sh\x00')
    rinkhalsUiPath = nonOfficialFirmware


    ################
    # Patch isCustomFirmware()
    # - Make it return 0

    isCustomFirmware = k3sysui.symbols['_ZN8GobalVar16isCustomFirmwareEPKc']

    k3sysui.asm(isCustomFirmware + 0,  'push {r4, r5, r6, r7, r8, r9, sl, lr}')
    k3sysui.asm(isCustomFirmware + 4,  'sub sp, sp, #0x500')
    k3sysui.asm(isCustomFirmware + 8,  'mov r1, #0')
    k3sysui.asm(isCustomFirmware + 12, 'mov r0, r1')
    k3sysui.asm(isCustomFirmware + 16, 'add sp, sp, #0x500')
    k3sysui.asm(isCustomFirmware + 20, 'pop {r4, r5, r6, r7, r8, r9, sl, pc}')
    k3sysui.asm(isCustomFirmware + 24, 'nop')


    ################
    # Patch MainWindow::AcSupportRefresh()
    # - Make it return 0

    acSupportRefresh = k3sysui.symbols['_ZN10MainWindow16AcSupportRefreshEv']

    k3sysui.asm(acSupportRefresh + 0,  'ldr r2, [pc, #0x43c]')
    k3sysui.asm(acSupportRefresh + 4,  'mvn r12, #0')
    k3sysui.asm(acSupportRefresh + 8,  'ldr r1, [pc, #0x438]')
    k3sysui.asm(acSupportRefresh + 12, 'mov r3, #0')
    k3sysui.asm(acSupportRefresh + 16, 'add r2, pc, r2')

    k3sysui.asm(acSupportRefresh + 20, 'push {r4, r5, r6, r7, r8, r9, lr}')
    k3sysui.asm(acSupportRefresh + 24, 'sub sp, sp, #0x1c')
    k3sysui.asm(acSupportRefresh + 28, 'mov r0, #0')
    k3sysui.asm(acSupportRefresh + 32, 'add sp, sp, #0x1c')
    k3sysui.asm(acSupportRefresh + 36, 'pop {r4, r5, r6, r7, r8, r9, pc}')


    ################
    # Patch MainWindow::AcSettingPageUiInit()::lambda()
    # - Move case 4 (Customer Support) to free space in isCustomFirmware
    # - In isCustomFirmware, call system() and return

    settingPageUi_touchCallback = k3sysui.symbols['_ZN9QtPrivate18QFunctorSlotObjectIZN10MainWindow19AcSettingPageUiInitEvEUlvE_Li0ENS_4ListIJEEEvE4implEiPNS_15QSlotObjectBaseEP7QObjectPPvPb']

    # Find position of case 4
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

    # Jump to free space in isCustomFirmware
    k3sysui.asm(case_4 + 28, 'b 0x{:x}'.format(isCustomFirmware + 28))

    # Call setCurrentIndex, then system('rinhals-ui.sh')
    setCurrentIndex = k3sysui.symbols['_ZN14QStackedWidget15setCurrentIndexEi']
    system = k3sysui.symbols['system']

    k3sysui.asm(isCustomFirmware + 28, f'bl 0x{setCurrentIndex:x}')
    k3sysui.asm(isCustomFirmware + 32, 'ldr r0,[pc,#0x8]')
    k3sysui.asm(isCustomFirmware + 36, 'add r0,pc,r0')
    k3sysui.asm(isCustomFirmware + 40, f'b 0x{system:x}')
    k3sysui.asm(isCustomFirmware + 44, 'nop')

    k3sysui.write(isCustomFirmware + 48, p32(rinkhalsUiPath - (isCustomFirmware + 48) + 4))


    ################
    # Replace "Customer Support" with "Rinkhals"

    customerSupport = next(k3sysui.search(b'Customer Support'))
    k3sysui.write(customerSupport, b'Rinkhals\x00')


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
