#Find dynamically allocated string structures in Go binaries. 
# type stringStruct struct {
#     str unsafe.Pointer
#     len int
# }
#Different instructions per architecture. Multiple solutions are possible.
#Future ToDo: add newly discovered instruction sequences.
#@author padorka@cujoai
#@category goscripts
#@keybinding
#@menupath
#@toolbar

from ghidra.program.model.lang import OperandType

#x86
#LEA REG, [STRING_ADDRESS]
#MOV [ESP + ..], REG
#MOV [ESP + ..], STRING_SIZE

def string_rename_x86():
    for block in getMemoryBlocks():
        if block.getName() != ".text":
            continue
        start = block.getStart()
        ins = getInstructionAt(start)
        while ins:
            op_type = ins.getOperandType(1)
            reg = ins.getRegister(0)
            #Check first instruction: LEA REG, [STRING_ADDRESS]
            if ins.getMnemonicString() != "LEA" or reg is None or OperandType.isAddress(op_type) is False:
                ins = getInstructionAfter(ins)
                continue

            ins_next = getInstructionAfter(ins)

            #Check second instruction: MOV [ESP + ..], REG (where REG is the same as in previous instruction)
            if ins_next.getMnemonicString() != "MOV" or ins_next.getRegister(1) != reg  or ins_next.getOpObjects(0)[0].toString() != "ESP":
                ins = getInstructionAfter(ins)
                continue

            ins_next2 = getInstructionAfter(ins_next)
            op_type = ins_next2.getOperandType(1)

            #Check third instruction: MOV [ESP + ..], STRING_SIZE
            if ins_next2.getMnemonicString() != "MOV" or ins_next2.getOpObjects(0)[0].toString() != "ESP" or OperandType.isScalar(op_type) is False:
                ins = getInstructionAfter(ins)
                continue

            address = ins.getPrimaryReference(1).getToAddress()
            length = ins_next2.getOpObjects(1)[0].getValue()

            try:
                #Create string.
                createAsciiString(address, length)
                #print "SUCCESS at %s" % address
            except:
                #print "ERROR at address %s" % ins.getAddress()
                ins = getInstructionAfter(ins)
                continue

            ins = getInstructionAfter(ins)

#x86_64
#LEA REG, [STRING_ADDRESS]
#MOV [RSP + ..], REG
#MOV [RSP + ..], STRING_SIZE

def string_rename_x86_64():
    for block in getMemoryBlocks():
        if block.getName() != ".text":
            continue
        start = block.getStart()
        ins = getInstructionAt(start)
        while ins:
            op_type = ins.getOperandType(1)
            reg = ins.getRegister(0)
            #Check first instruction: LEA REG, [STRING_ADDRESS]
            if ins.getMnemonicString() != "LEA" or reg is None or OperandType.isAddress(op_type) is False:
                ins = getInstructionAfter(ins)
                continue

            ins_next = getInstructionAfter(ins)

            #Check second instruction: MOV [RSP + ..], REG (where REG is the same as in previous instruction)
            if ins_next.getMnemonicString() != "MOV" or ins_next.getRegister(1) != reg  or ins_next.getOpObjects(0)[0].toString() != "RSP":
                ins = getInstructionAfter(ins)
                continue

            ins_next2 = getInstructionAfter(ins_next)
            op_type = ins_next2.getOperandType(1)

            #Check third instruction: MOV [RSP + ..], STRING_SIZE
            if ins_next2.getMnemonicString() != "MOV" or ins_next2.getOpObjects(0)[0].toString() != "RSP" or OperandType.isScalar(op_type) is False:
                ins = getInstructionAfter(ins)
                continue

            address = ins.getPrimaryReference(1).getToAddress()
            length = ins_next2.getOpObjects(1)[0].getValue()

            try:
                #Create string.
                createAsciiString(address, length)
                #print "SUCCESS at %s" % address
            except:
                #print "ERROR at address %s" % ins.getAddress()
                ins = getInstructionAfter(ins)
                continue

            ins = getInstructionAfter(ins)

#ARM, 32-bit
#LDR REG, [STRING_ADDRESS_POINTER]
#STR REG, [SP, ..]
#MOV REG, STRING_SIZE
#STR REG, [SP, ..]

