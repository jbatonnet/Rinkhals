# From a Windows machine:
#   docker run --rm -it -v .\files:/files -w /files/3-rinkhals/opt/rinkhals/patches ghcr.io/jbatonnet/rinkhals/build python3 ../scripts/create-patch.py .

import os
import json
import subprocess
import base64
import re
import sys

from pwn import context, ELF, asm, p32, util, enhex, u32


def read32(binary, address):
    return u32(binary.read(address, 4))

def getGoFunctions(binary):

    # Read cache if available
    md5 = util.hashes.md5file(binary.path)
    cachePath = f'{os.path.dirname(binary.path)}/cache_{enhex(md5)}.json'
    if os.path.isfile(cachePath):
        with open(cachePath, 'r') as f:
            return json.loads(f.read())

    gopclntab = binary.get_section_by_name('.gopclntab')
    gopclntab = gopclntab.header.sh_addr

    functionCount = read32(binary, gopclntab + 8)
    textStart = read32(binary, gopclntab + 16)
    
    functionNameTable = gopclntab + read32(binary, gopclntab + 20)
    functionTable = gopclntab + read32(binary, gopclntab + 36)

    functions = {}

    for i in range(functionCount):
        try:
            addressOffset = read32(binary, functionTable + i * 8)
            address = textStart + addressOffset

            functionOffset = read32(binary, functionTable + i * 8 + 4)
            function = functionTable + functionOffset

            nameOffset = read32(binary, function + 4)
            name = functionNameTable + nameOffset

            bytes = binary.read(name, 1024)
            name = bytes[:bytes.find(0)].decode('utf-8')

            functions[address] = name

        except:
            break

    with open(cachePath, 'w') as f:
        f.write(json.dumps(functions))

    return functions


