#Recover function names in stripped Go binaries.
#@author padorka@cujoai
#@category goscripts
#@keybinding 
#@menupath 
#@toolbar 

from ghidra.program.model.symbol.SourceType import *

pclntab_magic = ['\xfb\xff\xff\xff\x00\x00',
'\xfa\xff\xff\xff\x00\x00',
'\xf0\xff\xff\xff\x00\x00']

#Find pclntab structure in Windows PE files
def findPclntabPE():
    for magic in pclntab_magic:
        #Search could be smarter by looking only in specific sections
        pclntab = currentProgram.getMinAddress()
        while pclntab != None:
            pclntab = findBytes(pclntab.add(1), magic)
            if pclntab == None:
                continue
            if isPclntab(pclntab):
                print "Pclntab found"
                return pclntab
    return pclntab

#Test if pclntab was found by checking pc quantum and pointer size values
def isPclntab(address):
    pc_quantum = getByte(address.add(6))
    pointer_size = getByte(address.add(7))
    if (pc_quantum != 1 and pc_quantum != 2 and pc_quantum != 4) or (pointer_size != 4 and pointer_size != 8):
         return False
    return True

#Find the .gopclntab section
def getGopclntab():
    for block in getMemoryBlocks():
        if block.getName() == ".gopclntab":
            start = block.getStart()
            end = block.getEnd()
            print "%s [start: 0x%x, end: 0x%x]" % (block.getName(), start.getOffset(), end.getOffset())
            return start
    print "No .gopclntab section found."
    return None

#Recover function names for Go versions 1.2 - 1.15
def renameFunc12(start):
    ptrsize= getByte(start.add(7))
    if ptrsize == 8:
        nfunctab = getLong(start.add(8))
    else:
        nfunctab = getInt(start.add(8))
    functab = start.add(8 + ptrsize)

    p = functab
    for i in range (nfunctab):
        if ptrsize == 8:
            func_address = currentProgram.getAddressFactory().getAddress(hex(getLong(p)).rstrip("L"))
            p = p.add(ptrsize)
            name_offset = getLong(p)
        else:
            func_address = currentProgram.getAddressFactory().getAddress(hex(getInt(p)))
            p = p.add(ptrsize)
            name_offset = getInt(p)
        p = p.add(ptrsize)
        name_pointer = start.add(name_offset + ptrsize)
        name_address = start.add(getInt(name_pointer))
        func_name = getDataAt(name_address)

        #Try to define function name string.
        if func_name is None:
            try:
                func_name = createAsciiString(name_address)
            except:
                print "ERROR: No name" 
                continue

        
        func = getFunctionAt(func_address)
        if func is not None:
            func_name_old = func.getName()
            func.setName(func_name.getValue().replace(" ", ""), USER_DEFINED)
            print "Function %s renamed as %s" % (func_name_old, func_name.getValue())
        else:
            func = createFunction(func_address, func_name.getValue())
            print "New function created: %s" % func_name

#Recover function names for Go versions 1.16 - 1.17
def renameFunc116(start):
    ptrsize= getByte(start.add(7))
    if ptrsize == 8:
        nfunctab = getLong(start.add(8))
        offset = getLong(start.add(8 + 2*ptrsize))
        funcnametab = start.add(offset)
        offset = getLong(start.add(8 + 6*ptrsize))
    else:
        nfunctab = getInt(start.add(8))
        offset = getInt(start.add(8 + 2*ptrsize))
        funcnametab = start.add(offset)
        offset = getInt(start.add(8 + 6*ptrsize))
    functab = start.add(offset)

    p = functab
    for i in range (nfunctab):
        if ptrsize == 8:
            func_address = currentProgram.getAddressFactory().getAddress(hex(getLong(p)).rstrip("L"))
            p = p.add(ptrsize)
            funcdata_offset = getLong(p)
        else:
            func_address = currentProgram.getAddressFactory().getAddress(hex(getInt(p)))
            p = p.add(ptrsize)
            funcdata_offset = getInt(p)
        p = p.add(ptrsize)
        name_pointer = functab.add(funcdata_offset + ptrsize)
        name_address = funcnametab.add(getInt(name_pointer))
        func_name = getDataAt(name_address)

        #Try to define function name string.
        if func_name is None:
            try:
                func_name = createAsciiString(name_address)
            except:
                print "ERROR: No name" 
                continue

        
        func = getFunctionAt(func_address)
        if func is not None:
            func_name_old = func.getName()
            func.setName(func_name.getValue().replace(" ", ""), USER_DEFINED)
            print "Function %s renamed as %s" % (func_name_old, func_name.getValue())
        else:
            func = createFunction(func_address, func_name.getValue())
            print "New function created: %s" % func_name

