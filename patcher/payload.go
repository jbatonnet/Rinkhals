package main

import (
	"fmt"
)

// PayloadSpace holds the virtual memory addresses of our injected data
type PayloadSpace struct {
	BaseAddress     uint64
	StartUiStr      uint64
	WaitUiStr       uint64
	CleanPidStr     uint64
	AssemblyStart   uint64
}

// SetupPayloadSpace finds AcSupportRefreshEv, neuters it, and writes our strings
func (p *Patcher) SetupPayloadSpace() (*PayloadSpace, error) {
	// Find the function to neuter and hijack
	acSupportSymbol := "_ZN10MainWindow16AcSupportRefreshEv"
	acSupportAddr, _, err := p.FindSymbol(acSupportSymbol)
	if err != nil {
		return nil, fmt.Errorf("could not find %s: %w", acSupportSymbol, err)
	}

	offset, err := p.AddrToOffset(acSupportAddr)
	if err != nil {
		return nil, err
	}

	// Make the original function return immediately (mov pc, lr)
	p.Write32(offset, MovPc_Lr())

	freeSpaceOffset := offset + 4
	freeSpaceAddr := acSupportAddr + 4

	space := &PayloadSpace{
		BaseAddress: acSupportAddr,
	}

	// 1. Write the Rinkhals UI start command
	startUi := []byte("/useremain/rinkhals/.current/opt/rinkhals/ui/rinkhals-ui.sh & echo $! > /tmp/rinkhals/rinkhals-ui.pid\x00")
	space.StartUiStr = freeSpaceAddr
	copy(p.fileData[freeSpaceOffset:], startUi)
	
	freeSpaceOffset += uint64(len(startUi))
	freeSpaceAddr += uint64(len(startUi))

	// 2. Write the wait command
	waitUi := []byte("timeout -t 2 strace -qqq -e trace=none -p $(cat /tmp/rinkhals/rinkhals-ui.pid) 2> /dev/null\x00")
	space.WaitUiStr = freeSpaceAddr
	copy(p.fileData[freeSpaceOffset:], waitUi)
	
	freeSpaceOffset += uint64(len(waitUi))
	freeSpaceAddr += uint64(len(waitUi))

	// 3. Write the clean pid command
	cleanPid := []byte("rm -f /tmp/rinkhals/rinkhals-ui.pid\x00")
	space.CleanPidStr = freeSpaceAddr
	copy(p.fileData[freeSpaceOffset:], cleanPid)

	freeSpaceAddr += uint64(len(cleanPid))
	
	// Align to 4 bytes for assembly instructions
	space.AssemblyStart = (freeSpaceAddr + 3) &^ 3

	return space, nil
}
