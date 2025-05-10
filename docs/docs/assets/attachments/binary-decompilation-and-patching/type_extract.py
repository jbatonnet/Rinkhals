#Find types in stripped Go binaries.
#@author padorka@cujoai
#@category goscripts
#@keybinding 
#@menupath 
#@toolbar 

import struct
from ghidra.program.model.symbol.SourceType import *

versions = [
'\x67\x6f\x31\x2e\x32\x33',
'\x67\x6f\x31\x2e\x32\x32',
'\x67\x6f\x31\x2e\x32\x31',
'\x67\x6f\x31\x2e\x32\x30',
'\x67\x6f\x31\x2e\x31\x39',
'\x67\x6f\x31\x2e\x31\x38',
'\x67\x6f\x31\x2e\x31\x37',
'\x67\x6f\x31\x2e\x31\x36',
'\x67\x6f\x31\x2e\x31\x35',
'\x67\x6f\x31\x2e\x31\x34',
'\x67\x6f\x31\x2e\x31\x33',
'\x67\x6f\x31\x2e\x31\x32',
'\x67\x6f\x31\x2e\x31\x31',
'\x67\x6f\x31\x2e\x31\x30',
'\x67\x6f\x31\x2e\x39',
'\x67\x6f\x31\x2e\x38',
'\x67\x6f\x31\x2e\x37',
'\x67\x6f\x31\x2e\x36',
'\x67\x6f\x31\x2e\x35',
'\x67\x6f\x31\x2e\x34',
'\x67\x6f\x31\x2e\x33',
'\x67\x6f\x31\x2e\x32']

pclntab_magic = ['\xfb\xff\xff\xff\x00\x00',
'\xfa\xff\xff\xff\x00\x00',
'\xf0\xff\xff\xff\x00\x00',
'\xf1\xff\xff\xff\x00\x00']

#Get address at a specific address
def getAddressAt(address):
    return currentProgram.getAddressFactory().getAddress(hex(getInt(address)))

#Remove data at a specific location. Needed to be able to create the right strings. 
def removeDataAll(address, length):
    for i in range(length):
        removeDataAt(address.add(i))

#Find .typelink section
def getTypelink():
    for block in getMemoryBlocks():
        if block.getName() == ".typelink":
            start = block.getStart()
            end = block.getEnd()
            print "%s [start: 0x%x, end: 0x%x]" % (block.getName(), start.getOffset(), end.getOffset())
            return start,end
    print "No .typelink section found."
    return None

#Find .rodata section
def getRodata():
    for block in getMemoryBlocks():
        if block.getName() == ".rodata":
            start = block.getStart()
            end = block.getEnd()
            print "%s [start: 0x%x, end: 0x%x]" % (block.getName(), start.getOffset(), end.getOffset())
            return start
    print "No .rodata section found."
    return None

#Find version by string search
#ToDo: Find a smarter solution.
def findVersion():
    for version in versions:
        #Search could be smarter by looking only in specific sections
        address = currentProgram.getMinAddress()
        while address != None:
            address = findBytes(address.add(1), version)
            if address == None:
                continue
            else:
                print "Version found"
                print version
                return version
    return None

#Until go1.16 - two-byte long length. Now we only search for the second byte, possibly miss very long strings.
#From go1.17 - Varint-encoded length. Now we only search for the first byte, possible issues with long strings.
#Todo: Change it to avoid possible issues.
def getLengthOffset():
    if version in ['\x67\x6f\x31\x2e\x32\x33', '\x67\x6f\x31\x2e\x31\x39', '\x67\x6f\x31\x2e\x31\x38', '\x67\x6f\x31\x2e\x31\x37']:
        return 1
    else:
        return 2
    return None

#Find pclntab by looking for magic value
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
                return pclntab, magic
    return pclntab, None

#Test if pclntab was found by checking pc quantum and pointer size values
def isPclntab(address):
    pc_quantum = getByte(address.add(6))
    pointer_size = getByte(address.add(7))
    if (pc_quantum != 1 and pc_quantum != 2 and pc_quantum != 4) or (pointer_size != 4 and pointer_size != 8):
         return False
    return True

#Find moduledata by looking for references to pclntab
def findModuledata(pclntab, magic):
    references_to_pclntab = getReferencesTo(pclntab)
    for i in range (len(references_to_pclntab)):
        module_data = references_to_pclntab[i].getFromAddress()
        if isModuledata(module_data, magic):
            return module_data
    #If reference was not created look for the pclntab address directly
    #Search could be smarter by looking only in specific sections
    module_data = currentProgram.getMinAddress()
    while module_data != None:
        s = struct.pack('<I', pclntab.getOffset())
        module_data = findBytes(module_data.add(1),s)
        print module_data
        if module_data == None:
            return None
        if isModuledata(module_data, magic):
            return module_data
    return None