def patch_K3SysUi(binaryPath, modelCode, version):

    if os.path.isfile(f'{binaryPath}.patch'):
        return
        
    k3sysui = ELF(binaryPath, checksec=False)


    ################
    # Patch MainWindow::AcSupportRefresh()
    # - Make it return 0

    acSupportRefresh = k3sysui.symbols['_ZN10MainWindow16AcSupportRefreshEv']
    k3sysui.asm(acSupportRefresh + 0, 'mov pc, lr')

    freeSpace = acSupportRefresh + 4


    ################
    # Find the right patch / jump location
    # - In Ghidra, find connect<...AcXPageUiInit...> or a BtnRelease callback
    #   K2P / 3.1.2.3 - Settings > Support (5th button)

    patchJumpOperand = 'b'
    s1RowRegister = 'r3'

    if modelCode == 'K2P' and version == '3.1.2.3':
        buttonCallback = k3sysui.symbols['_ZN10MainWindow23AcSettingListBtnReleaseEi']
        patchJumpAddress = 0x99cb8
        patchJumpOperand = 'beq'
        patchReturnAddress = 0x99ce8
    elif modelCode == 'K2P' and version == '3.1.4':
        buttonCallback = k3sysui.symbols['_ZN10MainWindow23AcSettingListBtnReleaseEi']
        patchJumpAddress = 0x8c4ac
        patchJumpOperand = 'beq'
        patchReturnAddress = 0x8c528

    # K3 - Settings > Support (5th button)

    # case 4
    #     MainWindow::BottomStatusBarUiDisplay((*r0).b)
    #     QStackedWidget::setCurrentIndex(*(*r0 + 0x108c))

    # ldr r3, [r11, #-0x8]                 < patchJumpAddress
    # ldr r3, [r3]
    # mov r1, #0
    # mov r0, r3
    # bl  MainWindow::BottomStatusBarUiDisplay
    # ldr r3, [r11, #-0x8]
    # ldr r3, [r3]
    # add r3, r3, #0x1000
    # ldr r3, [r3, #0x8c]
    # mov r1, #0x1b
    # mov r0, r3
    # bl  QStackedWidget::setCurrentIndex
    # b   0xfaf4c                          < patchReturnAddress

    elif (modelCode == 'K3' and version == '2.4.0') or (modelCode == 'K3M' and version == '2.4.6'):
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow19AcSettingPageUiInitEvENKUlvE_clEv']
        patchJumpAddress = 0xfd278
        patchReturnAddress = 0xfd2a8
    elif (modelCode == 'K3' and version == '2.4.0.4') or (modelCode == 'K3M' and version == '2.4.6.5') or (modelCode == 'K3V2' and version == '1.0.5.8'):
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow19AcSettingPageUiInitEvENKUlvE_clEv']
        patchJumpAddress = 0xfef8c
        patchReturnAddress = 0xfefbc
    elif (modelCode == 'K3' and version == '2.4.1.9') or (modelCode == 'K3M' and version == '2.4.8.4') or (modelCode == 'K3V2' and version == '1.0.7.3'):
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow19AcSettingPageUiInitEvENKUlvE_clEv']
        patchJumpAddress = 0xecc30
        patchReturnAddress = 0xecc5c
    elif (modelCode == 'K3' and version == '2.4.4.3') or (modelCode == 'K3M' and version == '2.5.0.9') or (modelCode == 'K3V2' and version == '1.0.9.7'):
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow19AcSettingPageUiInitEvENKUlvE_clEv']
        patchJumpAddress = 0xf1c98
        patchReturnAddress = 0xf1cc4
    elif (modelCode == 'K3' and version == '2.4.4.7') or (modelCode == 'K3M' and version == '2.5.1.3') or (modelCode == 'K3V2' and version == '1.1.0.1'):
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow19AcSettingPageUiInitEvENKUlvE_clEv']
        patchJumpAddress = 0x103528
        patchReturnAddress = 0x103558
    elif (modelCode == 'K3' and version == '2.4.5') or (modelCode == 'K3M' and version == '2.5.1.7') or (modelCode == 'K3V2' and version == '1.1.0.4'):
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow19AcSettingPageUiInitEvENKUlvE_clEv']
        patchJumpAddress = 0x103558
        patchReturnAddress = 0x103588

    # KS1 - Settings > General > Service Support (4th button)
    
    # int32_t r4_1 = *(*arg1 + 0x10d4)
    # QModelIndex::row()
    # return QStackedWidget::setCurrentIndex(r4_1)

    # bl      QModelIndex::row
    # mov     r3, r0
    # mov     r1, r3
    # mov     r0, r4                           < patchJumpAddress
    # bl      QStackedWidget::setCurrentIndex
    # nop                                      < patchReturnAddress

    elif modelCode == 'KS1' and version == '2.5.3.1':
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow26AcSettingGeneralPageUiInitEvENKUlRK11QModelIndexE0_clES2_']
        patchJumpAddress = 0x11f48c
        patchReturnAddress = 0x11f494
    elif modelCode == 'KS1' and version == '2.5.3.5':
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow26AcSettingGeneralPageUiInitEvENKUlRK11QModelIndexE0_clES2_']
        patchJumpAddress = 0x12048c
        patchReturnAddress = 0x120494
    elif modelCode == 'KS1' and version == '2.5.3.8':
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow26AcSettingGeneralPageUiInitEvENKUlRK11QModelIndexE0_clES2_']
        patchJumpAddress = 0x1204ac
        patchReturnAddress = 0x1204b4
    elif modelCode == 'KS1' and version == '2.5.6.0':
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow26AcSettingGeneralPageUiInitEvENKUlRK11QModelIndexE0_clES2_']
        patchJumpAddress = 0x121db4
        patchReturnAddress = 0x121dbc
    elif modelCode == 'KS1' and version == '2.5.6.4':
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow26AcSettingGeneralPageUiInitEvENKUlRK11QModelIndexE0_clES2_']
        patchJumpAddress = 0x121dd4
        patchReturnAddress = 0x121ddc
    elif modelCode == 'KS1' and version == '2.5.8.8':
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow26AcSettingGeneralPageUiInitEvENKUlRK11QModelIndexE0_clES2_']
        patchJumpAddress = 0x12b04c
        patchReturnAddress = 0x12b054
    elif modelCode == 'KS1' and (version == '2.5.9.9' or version == '2.6.0.0'):
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow21AcSettingDeviceUiInitEvENKUlRK11QModelIndexE0_clES2_']
        patchJumpAddress = 0x14a51c
        patchReturnAddress = 0x14a524
        s1RowRegister = 'r1'
        
    elif modelCode == 'KS1M' and version == '2.1.6':
        buttonCallback = k3sysui.symbols['_ZZN10MainWindow21AcSettingDeviceUiInitEvENKUlRK11QModelIndexE0_clES2_']
        patchJumpAddress = 0x14a514
        patchReturnAddress = 0x14a51c
        s1RowRegister = 'r1'

    else:
        raise Exception('Unsupported model and version')


    ################
    # Patch the callback to call our code instead
    # - Patch the target address with a jump to free space
    # - In free space, call system() and return

    displayStatusBar = k3sysui.symbols.get('_ZN10MainWindow24BottomStatusBarUiDisplayEh')
    
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

    # Used functions
    system = k3sysui.symbols['system']
    osSleep = k3sysui.symbols['_ZN8GobalVar7OsSleepEi']
    acDisplayWaitHandler = k3sysui.symbols['_ZN10MainWindow20AcDisplayWaitHandlerEhh']
    
    if modelCode == 'K3' or modelCode == 'K3M' or modelCode == 'K3V2':
        acDisplayWaitHide = k3sysui.symbols['_ZN10MainWindow17AcDisplayWaitHideEv']
    elif modelCode == 'KS1' or modelCode == 'KS1M':
        acDisplayWaitHide = k3sysui.symbols['_ZN10MainWindow17AcDisplayWaitHideEh']
    elif modelCode == 'K2P':
        acDisplayWaitHide = acDisplayWaitHandler

    # Write system commands in free space
    startRinkhalsUiBytes = b'/useremain/rinkhals/.current/opt/rinkhals/ui/rinkhals-ui.sh & echo $! > /tmp/rinkhals/rinkhals-ui.pid\x00'
    k3sysui.write(freeSpace, startRinkhalsUiBytes)
    startRinkhalsUi = freeSpace
    freeSpace += len(startRinkhalsUiBytes)

    waitRinkhalsUiBytes = b'timeout -t 2 strace -qqq -e trace=none -p $(cat /tmp/rinkhals/rinkhals-ui.pid) 2> /dev/null\x00'
    k3sysui.write(freeSpace, waitRinkhalsUiBytes)
    waitRinkhalsUi = freeSpace
    freeSpace += len(waitRinkhalsUiBytes)

    cleanPidFileBytes = b'rm -f /tmp/rinkhals/rinkhals-ui.pid\x00'
    k3sysui.write(freeSpace, cleanPidFileBytes)
    cleanPidFile = freeSpace
    freeSpace += len(cleanPidFileBytes)

    # Write the patch
    address = freeSpace + 4
    address = address - address % 4
    k3sysui.asm(patchJumpAddress, f'{patchJumpOperand} 0x{address:x}')
    
    if modelCode == 'KS1' or modelCode == 'KS1M':
        # if (row() != 3) return
        k3sysui.asm(address + 0, 'mov r0, r4')
        k3sysui.asm(address + 4, f'cmp {s1RowRegister}, #0x3')
        k3sysui.asm(address + 8, f'bne 0x{(patchReturnAddress - 4):x}')
        address = address + 12

    # system('.../rinkhals-ui.sh & echo $! > /tmp/rinkhals/rinkhals-ui.pid')
    k3sysui.asm  (address +  0,  'ldr r0, [pc]')
    k3sysui.asm  (address +  4, f'b 0x{(address + 12):x}')
    k3sysui.write(address +  8, p32(startRinkhalsUi))
    k3sysui.asm  (address + 12, f'bl 0x{system:x}')
    address = address + 16

    # loop:
    loopAddress = address

    # OsSleep(100)
    k3sysui.asm(address + 0, f'mov r0, #0x{100:x}')
    k3sysui.asm(address + 4, f'bl 0x{osSleep:x}')
    address = address + 8

    # code = system('timeout -t 2 strace -qqq -e trace=none -p $(cat /tmp/rinkhals/rinkhals-ui.pid) 2> /dev/null')
    k3sysui.asm  (address +  0, f'ldr r0, [pc]')
    k3sysui.asm  (address +  4, f'b 0x{(address + 12):x}')
    k3sysui.write(address +  8, p32(waitRinkhalsUi))
    k3sysui.asm  (address + 12, f'bl 0x{system:x}')
    address = address + 16

    # if code == 15: goto loop
    k3sysui.asm(address + 0,   'cmp r0, #0x0F') # Terminated (15)
    k3sysui.asm(address + 4,  f'beq 0x{loopAddress:x}')
    address = address + 8

    # system('rm -f /tmp/rinkhals/rinkhals-ui.pid')
    k3sysui.asm  (address +  0, f'ldr r0, [pc]')
    k3sysui.asm  (address +  4, f'b 0x{(address + 12):x}')
    k3sysui.write(address +  8, p32(cleanPidFile))
    k3sysui.asm  (address + 12, f'bl 0x{system:x}')
    address = address + 16

    # this->AcDisplayWaitHandler(1, 4)
    acDisplayWaitHandler = k3sysui.symbols.get('_ZN10MainWindow20AcDisplayWaitHandlerEhh')

    for i in thisInstructions:
        k3sysui.write(address, i)
        address = address + 4

    k3sysui.asm(address + 0,  'mov r2, #0x4')
    k3sysui.asm(address + 4,  'mov r1, #0x1')
    k3sysui.asm(address + 8, f'bl 0x{acDisplayWaitHandler:x}')
    address = address + 12

    # this->AcDisplayWaitHide()
    for i in thisInstructions:
        k3sysui.write(address, i)
        address = address + 4

    if modelCode == 'K2P':
        k3sysui.asm(address + 0,  'mov r1, #0x0')
    else:
        k3sysui.asm(address + 0,  'mov r1, #0x4')

    if useTailCall:
        k3sysui.asm(address + 4, f'b 0x{acDisplayWaitHide:x}')
    else:
        k3sysui.asm(address + 4, f'bl 0x{acDisplayWaitHide:x}')

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

