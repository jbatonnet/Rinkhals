#Find statically allocated string structures in Go binaries.
# type stringStruct struct {
#     str unsafe.Pointer
#     len int
# }
#@author padorka@cujoai
#@category goscripts
#@keybinding 
#@menupath 
#@toolbar 

from ghidra.program.model.data import PointerDataType
from ghidra.program.model.data import IntegerDataType
from ghidra.program.model.data import LongDataType


image_base = currentProgram.getImageBase()
max_offset = currentProgram.getMaxAddress()
pointer_size = currentProgram.getDefaultPointerSize()

print "Image Base: 0x%x, Max offset: 0x%x" % (image_base.getOffset(), max_offset.getOffset())

#Look for strings with printable characters only to eliminate FPs.
def isPrintable(s, l):
    for i in range(l):
        if getByte(s) not in range(32,126):
            return False
        s = s.add(1)
    return True

def string_rename(ptr):
    for block in getMemoryBlocks():
        if block.getName() not in [".data", ".rodata"]:
            continue
        start = block.getStart()
        end = block.getEnd()
        while start <= end:
            string_address_pointer = start
            length_address = start.add(ptr)
            start = start.add(ptr)
            try:
                if pointer_size == 8:
                    length = getLong(length_address)
                else:
                    length = getInt(length_address)
                #Set the possible length to eliminate FPs.
                if length not in range(1,100):
                    continue
                if pointer_size == 8:
                    string_address = currentProgram.getAddressFactory().getAddress(hex(getLong(string_address_pointer)).rstrip("L"))
                else:
                    string_address = currentProgram.getAddressFactory().getAddress(hex(getInt(string_address_pointer)))
                if string_address < image_base or string_address >= max_offset:
                    continue
                if not isPrintable (string_address, length):
                    continue
                #Create pointer to string.
                createData(string_address_pointer, PointerDataType.dataType)
                if getDataAt(length_address) is not None:
                    data_type = getDataAt(length_address).getDataType()
                    #Remove undefined data to be able to create int. 
                    #Keep an eye on other predefined data types.
                    if data_type.getName() in ["undefined4", "undefined8"]:
                        removeData(getDataAt(length_address))
                #Create int at length.
                createData(length_address, IntegerDataType.dataType)
                #Create string.
                createAsciiString(string_address, length)
            except:
                continue

pointer = currentProgram.getDefaultPointerSize()

print "pointer: %d" % pointer

string_rename(pointer)
