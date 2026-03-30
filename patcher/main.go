package main

import (
	"bytes"
	"debug/elf"
	"encoding/binary"
	"flag"
	"fmt"
	"log"
	"os"
)

// Patcher contains the context for our binary patching operation
type Patcher struct {
	binaryPath string
	fileData   []byte
	elfFile    *elf.File
}

func main() {
	var targetBinary string
	var dryRun bool
	flag.StringVar(&targetBinary, "binary", "", "Path to the K3SysUi binary")
	flag.BoolVar(&dryRun, "dry-run", false, "Perform all analysis but do not save back to disk")
	flag.Parse()

	if targetBinary == "" {
		log.Fatal("Must provide a --binary path")
	}

	log.Printf("Starting dynamic patch for Rinkhals UI...")

	p, err := NewPatcher(targetBinary)
	if err != nil {
		log.Fatalf("Failed to initialize patcher: %v", err)
	}
	defer p.Close()

	if bytes.Contains([]byte(targetBinary), []byte("gkapi")) {
		log.Printf("Detected gkapi binary, applying gkapi patches...")
		err = p.PatchGkapi()
		if err != nil {
			if err.Error() == "already patched" {
				log.Printf("gkapi binary is already patched. Skipping.")
				return
			}
			log.Printf("Warning: Failed to patch gkapi (may not be supported/needed on this firmware): %v", err)
			return
		}
	} else {
		log.Printf("Detected K3SysUi binary, applying UI patches...")

		if p.IsAlreadyPatchedUI() {
			log.Printf("K3SysUi binary is already patched. Skipping.")
			return
		}

		// 1. Strings Replacement: Change "Customer Support" / "Service Support" to "Rinkhals"
		err = p.PatchRodataString("Customer Support", "Rinkhals")
		if err != nil {
			log.Printf("Warning: 'Customer Support' string patch failed: %v", err)
		} else {
			log.Printf("Successfully replaced 'Customer Support' with 'Rinkhals'")
		}

		err = p.PatchRodataString("Service Support", "Rinkhals")
		if err != nil {
			log.Printf("Warning: 'Service Support' string patch failed: %v", err)
		} else {
			log.Printf("Successfully replaced 'Service Support' with 'Rinkhals'")
		}

		// Step 2: Locate payload injection site and write string data
		space, err := p.SetupPayloadSpace()
		if err != nil {
			log.Fatalf("Failed to setup payload space in AcSupportRefreshEv: %v", err)
		}

		// Step 3: Locate button callback functions dynamically
		hookInfos, err := p.FindHookTargets()
		if err != nil {
			log.Fatalf("Failed to dynamically locate hook targets: %v", err)
		}

		for _, hookInfo := range hookInfos {
			log.Printf("Found Hook Injection Site at 0x%x", hookInfo.Address)

			// Step 4: Generate Payload & Branches
			payloadStart, err := p.BuildPayload(space, hookInfo.ReturnAddress, hookInfo.IsS1Mode, hookInfo.S1RowRegister, hookInfo.ThisInstructions, hookInfo.SetCurrentIndexAddress)
			if err != nil {
				log.Fatalf("Failed to build assembly payload: %v", err)
			}

			// Branch from hook location to our payload
			hookOff, _ := p.AddrToOffset(hookInfo.Address)
			p.Write32(hookOff, Branch(hookInfo.Address, payloadStart))
		}
	}

	if !dryRun {
		tmpFile := targetBinary + ".patched.tmp"
		finalFile := targetBinary + ".patched"
		err = os.WriteFile(tmpFile, p.fileData, 0755)
		if err != nil {
			log.Fatalf("Failed to write temporary patched binary: %v", err)
		}
		err = os.Rename(tmpFile, finalFile)
		if err != nil {
			os.Remove(tmpFile)
			log.Fatalf("Failed to verify atomic write (rename failed): %v", err)
		}
		log.Printf("Patched binary saved to %s", finalFile)
	} else {
		log.Printf("Dry run complete. No files written.")
	}
}

// NewPatcher loads the ELF binary and prepares it for modification
func NewPatcher(path string) (*Patcher, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read file: %w", err)
	}

	f, err := elf.NewFile(bytes.NewReader(data))
	if err != nil {
		return nil, fmt.Errorf("parse ELF: %w", err)
	}

	return &Patcher{
		binaryPath: path,
		fileData:   data,
		elfFile:    f,
	}, nil
}

// Close closes the underlying ELF file
func (p *Patcher) Close() {
	if p.elfFile != nil {
		p.elfFile.Close()
	}
}

// FindSymbol finds the remote address of a given symbol by its name
func (p *Patcher) FindSymbol(name string) (uint64, uint64, error) {
	syms, err := p.elfFile.Symbols()
	if err != nil {
		syms, err = p.elfFile.DynamicSymbols()
		if err != nil {
			return 0, 0, fmt.Errorf("failed to read symbols: %w", err)
		}
	}

	for _, s := range syms {
		if s.Name == name {
			return s.Value, s.Size, nil
		}
	}
	return 0, 0, fmt.Errorf("symbol %q not found", name)
}

// PatchRodataString searches the .rodata section for an exact string and replaces it
func (p *Patcher) PatchRodataString(oldStr, newStr string) error {
	rodata := p.elfFile.Section(".rodata")
	if rodata == nil {
		return fmt.Errorf("could not find .rodata section")
	}

	if len(newStr) > len(oldStr) {
		return fmt.Errorf("new string cannot be larger than old string")
	}

	start := rodata.Offset
	end := rodata.Offset + rodata.Size

	oldBytes := append([]byte(oldStr), 0)
	newBytes := append([]byte(newStr), 0)

	idx := bytes.Index(p.fileData[start:end], oldBytes)
	if idx == -1 {
		return fmt.Errorf("string '%s' not found", oldStr)
	}

	targetOffset := start + uint64(idx)

	// Copy the new string in (and pad the rest with null bytes up to the old string length)
	copy(p.fileData[targetOffset:], newBytes)
	for i := len(newBytes); i < len(oldBytes); i++ {
		p.fileData[targetOffset+uint64(i)] = 0
	}

	return nil
}

// Write32 writes a 32-bit uint in LittleEndian format at the specified file offset
func (p *Patcher) Write32(offset uint64, val uint32) {
	binary.LittleEndian.PutUint32(p.fileData[offset:offset+4], val)
}

// IsAlreadyPatchedUI checks if the K3SysUi binary has already been patched
func (p *Patcher) IsAlreadyPatchedUI() bool {
	rodata := p.elfFile.Section(".rodata")
	if rodata == nil {
		return false
	}

	start := rodata.Offset
	end := rodata.Offset + rodata.Size

	oldBytes := append([]byte("Customer Support"), 0)
	newBytes := append([]byte("Rinkhals"), 0)
	paddedBytes := make([]byte, len(oldBytes))
	copy(paddedBytes, newBytes)

	return bytes.Index(p.fileData[start:end], oldBytes) == -1 && bytes.Index(p.fileData[start:end], paddedBytes) != -1
}
