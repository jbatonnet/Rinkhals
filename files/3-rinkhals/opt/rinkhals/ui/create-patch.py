# From a Windows machine:
#   docker run --rm -it -v .\files:/files ghcr.io/jbatonnet/rinkhals/build python3 /files/4-rinkhals/opt/rinkhals/ui/create-patch.py

import os

from pwn import *


def patchK3SysUi(binaryPath, modelCode, version):

    k3sysui = ELF(binaryPath)


    ################
    # Patch MainWindow::AcSupportRefresh()
    # - Make it return 0

    acSupportRefresh = k3sysui.symbols['_ZN10MainWindow16AcSupportRefreshEv']
    k3sysui.asm(acSupportRefresh + 0, 'mov pc, lr')

    freeSpace = acSupportRefresh + 4


    ################
    # Find the right patch / jump location
    # - In Ghidra, find connect<...AcXPageUiInit...> or a BtnRelease callback
    #     K2P / 3.1.2.3 - Settings > Support (5th button)
    #     K3 / 2.3.5.3, 2.3.7.1 - Settings > Support (5th button)
    #     KS1 / 2.4.8.3 - Settings > General > Service Support (4th button)

    if modelCode == 'K2P' and version == '3.1.2.3':
        buttonCallback = k3sysui.symbols['_ZN10MainWindow23AcSettingListBtnReleaseEi']
        patchJumpAddress = 0x99cb8
        patchJumpOperand = 'beq'
        patchReturnAddress = 0x99ce8

    elif modelCode == 'K3' and version == '2.3.5.3':
        buttonCallback = k3sysui.symbols['_ZN9QtPrivate18QFunctorSlotObjectIZN10MainWindow19AcSettingPageUiInitEvEUlvE_Li0ENS_4ListIJEEEvE4implEiPNS_15QSlotObjectBaseEP7QObjectPPvPb']
        patchJumpAddress = 0xe9d8c
        patchJumpOperand = 'b'
        patchReturnAddress = None

    elif modelCode == 'K3' and version == '2.3.7.1':
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow19AcSettingPageUiInitEvENKUlvE_clEv']
        patchJumpAddress = 0xf7970
        patchJumpOperand = 'b'
        patchReturnAddress = 0xf79a0

    elif modelCode == 'KS1' and version == '2.4.8.3':
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow26AcSettingGeneralPageUiInitEvENKUlRK11QModelIndexE0_clES2_']
        patchJumpAddress = 0x13f250
        patchJumpOperand = 'b'
        patchReturnAddress = 0x13f258

    else:
        raise Exception('Unsupported model and version')


    ################
    # Patch the callback to call our code instead
    # - Patch the target address with a jump to free space
    # - In free space, call system() and return

    system = k3sysui.symbols['system']
    displayStatusBar = k3sysui.symbols.get('_ZN10MainWindow24BottomStatusBarUiDisplayEh')
    resetStatusBar = k3sysui.symbols.get('_ZN10MainWindow20BottomStatusBarResetEv')

    # Find "this"
    # - If the function is short it might uses tailcalls. In this case, no parameters are stored on the stack, and we need to find the right register
    # - If this is a classic function, it will store "this"on the stack and we need to find it

    bytes = k3sysui.read(buttonCallback, 0x1000)

    strAssembly = b'\x00\x0b\xe5' # str r0, [fp, ??]
    strInstruction = bytes.find(strAssembly, 0, 4 * 10) - 1

    if strInstruction >= 0:
        thisOffset = bytes[strInstruction]
        thisInstructions = [ asm(f'ldr r0, [r11, #-0x{thisOffset:x}]'), asm('ldr r0, [r0]') ]
    else:
        for i in range(20):
            address = patchJumpAddress - i * 4
            instruction = k3sysui.read(address, 4)

            blInstruction = asm(f'bl 0x{displayStatusBar:x}', vma = address)
            if instruction == blInstruction:
                
                previousInstructions = [ k3sysui.read(address - 8, 4), k3sysui.read(address - 4, 4) ]
                for i in previousInstructions:
                    # ?? 00 a0 e1    mov r0, ?
                    if i[3] == 0xe1 and i[2] == 0xa0 and i[1] == 0x00:
                        thisInstructions = [ i ]
                        break

                    # ?? 00 ?? e5    ldr r0, ?
                    if i[3] == 0xe5 and i[1] == 0x00:
                        thisInstructions = [ i ]
                        break

                if thisInstructions:
                    break

    useTailCall = bytes[2] != 0x2d or bytes[3] != 0xe9 # push {?}

    # Write rinkhals-ui.sh path in free space
    rinkhalsUiPathBytes = b'/useremain/rinkhals/.current/opt/rinkhals/ui/rinkhals-ui.sh\x00'
    rinkhalsUiPath = freeSpace

    k3sysui.write(freeSpace, rinkhalsUiPathBytes)
    freeSpace += len(rinkhalsUiPathBytes)

    # Write the patch
    k3sysui.asm(patchJumpAddress, f'{patchJumpOperand} 0x{freeSpace:x}')

    address = freeSpace
    
    if modelCode == 'KS1' and version == '2.4.8.3':
        # if (row() != 3) return
        k3sysui.asm(address + 0, 'mov r0, r4')
        k3sysui.asm(address + 4, 'cmp r3, #0x3')
        k3sysui.asm(address + 8, f'bne 0x{(patchReturnAddress - 4):x}')
        address = address + 12

    # system('.../rinkhals-ui.sh')
    k3sysui.asm  (address +  0, f'ldr r0, [pc]')
    k3sysui.asm  (address +  4, f'b 0x{(address + 12):x}')
    k3sysui.write(address +  8, p32(rinkhalsUiPath))
    k3sysui.asm  (address + 12, f'bl 0x{system:x}')
    address = address + 16

    if modelCode == 'KS1':
        # this->BottomStatusBarReset()
        for i in thisInstructions:
            k3sysui.write(address, i)
            address = address + 4

        if useTailCall:
            k3sysui.asm(address, f'b 0x{resetStatusBar:x}')
        else:
            k3sysui.asm(address, f'bl 0x{resetStatusBar:x}')

        address = address + 4

    else:
        # this->BottomStatusBarUiDisplay(false)
        for i in thisInstructions:
            k3sysui.write(address, i)
            address = address + 4

        k3sysui.asm(address + 0,  'mov r1, #0x0')
        k3sysui.asm(address + 4, f'bl 0x{displayStatusBar:x}')
        address = address + 8

        # this->BottomStatusBarUiDisplay(true)
        for i in thisInstructions:
            k3sysui.write(address, i)
            address = address + 4

        k3sysui.asm(address,  'mov r1, #0x1')

        if useTailCall:
            k3sysui.asm(address + 4, f'b 0x{displayStatusBar:x}')
        else:
            k3sysui.asm(address + 4, f'bl 0x{displayStatusBar:x}')

        address = address + 8

    # return
    if not useTailCall:
        k3sysui.asm(address, f'b 0x{patchReturnAddress:x}')


    ################
    # Replace "Customer Support" with "Rinkhals"

    customerSupport = next(k3sysui.search(b'Customer Support\x00'), None)
    if customerSupport:
        k3sysui.write(customerSupport, b'Rinkhals\x00')

    serviceSupport = next(k3sysui.search(b'Service Support\x00'), None)
    if serviceSupport:
        k3sysui.write(serviceSupport, b'Rinkhals\x00')

    support = next(k3sysui.search(b'Support\x00'), None)
    if support:
        k3sysui.write(support, b'Rinkhal\x00') # Without final s so it's the same length :/


    ################
    # Patch isCustomFirmware()
    # - Make it return 0

    isCustomFirmware = k3sysui.symbols.get('_ZN8GobalVar16isCustomFirmwareEPKc')
    if isCustomFirmware:
        k3sysui.asm(isCustomFirmware + 0, 'mov r0, #0')
        k3sysui.asm(isCustomFirmware + 4, 'mov pc, lr')


    ################
    # Save patched binary

    acSupportRefresh_code = k3sysui.disasm(acSupportRefresh, 1024)
    buttonCallback_code = k3sysui.disasm(buttonCallback, 1024)
    isCustomFirmware_code = k3sysui.disasm(isCustomFirmware, 1024) if isCustomFirmware else None

    k3sysui.save(binaryPath + '.patch')

def main():

    context.update(arch='arm', bits=32, endian='little')

    RINKHALS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

    patchK3SysUi(RINKHALS_ROOT + '/opt/rinkhals/ui/K3SysUi.K2P_3.1.2.3', 'K2P', '3.1.2.3')
    patchK3SysUi(RINKHALS_ROOT + '/opt/rinkhals/ui/K3SysUi.K3_2.3.5.3', 'K3', '2.3.5.3')
    patchK3SysUi(RINKHALS_ROOT + '/opt/rinkhals/ui/K3SysUi.K3_2.3.7.1', 'K3', '2.3.7.1')
    patchK3SysUi(RINKHALS_ROOT + '/opt/rinkhals/ui/K3SysUi.KS1_2.4.8.3', 'KS1', '2.4.8.3')
    
if __name__ == "__main__":
    main()