def patch_gkapi(binaryPath, modelCode, version):

    if os.path.isfile(f'{binaryPath}.patch'):
        return

    gkapi = ELF(binaryPath, checksec=False)

    functionsByAddress = getGoFunctions(gkapi)
    functionsByName = { f: int(a) for a, f in functionsByAddress.items() }


    ################
    # Open MQTT broker to the outside

    # brokerAddress = next(gkapi.search(b'127.0.0.1:2883'), None)
    # if brokerAddress:
    #     gkapi.write(brokerAddress, b'0.0.0.0:002883')


    ################
    # Change orcaSim (Octoprint compat API) to port 71
    # - We replace the reference to :80 by a reference to :71 (from localhost:7125)

    moonrakerAddress = next(gkapi.search(b'localhost:7125'), None)
    if moonrakerAddress:
        orcaSimStart = functionsByName.get('printerApi/service/orcaSim.Start')

        moonrakerOffset = None
        for i in range(200):
            moonrakerReference = read32(gkapi, orcaSimStart + 4 * i)
            if moonrakerReference == moonrakerAddress:
                moonrakerOffset = i * 4
                break

        if moonrakerOffset:
            gkapi.write(orcaSimStart + moonrakerOffset - 4, p32(moonrakerAddress + 9))
        

    ################
    # Patch calls to printerApi/common/config.LanPrintIsOpen
    # - Force startup of MQTT broker
    # - Force SSDP discovery
    # - Try to force AI detection startup

    if False:
        lanModeReplacementTargets = {}
        # lanModeReplacementTargets = {
        #     # SSDP, safe patches
        #     'printerApi/service/ssdp.(*ssdp).Advertise': [ True ],
        #     'printerApi/service/ssdp.(*HttpServer).Run.(*HttpServer).handleInfoWrapper.func2': [ True ],
        #     'printerApi/service/ssdp.(*HttpServer).Run.(*HttpServer).handleCtrlWrapper.func3': [ True ],
        #     'printerApi/service/ssdp.(*HttpServer).handleGcodeUpload': [ True ],

        #     # To start the MQTT broker
        #     'main.main': [ True ],

        #     # Control LAN vs Cloud
        #     'printerApi/common/config.GetDeviceUnionid': [ True ],
        #     'printerApi/cloud.(*Cloud).Connect': [ True ],

        #     #'printerApi/cloud.(*printerHandler).runAIDetect': [ False ],
        #     #'printerApi/cloud.(*printerHandler).handleUIResumePrintEvent': [ False ],
        #     #'printerApi/cloud.(*printerHandler).localtask': [ True ],
        #     #'printerApi/cloud.ReportCloudConnectState': [ False ],
        #     #'0x56c8f4': [ True ], # ?
        # }

        lanPrintIsOpen = functionsByName['printerApi/common/config.LanPrintIsOpen']

        for name, patches in lanModeReplacementTargets.items():
            address = functionsByName.get(name)
            if not address:
                address = int(name, 16)

            for p in patches:
                while True:
                    address += 4

                    instruction = gkapi.read(address, 4)
                    if instruction[3] != 0xeb:
                        continue

                    blInstruction = asm(f'bl 0x{lanPrintIsOpen:x}', vma = address)
                    if instruction == blInstruction:
                        # Then look for those instructions
                        #   cmp r0, #0x0
                        #   beq ? / bne ?

                        for i in range(20):
                            instruction = gkapi.read(address + i * 4, 4)
                            if instruction[3] != 0x0a and instruction[3] != 0x1a: # beq or bne
                                continue

                            logic = instruction[3] == 0x1a # bne

                            # Patch accordingly
                            if p == logic:
                                gkapi.write(address + i * 4 + 3, b'\xea') # b
                            else:
                                gkapi.asm(address + i * 4, 'nop')

                            break
                        break

    gkapi.save(binaryPath + '.patch')

