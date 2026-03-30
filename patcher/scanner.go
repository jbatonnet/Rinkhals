package main

import (
	"bytes"
	"fmt"
)

// Scanner is a helper to scan for byte patterns within a binary slice
type Scanner struct {
	data []byte
}

// NewScanner creates a new Scanner
func NewScanner(data []byte) *Scanner {
	return &Scanner{data: data}
}

// FindFirst searches for a literal byte pattern and returns the offset
func (s *Scanner) FindFirst(pattern []byte, start uint64, maxLen uint64) (uint64, error) {
	end := start + maxLen
	if end > uint64(len(s.data)) {
		end = uint64(len(s.data))
	}

	searchSlice := s.data[start:end]
	idx := bytes.Index(searchSlice, pattern)
	if idx == -1 {
		return 0, fmt.Errorf("pattern not found")
	}

	return start + uint64(idx), nil
}

// CheckInstruction returns a 32 bit ARM instruction at an offset
func (s *Scanner) ReadInstruction(offset uint64) uint32 {
	if offset+4 > uint64(len(s.data)) {
		return 0
	}
	// Little endian read
	return uint32(s.data[offset]) | uint32(s.data[offset+1])<<8 | uint32(s.data[offset+2])<<16 | uint32(s.data[offset+3])<<24
}
