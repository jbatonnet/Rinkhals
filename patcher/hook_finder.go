package main

import (
	"fmt"
)

// HookTarget describes where we will inject our jump
type HookTarget struct {
	Address                uint64
	ReturnAddress          uint64
	SetCurrentIndexAddress uint64
	ThisInstructions       []uint32
	IsS1Mode               bool
	S1RowRegister          string
}

// FindHookTargets generically discovers all valid UI hook injection sites
func (p *Patcher) FindHookTargets() ([]*HookTarget, error) {
	// Candidate callback functions
	candidates := []struct {
		Symbol string
		IsS1   bool
	}{
		{"_ZZN10MainWindow26AcSettingGeneralPageUiInitEvENKUlRK11QModelIndexE0_clES2_", true}, // KS1 General Page
		{"_ZZN10MainWindow21AcSettingDeviceUiInitEvENKUlRK11QModelIndexE0_clES2_", true},      // KS1 Device Page
		{"_ZZN10MainWindow19AcSettingPageUiInitEvENKUlvE_clEv", false},
		{"_ZN10MainWindow23AcSettingListBtnReleaseEi", false}, // K2P
	}

	var results []*HookTarget

	displayStatusBar, _, _ := p.FindSymbol("_ZN10MainWindow24BottomStatusBarUiDisplayEh")
	if displayStatusBar == 0 {
		displayStatusBar = p.FindPltSymbol("_ZN10MainWindow24BottomStatusBarUiDisplayEh")
	}
	qStackedWidgetSetCurrentIndex, _, _ := p.FindSymbol("_ZN14QStackedWidget15setCurrentIndexEi")
	if qStackedWidgetSetCurrentIndex == 0 {
		qStackedWidgetSetCurrentIndex = p.FindPltSymbol("_ZN14QStackedWidget15setCurrentIndexEi")
	}

	for _, cand := range candidates {
		addr, fnSize, err := p.FindSymbol(cand.Symbol)
		if err != nil || addr == 0 {
			continue // Symbol not in this firmware
		}

		callbackAddr := addr
		callbackSize := fnSize
		isS1 := cand.IsS1

		offset, err := p.AddrToOffset(callbackAddr)
		if err != nil {
			continue
		}

		s := NewScanner(p.fileData)

		var patchJumpAddress uint64
		var patchReturnAddress uint64
		var thisInstructions []uint32

		var foundBl uint64
		var foundBls []uint64

		maxScan := offset + callbackSize

		for cur := offset; cur < maxScan; cur += 4 {
			inst := s.ReadInstruction(cur)
			vma := callbackAddr + (cur - offset)

			if displayStatusBar != 0 && inst == BranchLink(vma, displayStatusBar) {
				foundBls = append(foundBls, cur)
			}
			// Some models jump right to setCurrentIndex if displayStatusBar isn't used
			if qStackedWidgetSetCurrentIndex != 0 && inst == BranchLink(vma, qStackedWidgetSetCurrentIndex) {
				foundBls = append(foundBls, cur)
			}
		}

		if len(foundBls) > 0 {
			if isS1 {
				foundBl = foundBls[len(foundBls)-1]
			} else {
				foundBl = foundBls[0]
			}
		}

		if foundBl != 0 {
			patchJumpAddress = callbackAddr + (foundBl - offset)
			patchReturnAddress = patchJumpAddress + 4

			// 1. Try to find the 'this' pointer stored on the stack first
			strInstructionOffset := p.FindStrR0Fp(offset, 20)
			if strInstructionOffset != 0 {
				strInstruction := s.ReadInstruction(strInstructionOffset)
				thisOffset := strInstruction & 0xFFF
				thisInstructions = []uint32{
					0xE51B0000 | thisOffset, // ldr r0, [fp, #-offset]
					0xE5900000,              // ldr r0, [r0]
				}
			}

			// 2. Fall back to finding 'mov r0, r4' (or r5/r6) where 'this' is parked.
			if len(thisInstructions) == 0 {
				searchBl := foundBls[0] // Typically look before the FIRST bl (usually displayStatusBar)
				for i := 1; i <= 10; i++ {
					prevAddr := searchBl - uint64(i*4)
					inst := s.ReadInstruction(prevAddr)

					// If it's mov r0, rx
					if (inst & 0xFFFFFF00) == 0xE1A00000 {
						thisInstructions = append(thisInstructions, inst)
						break
					}
					// If it's ldr r0, [...]
					if (inst&0xFFF00000) == 0xE5900000 || (inst&0xFFF00000) == 0xE5100000 {
						thisInstructions = append(thisInstructions, inst)
						break
					}
				}
			}

			if len(thisInstructions) > 0 {
				var s1RowRegister string = "r1"

				results = append(results, &HookTarget{
					Address:                patchJumpAddress,
					SetCurrentIndexAddress: qStackedWidgetSetCurrentIndex,
					ReturnAddress:          patchReturnAddress,
					ThisInstructions:       thisInstructions,
					IsS1Mode:               isS1,
					S1RowRegister:          s1RowRegister,
				})
			}
		}
	}

	if len(results) == 0 {
		return nil, fmt.Errorf("could not find any valid hook targets in the UI button callbacks")
	}

	return results, nil
}

// FindStrR0Fp searches for "str r0, [fp, #-xx]"
func (p *Patcher) FindStrR0Fp(start uint64, maxInst int) uint64 {
	s := NewScanner(p.fileData)
	for cur := start; cur < start+uint64(maxInst*4); cur += 4 {
		inst := s.ReadInstruction(cur)
		if (inst & 0xFFFFF000) == 0xE50B0000 {
			return cur
		}
	}
	return 0
}

func (p *Patcher) FindPltSymbol(name string) uint64 {
	syms, err := p.elfFile.DynamicSymbols()
	if err != nil {
		return 0
	}
	var symIdx int = -1
	for i, s := range syms {
		if s.Name == name {
			symIdx = i + 1
			break
		}
	}
	if symIdx == -1 {
		return 0
	}

	plt := p.elfFile.Section(".plt")
	if plt == nil {
		return 0
	}

	relPlt := p.elfFile.Section(".rel.plt")
	if relPlt != nil {
		data, _ := relPlt.Data()
		for i := 0; i < len(data); i += 8 {
			info := uint32(data[i+4]) | uint32(data[i+5])<<8 | uint32(data[i+6])<<16 | uint32(data[i+7])<<24
			idx := int(info >> 8)
			if idx == symIdx {
				return plt.Addr + 20 + uint64(i/8)*12
			}
		}
	}
	return 0
}