#Test if moduldata was found by checking .text section address
def isModuledata(address, magic):
    if magic == '\xfb\xff\xff\xff\x00\x00':
        offset = 12
    else:
        offset = 22
    text = getAddressAt(address.add(offset*pointer_size))
    memory = currentProgram.getMemory()
    if text == memory.getBlock(".text").getStart():
        print "Moduldata found"
        return True
    return False

#Get typelinks slice, beginning and end of types section
def getTypelinks(moduledata, magic):
    if magic == '\xfb\xff\xff\xff\x00\x00':
        offset = 25
        offset2 = 30
    else:
        offset = 35
        offset2 = 42
    type = getAddressAt(moduledata.add(offset*pointer_size))
    etype = getAddressAt(moduledata.add((offset+1)*pointer_size))
    typelinks = getAddressAt(moduledata.add(offset2*pointer_size))
    ntypes = getInt(moduledata.add((offset2+1)*pointer_size))
    return type, etype, typelinks, ntypes

#Main function to find and recover types
def recoverTypes(type_address):
    if type_address in recovered_types:
        print "Type already recovered at  0x%x" % type_address.getOffset()
        return type_address
    recovered_types.append(type_address)
    print "type_address: 0x%x" % type_address.getOffset()
    tflagUncommon = getByte(type_address.add(2*pointer_size+4))&0x01
    tflagExtraStar = getByte(type_address.add(2*pointer_size+4))&0x02
    kind = getByte(type_address.add(2*pointer_size+7))&0x1F
    print "KIND: 0x%x" % kind
    name_offset = getInt(type_address.add(4*pointer_size+8))
    name_length = getByte(type.add(name_offset + length_offset))
    name_address = type.add(name_offset + length_offset + 1)
    removeDataAll(name_address,name_length)
    try:
        name = createAsciiString(name_address,name_length)
    except:
        print "Error at  0x%x" % type_address.getOffset()
        return type_address

    if tflagExtraStar:
        name_type = name.getValue()[1:]
    else:
        name_type = name.getValue()
    print "NAME: %s" % name_type
    createLabel(type_address,name_type.replace(" ","_"), 1)
    #print "type_address: 0x%x, name_offset:0x%x, name_address:0x%x, data:%s" %(type_address.getOffset(), name_offset, name_address.getOffset(), name_type)

    #Function type
    #// funcType represents a function type.
    #//
    #// A *rtype for each in and out parameter is stored in an array that
    #// directly follows the funcType (and possibly its uncommonType). So
    #// a function type with one method, one input, and one output is:
    #//
    #//	struct {
    #//		funcType
    #//		uncommonType
    #//		[2]*rtype    // [0] is in, [1] is out
    #//	}
    #type funcType struct {
    #	rtype
    #	inCount  uint16
    #	outCount uint16 // top bit is set if last input parameter is ...
    #}
    if kind == 0x13:
        inCount = struct.unpack('<H',getBytes(type_address.add(4*pointer_size+8+8),2))[0]
        out_bytes = getBytes(type_address.add(4*pointer_size+8+8+2),2)
        #top bit is set if last input parameter is ...
        last_input = out_bytes[1]&0x80
        out_bytes[1] = out_bytes[1]&0x7F
        print last_input
        outCount = struct.unpack('<H',out_bytes)[0]
        inputs = []
        outputs= []
        for i in range(inCount):
            input = getAddressAt(type_address.add(4*pointer_size+8+8+pointer_size + tflagUncommon*16 + i*pointer_size))
            recoverTypes(input)
            inputs.append(getSymbolAt(input).getName())
        for i in range(outCount):
            output = getAddressAt(type_address.add(4*pointer_size+8+8+pointer_size + tflagUncommon*16 +inCount*pointer_size + i*pointer_size))
            recoverTypes(output)
            outputs.append(getSymbolAt(output).getName())
        if last_input == 0x80 and len(inputs) > 0:
            inputs[-1] = inputs[-1].replace("[]","...")
        setPreComment(type_address,"func(" + ", ".join(inputs) + ")" + " (" +  ", ".join(outputs) + ")")

    #Interface type
    #// interfaceType represents an interface type.
    #type interfaceType struct {
    #	rtype
    #	pkgPath name      // import path
    #	methods []imethod // sorted by hash
    #}
    #// imethod represents a method on an interface type
    #type imethod struct {
    #	name nameOff // name of method
    #	typ  typeOff // .(*FuncType) underneath
    #}
    if kind == 0x14:
        imethod_field = getAddressAt(type_address.add(5*pointer_size+8+8))
        methods = []
        methods_length = getInt(type_address.add(6*pointer_size+8+8))
        for i in range(methods_length):
            imethod_name_offset = (getInt(imethod_field))
            name_length = getByte(type.add(imethod_name_offset + length_offset))
            name_address = type.add(imethod_name_offset + length_offset + 1)
            removeDataAll(name_address, name_length)
            name = createAsciiString(name_address, name_length) 
            setEOLComment(imethod_field,name.getValue())
            createLabel(imethod_field,name.getValue().replace(" ","_"), 1)
            new_type_offset = (getInt(imethod_field.add(4)))
            new_type = type.add(new_type_offset)
            print "new_type: 0x%x" % new_type.getOffset()
            recoverTypes(new_type)
            imethod_field = imethod_field.add(8)
            methods.append(name.getValue()  + " " + getSymbolAt(new_type).getName())
        setPreComment(type_address,"type " + name_type + " interface{" + "\n\t" + "\n\t".join(methods) + "\n" + "}")

    #Pointer type
    #// ptrType represents a pointer type.
    #type ptrType struct {
    #	rtype
    #	elem *rtype // pointer element (pointed at) type
    #}
    if kind == 0x16:
        new_address =currentProgram.getAddressFactory().getAddress(hex(getInt(type_address.add(4*pointer_size+8+8)))) 
        recoverTypes(new_address)

    # Struct type
    #// structType represents a struct type.
    #type structType struct {
    #	rtype
    #	pkgPath name
    #	fields  []structField // sorted by offset
    #}
    #// Struct field
    #type structField struct {
    #	name        name    // name is always non-empty
    #	typ         *rtype  // type of field
    #	offsetEmbed uintptr // byte offset of field<<1 | isEmbedded
    #}
    if kind == 0x19:
        struct_field =getAddressAt(type_address.add(5*pointer_size+8+8))
        fields = []
        fields_length = getInt(type_address.add(6*pointer_size+8+8))
        for i in range(fields_length):
            struct_field_name = getAddressAt(struct_field)
            name_length_address = struct_field_name.add(length_offset)
            name_length = getByte(name_length_address)
            name_address = getAddressAt(struct_field).add(length_offset+1)
            removeDataAll(name_address, name_length)
            name = createAsciiString(name_address, name_length)
            setEOLComment(struct_field,name.getValue())
            createLabel(struct_field_name,name.getValue().replace(" ","_"), 1)
            new_type = getAddressAt(struct_field.add(pointer_size))
            print "new_type: 0x%x" % new_type.getOffset()
            recoverTypes(new_type)
            struct_field = struct_field.add(3*pointer_size)
            fields.append(name.getValue()  + " " + getSymbolAt(new_type).getName())
        setPreComment(type_address,"type " + name_type + " struct{" + "\n\t" + "\n\t".join(fields) + "\n" + "}")

