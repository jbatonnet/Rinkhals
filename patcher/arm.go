package main

import (
	"fmt"
)

// ARM32 Instruction Encoders

// Branch computes an ARM32 unconditional branch (B) instruction 
// from a source address (PC) to a target address
func Branch(sourceAddr, targetAddr uint64) uint32 {
	return generateBranchInstruction(0xEA000000, sourceAddr, targetAddr)
}

// BranchLink computes an ARM32 branch with link (BL) instruction
func BranchLink(sourceAddr, targetAddr uint64) uint32 {
	return generateBranchInstruction(0xEB000000, sourceAddr, targetAddr)
}

// BranchEqual computes an ARM32 branch equal (BEQ) instruction
func BranchEqual(sourceAddr, targetAddr uint64) uint32 {
	return generateBranchInstruction(0x0A000000, sourceAddr, targetAddr)
}

// BranchNotEqual computes an ARM32 branch not equal (BNE) instruction
func BranchNotEqual(sourceAddr, targetAddr uint64) uint32 {
	return generateBranchInstruction(0x1A000000, sourceAddr, targetAddr)
}

func generateBranchInstruction(opcode uint32, sourceAddr, targetAddr uint64) uint32 {
	// In ARM state, the PC reads as the current instruction address + 8 bytes
	pc := int32(sourceAddr) + 8
	offset := int32(targetAddr) - pc

	// Hardware shifts the offset left by 2 when branching, 
	// so we shift right by 2 to encode it
	imm24 := (offset >> 2) & 0x00FFFFFF

	return opcode | uint32(imm24)
}

// AddrToOffset converts a runtime Virtual Memory Address (VMA) 
// to a physical file offset in the ELF.
func (p *Patcher) AddrToOffset(vma uint64) (uint64, error) {
	for _, prog := range p.elfFile.Progs {
		if prog.Type != 1 { // PT_LOAD
			continue
		}
		
		if vma >= prog.Vaddr && vma < prog.Vaddr+prog.Memsz {
			return prog.Off + (vma - prog.Vaddr), nil
		}
	}
	return 0, fmt.Errorf("address 0x%x not found in any loadable segment", vma)
}

// ARM32 Instruction Builders

// MovRc_Imm builds a "mov Rdest, #imm" instruction (for small imm)
func MovRc_Imm(destReg uint32, imm uint32) uint32 {
	return 0xE3A00000 | (destReg << 12) | (imm & 0xFF)
}

// LdrR0_Pc builds a "ldr r0, [pc]" instruction
func LdrR0_Pc() uint32 {
	return 0xE59F0000
}

// MovPc_Lr builds a "mov pc, lr" instruction (return from subroutine)
func MovPc_Lr() uint32 {
	return 0xE1A0F00E
}

// CmpR0_Imm builds a "cmp r0, #imm" instruction
func CmpR0_Imm(imm uint32) uint32 {
	return 0xE3500000 | (imm & 0xFF)
}

// Cmp_Imm builds a "cmp rx, #imm" instruction
func Cmp_Imm(reg uint8, imm uint32) uint32 {
	return 0xE3500000 | (uint32(reg&0xf) << 16) | (imm & 0xFF)
}

// MovReg_Reg builds a "mov Rdest, Rsrc" instruction
func MovReg_Reg(destReg uint8, srcReg uint8) uint32 {
	return 0xE1A00000 | (uint32(destReg&0xf) << 12) | (uint32(srcReg&0xf))
}