def create_patch_script(beforePath, afterPath, scriptPath):

    if os.path.isfile(scriptPath):
        return
        
    beforeMd5 = util.hashes.md5file(beforePath)
    beforeMd5 = enhex(beforeMd5)
    afterMd5 = util.hashes.md5file(afterPath)
    afterMd5 = enhex(afterMd5)
    
    if beforeMd5 == afterMd5:
        return

    command = f'cmp -l {beforePath} {afterPath}'
    cmp = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    diff = cmp.communicate()[0]
    diff = diff.decode('utf-8').strip()

    with open(scriptPath, 'w') as f:
        f.write('#!/bin/sh\n')
        f.write('\n')
        f.write("# This script was automatically generated, don't modify it directly\n")
        f.write(f'# Before MD5: {beforeMd5}\n')
        f.write(f'# After MD5: {afterMd5}\n')
        f.write('\n')
        f.write('TARGET=$1\n')
        f.write('\n')
        f.write("MD5=$(md5sum $TARGET | awk '{print $1}')\n")
        f.write(f'if [ "$MD5" = "{afterMd5}" ]; then\n')
        f.write('    echo $TARGET is already patched, skipping...\n')
        f.write('    exit 0\n')
        f.write('fi\n')
        f.write(f'if [ "$MD5" != "{beforeMd5}" ]; then\n')
        f.write('    echo $TARGET hash does not match, skipping patch...\n')
        f.write('    exit 1\n')
        f.write('fi\n')
        f.write('\n')
        f.write('PATCH_FILE=/tmp/patch-$RANDOM.bin\n')

        diffs = diff.splitlines()

        patchBytes = [ int(d.split()[2], 8) for d in diffs ]
        patchBytes = bytes(patchBytes)

        patchBase64 = base64.b64encode(patchBytes)
        patchBase64 = patchBase64.decode('utf-8')

        f.write(f"echo '{patchBase64}' | base64 -d > $PATCH_FILE\n")
        f.write('\n')

        i = 0
        while i < len(diffs):
            address, before, after = diffs[i].split()

            j = i + 1
            while j < len(diffs):
                nextAddress, nextBefore, nextAfter = diffs[j].split()
                if int(nextAddress) != int(address) + (j - i):
                    break
                j += 1

            f.write(f"dd if=$PATCH_FILE skip={i} ibs=1 of=$TARGET seek={int(address) - 1} obs=1 count={j - i} conv=notrunc")
            f.write(f' # 0x{int(address) - 1:x} / 0x{int(address) + 0x10000 - 1:x} > 0x{enhex(bytes([ int(d.split()[2], 8) for d in diffs[i:j] ]))}\n')
            i = j
            
        f.write('\n')
        f.write('rm $PATCH_FILE\n')
        