def mainPE():
    pclntab, magic = findPclntabPE()
    module_data = findModuledata(pclntab, magic)
    type, etype, typelinks, ntypes = getTypelinks(module_data, magic) 
    etypelinks = typelinks.add(ntypes*4)
    return typelinks, etypelinks, type

def mainELF():
    typelinks, etypelinks = getTypelink() 
    type = getRodata()
    etypelinks = etypelinks.add(1)
    return typelinks, etypelinks, type

def getAllTypes(typelinks, etypelinks, type):
    if typelinks is not None:
        p = typelinks
        while p != etypelinks:
            type_offset = getInt(p)
            type_address = type.add(type_offset)
            recoverTypes(type_address)
            p = p.add(4)
    print len(recovered_types)
    return len(recovered_types)

executable_format = currentProgram.getExecutableFormat()
pointer_size = currentProgram.getDefaultPointerSize()
recovered_types = []
version = findVersion()
length_offset = getLengthOffset()

if executable_format== "Portable Executable (PE)":
    print "PE file found"
    typelinks, etypelinks, type = mainPE()
    getAllTypes(typelinks, etypelinks, type)
elif executable_format== "Executable and Linking Format (ELF)":
    print "ELF file found"
    typelinks, etypelinks, type = mainELF()
    getAllTypes(typelinks, etypelinks, type)
else:
    print "Incorrect file format."