#Recover function names for Go versions 1.18 - 1.19
def renameFunc118(start):
    ptrsize= getByte(start.add(7))
    if ptrsize == 8:
        nfunctab = getLong(start.add(8))
        textStart = getLong(start.add(8 + 2*ptrsize))
        offset = getLong(start.add(8 + 3*ptrsize))
        funcnametab = start.add(offset)
        offset = getLong(start.add(8 + 7*ptrsize))
    else:
        nfunctab = getInt(start.add(8))
        textStart = getInt(start.add(8 + 2*ptrsize))
        offset = getInt(start.add(8 + 3*ptrsize))
        funcnametab = start.add(offset)
        offset = getInt(start.add(8 + 7*ptrsize))
    functab = start.add(offset)

    p = functab
    functabFieldSize = 4
    for i in range (nfunctab):
        func_address = currentProgram.getAddressFactory().getAddress(hex(getInt(p)+textStart).rstrip("L"))
        p = p.add(functabFieldSize)
        funcdata_offset = getInt(p)
        p = p.add(functabFieldSize)
        name_pointer = functab.add(funcdata_offset + functabFieldSize)
        name_address = funcnametab.add(getInt(name_pointer))
        func_name = getDataAt(name_address)

        #Try to define function name string.
        if func_name is None:
            try:
                func_name = createAsciiString(name_address)
            except:
                print "ERROR: No name" 
                continue

        
        func = getFunctionAt(func_address)
        if func is not None:
            func_name_old = func.getName()
            func.setName(func_name.getValue().replace(" ", ""), USER_DEFINED)
            print "Function %s renamed as %s" % (func_name_old, func_name.getValue())
        else:
            func = createFunction(func_address, func_name.getValue())
            print "New function created: %s" % func_name

#Recover function names for Go versions 1.20 and above
def renameFunc120(start):
    ptrsize= getByte(start.add(7))
    if ptrsize == 8:
        nfunctab = getLong(start.add(8))
        textStart = getLong(start.add(8 + 2*ptrsize))
        offset = getLong(start.add(8 + 3*ptrsize))
        funcnametab = start.add(offset)
        offset = getLong(start.add(8 + 7*ptrsize))
    else:
        nfunctab = getInt(start.add(8))
        textStart = getInt(start.add(8 + 2*ptrsize))
        offset = getInt(start.add(8 + 3*ptrsize))
        funcnametab = start.add(offset)
        offset = getInt(start.add(8 + 7*ptrsize))
    functab = start.add(offset)

    p = functab
    functabFieldSize = 4
    for i in range (nfunctab):
        func_address = currentProgram.getAddressFactory().getAddress(hex(getInt(p)+textStart).rstrip("L"))
        p = p.add(functabFieldSize)
        funcdata_offset = getInt(p)
        p = p.add(functabFieldSize)
        name_pointer = functab.add(funcdata_offset + functabFieldSize)
        name_address = funcnametab.add(getInt(name_pointer))
        func_name = getDataAt(name_address)

        #Try to define function name string.
        if func_name is None:
            try:
                func_name = createAsciiString(name_address)
            except:
                print "ERROR: No name" 
                continue

        
        func = getFunctionAt(func_address)
        if func is not None:
            func_name_old = func.getName()
            func.setName(func_name.getValue().replace(" ", ""), USER_DEFINED)
            print "Function %s renamed as %s" % (func_name_old, func_name.getValue())
        else:
            func = createFunction(func_address, func_name.getValue())
            print "New function created: %s" % func_name

executable_format = currentProgram.getExecutableFormat()
start = None

if executable_format== "Portable Executable (PE)":
    print "PE file found"
    start = findPclntabPE()
elif executable_format== "Executable and Linking Format (ELF)":
    print "ELF file found"
    start = getGopclntab()
else:
    print "Incorrect file format."
    
if start is not None:
    magic = getInt(start) & 0xffffffff
    if magic == 0xfffffff1:
        renameFunc120(start)
    elif magic == 0xfffffff0:
        renameFunc118(start)
    elif magic == 0xfffffffa:
        renameFunc116(start)
    elif magic == 0xfffffffb:
        renameFunc12(start)
    else:
        print "WARNING: Unknown .gopclntab magic, assuming Go 1.2 compatibility"
        renameFunc12(start)
