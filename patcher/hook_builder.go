package main

import (
	"encoding/binary"
	"fmt"
)

// EmitSystemCall writes the ARM instructions to call system() with a specific string.
// Generates:
//
//	ldr r0, [pc]
//	b   +8
//	.word stringAddr
//	bl  systemAddr
//
// Returns the next available address
func (p *Patcher) EmitSystemCall(address, stringAddr, systemAddr uint64) (uint64, error) {
	offset, err := p.AddrToOffset(address)
	if err != nil {
		return 0, err
	}

	// 1. ldr r0, [pc] (which reads from address + 8)
	p.Write32(offset, LdrR0_Pc())

	// 2. b +8 (skip the data word) -> target is address + 12
	p.Write32(offset+4, Branch(address+4, address+12))

	// 3. .word stringAddr
	binary.LittleEndian.PutUint32(p.fileData[offset+8:offset+12], uint32(stringAddr))

	// 4. bl systemAddr
	p.Write32(offset+12, BranchLink(address+12, systemAddr))

	return address + 16, nil
}

// BuildPayload writes the main hook assembly logic into the free space
// and returns the starting address of the hook.
func (p *Patcher) BuildPayload(space *PayloadSpace, returnAddr uint64, isS1 bool, s1RowRegister string, thisInstructions []uint32, setCurrentIndexAddress uint64) (uint64, error) {
	system, _, err := p.FindSymbol("system")
	if system == 0 {
		system = p.FindPltSymbol("system")
	}
	if system == 0 {
		return 0, fmt.Errorf("system symbol not found in PLT or symtab")
	}

	osSleep, _, err := p.FindSymbol("_ZN8GobalVar7OsSleepEi")
	if osSleep == 0 {
		osSleep = p.FindPltSymbol("_ZN8GobalVar7OsSleepEi")
	}
	if osSleep == 0 {
		return 0, fmt.Errorf("osSleep symbol not found")
	}

	acDisplayWaitHandler, _, err := p.FindSymbol("_ZN10MainWindow20AcDisplayWaitHandlerEhh")
	if err != nil {
		return 0, err
	}

	// K3 series uses one AcDisplayWaitHide (no args), KS series might use different ones,
	// but we'll try to find any matching WaitHide
	acDisplayWaitHide, _, err := p.FindSymbol("_ZN10MainWindow17AcDisplayWaitHideEv")
	if err != nil {
		acDisplayWaitHide, _, _ = p.FindSymbol("_ZN10MainWindow17AcDisplayWaitHideEh")
	}

	address := space.AssemblyStart

	// Push r0, r1 tightly (r0 is QStackedWidget*, r1 is index)
	// e92d0003 = push {r0, r1}
	off, _ := p.AddrToOffset(address)
	p.Write32(off, 0xe92d0003)
	address += 4

	// If we are on KS1 / KS1M, check the row index
	if isS1 {
		// mov r0, r4
		off, _ = p.AddrToOffset(address)
		p.Write32(off, MovReg_Reg(0, 4))
		address += 4

		// cmp <s1RowRegister>, #0x3
		s1RowRegMap := map[string]uint8{"r1": 1, "r2": 2, "r3": 3, "r4": 4, "r5": 5}
		regIdx := uint8(1) // default to r1
		if val, ok := s1RowRegMap[s1RowRegister]; ok {
			regIdx = val
		}

		off, _ = p.AddrToOffset(address)
		p.Write32(off, Cmp_Imm(regIdx, 0x3))
		address += 4

		// bne <patchReturnAddress - 4>
		off, _ = p.AddrToOffset(address)
		// The python script does patchReturnAddress - 4, which is effectively returning BEFORE the instruction that was skipped,
		// but since we pushed {r0,r1} we MUST pop {r0,r1} first if we are abandoning.
		// Wait, if we return early we MUST pop our stack frame. Let's redirect to a pop block.
		// Actually, let's just assemble a pop and return right here if not equal.

		// BNE to the normal logic if it IS equal? No, BNE means "if not equal, skip the rinkhals launch".
		// We'll jump forward to the POP/return logic for S1.

		// For simplicity, let's jump to the pop {r0, r1} instruction near the end.
		// Actually, it's safer to pop here and return immediately.

		p.Write32(off, BranchEqual(address, address+16)) // if EQUAL (it is row 3), skip the abort block
		address += 4

		// This block executes IF NOT EQUAL (meaning we don't handle it, e.g. row != 3)
		// pop {r0, r1}
		off, _ = p.AddrToOffset(address)
		p.Write32(off, 0xe8bd0003)
		address += 4

		// we overwrote the original bl setCurrentIndex, so we must call it here for normal tabs
		off, _ = p.AddrToOffset(address)
		p.Write32(off, BranchLink(address, setCurrentIndexAddress))
		address += 4

		// b returnAddr
		off, _ = p.AddrToOffset(address)
		p.Write32(off, Branch(address, returnAddr))
		address += 4
	}

	var errs error
	// system("/useremain/.../rinkhals-ui.sh ...")
	address, errs = p.EmitSystemCall(address, space.StartUiStr, system)
	if errs != nil {
		return 0, errs
	}

	loopAddress := address

	// OsSleep(100)
	// mov r0, #0x64 (100)
	// bl osSleep
	off, _ = p.AddrToOffset(address)
	p.Write32(off, MovRc_Imm(0, 100))
	p.Write32(off+4, BranchLink(address+4, osSleep))
	address += 8

	// code = system("timeout -t 2 ...")
	address, errs = p.EmitSystemCall(address, space.WaitUiStr, system)
	if errs != nil {
		return 0, errs
	}

	// cmp r0, #15
	// beq loopAddress
	off, _ = p.AddrToOffset(address)
	p.Write32(off, CmpR0_Imm(15))
	p.Write32(off+4, BranchEqual(address+4, loopAddress))
	address += 8

	// system("rm -f .../rinkhals-ui.pid")
	address, errs = p.EmitSystemCall(address, space.CleanPidStr, system)
	if errs != nil {
		return 0, errs
	}

	// this->AcDisplayWaitHandler(1, 4)
	if acDisplayWaitHandler != 0 {
		off, _ = p.AddrToOffset(address)
		for i, inst := range thisInstructions {
			p.Write32(off+uint64(i*4), inst)
		}
		address += uint64(len(thisInstructions) * 4)

		off, _ = p.AddrToOffset(address)
		p.Write32(off+0, MovRc_Imm(2, 4))
		p.Write32(off+4, MovRc_Imm(1, 1))
		p.Write32(off+8, BranchLink(address+8, acDisplayWaitHandler))
		address += 12
	}

	if acDisplayWaitHide != 0 {
		off, _ = p.AddrToOffset(address)
		for i, inst := range thisInstructions {
			p.Write32(off+uint64(i*4), inst)
		}
		address += uint64(len(thisInstructions) * 4)

		off, _ = p.AddrToOffset(address)
		// Need to decide whether to pass 0 or 4 based on K2P vs others. In general, 0 works for K2P, 4 for others
		// But passing 4 as r1 works as an argument for WaitHideEh (S1). K2P needs r1 = 0 when using WaitHandler to hide.
		if acDisplayWaitHide == acDisplayWaitHandler {
			p.Write32(off, MovRc_Imm(1, 0)) // K2P hide equivalent: r1 = 0
		} else {
			p.Write32(off, MovRc_Imm(1, 4)) // KS1 wait hide parameter
		}
		p.Write32(off+4, BranchLink(address+4, acDisplayWaitHide))
		address += 8
	}
	off, _ = p.AddrToOffset(address)
	p.Write32(off, 0xe8bd0003)
	address += 4

	// Branch back to return address
	off, _ = p.AddrToOffset(address)
	p.Write32(off, Branch(address, returnAddr))

	return space.AssemblyStart, nil
}