def string_rename_arm():
    for block in getMemoryBlocks():
        if block.getName() != ".text":
            continue
        start = block.getStart()
        #start = toAddr('00602238')

        ins = getInstructionAt(start)
        while ins:
            #print "INS at %s" % ins.getAddress()

            op_type = ins.getOperandType(1)
            #Check first instruction: LDR REG, [STRING_ADDRESS_POINTER]
            if ins.getMnemonicString() != "ldr" or ins.getRegister(0) is None or OperandType.isAddress(op_type) is False or OperandType.isScalar(op_type) is False:
                ins = getInstructionAfter(ins)
                #print "continue 1"
                continue

            reg = ins.getRegister(0)
            ins_next = getInstructionAfter(ins)

            #Check second instruction: STR REG, [SP + ..] (where REG is the same as in previous instruction)
            if ins_next.getMnemonicString() != "str" or ins_next.getRegister(0) != reg  or ins_next.getOpObjects(1)[0].toString() != "sp":
                ins = getInstructionAfter(ins)
                #print "continue 2"
                continue

            ins_next2 = getInstructionAfter(ins_next)
            op_type = ins_next2.getOperandType(1)

            #Check third instruction: MOV REG, STRING_SIZE
            if ins_next2.getMnemonicString() != "mov" or ins_next2.getRegister(0) is None or OperandType.isScalar(op_type) is False:
                ins = getInstructionAfter(ins)
                #print "continue 3"
                continue

            reg = ins_next2.getRegister(0) 
            ins_next3 = getInstructionAfter(ins_next2)


            #Check fourth instruction: STR REG, [SP + ..] (where REG is the same as in previous instruction)
            if ins_next3.getMnemonicString() != "str" or ins_next3.getRegister(0) != reg  or ins_next3.getOpObjects(1)[0].toString() != "sp":
                ins = getInstructionAfter(ins)
                #print "continue 4"
                continue

            #print "ins: %s" % ins
            address_pointer = getInt(ins.getPrimaryReference(1).getToAddress())
            address = currentProgram.getAddressFactory().getAddress(hex(address_pointer))
            length = ins_next2.getOpObjects(1)[0].getValue()

            if length == 0:
                ins = getInstructionAfter(ins)
                continue

            try:
                #Create string.
                #print "Creating string %s at %s" % (address, length)
                try:
                    for i in range(length):
                        removeDataAt(address.add(i))
                except:
                    #print "not remove at %s" % address
                    pass
                createAsciiString(address, length)
                print "SUCCESS at %s" % address
            except:
                print "ERROR at address %s" % ins.getAddress()
                #print error
                ins = getInstructionAfter(ins)
                #print "continue 5"
                continue

            ins = getInstructionAfter(ins)

#ARM, 64-bit - version 1
#ADRP REG, [STRING_ADDRESS_START]
#ADD REG, REG, INT
#STR REG, [SP, ..]
#ORR REG, REG, STRING_SIZE
#STR REG, [SP, ..]

#ARM, 64-bit - version 2
#ADRP REG, [STRING_ADDRESS_START]
#ADD REG, REG, INT
#STR REG, [SP, ..]
#MOV REG, STRING_SIZE
#STR REG, [SP, ..]

def string_rename_arm_64():
    for block in getMemoryBlocks():
        if block.getName() != ".text":
            continue
        start = block.getStart()
        ins = getInstructionAt(start)
        while ins:
            op_type = ins.getOperandType(1)
            reg = ins.getRegister(0)

            #Check first instruction: ADRP REG, [STRING_ADDRESS_START]
            if ins.getMnemonicString() != "adrp" or reg is None or OperandType.isScalar(op_type) is False:
                ins = getInstructionAfter(ins)
                continue

            ins_next = getInstructionAfter(ins)
            op_type = ins_next.getOperandType(2)

            #Check second instruction: ADD REG, REG, INT (where REG is the same as in previous instruction)
            if ins_next.getMnemonicString() != "add" or ins_next.getRegister(0) != reg or OperandType.isScalar(op_type) is False:
                ins = getInstructionAfter(ins)
                continue

            ins_next2 = getInstructionAfter(ins_next)

            #Check third instruction: STR REG, [SP + ..] (where REG is the same as in previous instruction)
            if ins_next2.getMnemonicString() != "str" or ins_next2.getRegister(0) != reg  or ins_next2.getOpObjects(1)[0].toString() != "sp":
                ins = getInstructionAfter(ins)
                continue

            ins_next3 = getInstructionAfter(ins_next2)
            reg = ins_next3.getRegister(0)

            #Check fourth instruction: ORR REG, REG, STRING_SIZE
            if ins_next3.getMnemonicString() == "orr" and reg is not None and OperandType.isScalar(ins_next3.getOperandType(2)) is True:
                length = ins_next3.getOpObjects(2)[0].getValue()
            #Check fourth instruction: MOV REG, STRING_SIZE
            elif ins_next3.getMnemonicString() == "mov" and reg is not None and OperandType.isScalar(ins_next3.getOperandType(1)) is True:
                length = ins_next3.getOpObjects(1)[0].getValue()
            else:
                ins = getInstructionAfter(ins)
                continue

            ins_next4 = getInstructionAfter(ins_next3)

            #Check fifth instruction: STR REG, [SP + ..] (where REG is the same as in previous instruction)
            if ins_next4.getMnemonicString() != "str" or ins_next4.getRegister(0) != reg  or ins_next4.getOpObjects(1)[0].toString() != "sp":
                ins = getInstructionAfter(ins)
                continue

            #print "ins: %s" % ins
            address_int = int(ins.getOpObjects(1)[0].getValue() + ins_next.getOpObjects(2)[0].getValue())
            address = currentProgram.getAddressFactory().getAddress(hex(address_int))
            
            try:
                #Create string.
                createAsciiString(address, length)
                #print "SUCCESS at %s" % address
            except:
                #print "ERROR at address %s" % ins.getAddress()
                ins = getInstructionAfter(ins)
                continue

            ins = getInstructionAfter(ins)

#Check program architecture.
language_id = currentProgram.getLanguageID()
print "lang: %s" % language_id
pointer_size = currentProgram.getDefaultPointerSize()

if language_id.toString().startswith("ARM"):
    print "32 BIT ARM"
    string_rename_arm()
elif language_id.toString().startswith("AARCH64"):
    print "64 BIT ARM"
    string_rename_arm_64()
elif language_id.toString().startswith("x86") and pointer_size == 4:
    print "32 BIT x86"
    string_rename_x86()
elif language_id.toString().startswith("x86") and pointer_size == 8:
    print "64 BIT x86"
    string_rename_x86_64()
else:
    print "ERROR: unknown arch."