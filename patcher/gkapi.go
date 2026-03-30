package main

import (
	"bytes"
	"debug/elf"
	"debug/gosym"
	"encoding/binary"
	"fmt"
	"log"
)

func (p *Patcher) PatchGkapi() error {
	exe, err := elf.NewFile(bytes.NewReader(p.fileData))
	if err != nil {
		return err
	}
	defer exe.Close()

	var pclndata []byte
	if sec := exe.Section(".gopclntab"); sec != nil {
		pclndata, _ = sec.Data()
	} else {
		return fmt.Errorf("no .gopclntab section")
	}

	var symtab []byte
	var text uint64
	if sec := exe.Section(".symtab"); sec != nil {
		symtab, _ = sec.Data()
	}
	if sec := exe.Section(".text"); sec != nil {
		text = sec.Addr
	}

	pcln := gosym.NewLineTable(pclndata, text)
	tab, err := gosym.NewTable(symtab, pcln)
	if err != nil {
		return err
	}

	funcsByName := make(map[string]uint64)
	for _, f := range tab.Funcs {
		if f.Sym != nil {
			funcsByName[f.Sym.Name] = f.Entry
		}
	}

	// Change orcaSim (Octoprint compat API) to port 71
	// We replace the reference to :80 by a reference to :71 (from localhost:7125)
	moonrakerString := []byte("localhost:7125")
	idx := bytes.Index(p.fileData, moonrakerString)
	if idx == -1 {
		return fmt.Errorf("could not find 'localhost:7125' string")
	}

	// Calculate VMA of the string
	var stringVma uint64
	for _, sec := range exe.Sections {
		if sec.Type == elf.SHT_PROGBITS && uint64(idx) >= sec.Offset && uint64(idx) < sec.Offset+sec.Size {
			stringVma = sec.Addr + uint64(idx) - sec.Offset
			break
		}
	}

	if stringVma == 0 {
		return fmt.Errorf("could not find VMA for 'localhost:7125' string")
	}

	orcaSimStart, ok := funcsByName["printerApi/service/orcaSim.Start"]
	if !ok {
		return fmt.Errorf("could not find printerApi/service/orcaSim.Start in go symtab")
	}

	startOff, err := p.AddrToOffset(orcaSimStart)
	if err != nil {
		return err
	}

	// Search for stringVma reference within the first 800 bytes (200 ops)
	var moonrakerOffset uint64
	for i := uint64(0); i < 200; i++ {
		if startOff+i*4+4 > uint64(len(p.fileData)) {
			break
		}
		val := binary.LittleEndian.Uint32(p.fileData[startOff+i*4 : startOff+i*4+4])
		if uint64(val) == stringVma {
			moonrakerOffset = i * 4
			break
		}
	}

	if moonrakerOffset != 0 {
		patchOff := startOff + moonrakerOffset - 4

		currentVal := binary.LittleEndian.Uint32(p.fileData[patchOff : patchOff+4])
		if currentVal == uint32(stringVma+9) {
			return fmt.Errorf("already patched")
		}

		log.Printf("Found moonraker reference at orcaSim.Start+0x%x, patching for port 71...", moonrakerOffset)
		// Write stringVma + 9 (which points to "7125")
		p.Write32(patchOff, uint32(stringVma+9))
		log.Printf("Successfully changed orcaSim port definition")
	} else {
		log.Printf("Could not find moonraker reference in orcaSim.Start")
		return fmt.Errorf("moonraker string reference not found in orcaSim.Start")
	}

	return nil
}