# Entrypoint to process a single file
def main_file(path, model, version):
    fileName = os.path.basename(path)
    print(f'Patching {fileName} for {model} {version}')

    if 'gkapi' in fileName:
        patch_gkapi(path, model, version)
        create_patch_script(path, f'{path}.patch', f'{path}.sh')
    if 'K3SysUi' in fileName:
        patch_K3SysUi(path, model, version)
        create_patch_script(path, f'{path}.patch', f'{path}.sh')

# Entrypoint to process a directory of binaries
def main_directory(path):
    files = os.listdir(path)
    for file in files:
        match = re.search('^([a-zA-Z0-9]+)\.(K[A-Z0-9]+)_([0-9.]+)$', file)
        if not match:
            continue

        model = match.group(2)
        version = match.group(3)

        main_file(f'{path}/{file}', model, version)

# Main entrypoint
def main():
    context.update(arch='arm', bits=32, endian='little')

    def noop(me):
        pass

    #ELF._populate_got = noop
    #ELF._populate_plt = noop

    if len(sys.argv) > 1:
        path = sys.argv[1]

        if os.path.isdir(path):
            main_directory(path)
            return
        
        if os.path.isfile(path):
            model = os.getenv('KOBRA_MODEL_CODE')
            version = os.getenv('KOBRA_VERSION')

            match = re.search('^([a-zA-Z0-9]+)\.(K[A-Z0-9]+)_([0-9.]+)$', os.path.basename(path))
            if match:
                model = match.group(2)
                version = match.group(3)

            if len(sys.argv) == 4:
                model = sys.argv[2]
                version = sys.argv[3]

            if not model or not version:
                sys.exit(1)

            main_file(path, model, version)
            return

    print("Usage:")
    print(f"  {sys.argv[0]} <directory_path>")
    print(f"  {sys.argv[0]} <file_path> # Extracts model/version from filename")
    print(f"  {sys.argv[0]} <file_path> <model> <version>")
    print(f"  {sys.argv[0]} # Process default directory")
    sys.exit(1)

if __name__ == "__main__":
    main()
