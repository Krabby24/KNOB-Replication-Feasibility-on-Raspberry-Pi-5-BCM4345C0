#!/usr/bin/env python3
# hcd_to_bin.py
# Extracts RAM patch segments from a Broadcom .hcd firmware file
# and saves them as a flat binary for Ghidra analysis.
#
# Usage: python3 hcd_to_bin.py <input.hcd> <output.bin>

import sys
import struct

def hcd_to_bin(input_path, output_path):
    with open(input_path, 'rb') as f:
        data = f.read()

    segments = []
    i = 0
    while i < len(data) - 3:
        opcode = struct.unpack_from('<H', data, i)[0]
        length = data[i + 2]
        i += 3
        payload = data[i:i + length]
        i += length

        if opcode == 0xfc4c and length >= 4:
            address = struct.unpack_from('<I', payload, 0)[0]
            content = payload[4:]
            if content:
                segments.append((address, content))

    if not segments:
        print("[-] No segments found.")
        return

    segments.sort(key=lambda x: x[0])
    base_addr = segments[0][0]
    end_addr = segments[-1][0] + len(segments[-1][1])
    total_size = end_addr - base_addr

    binary = bytearray(total_size)
    for address, content in segments:
        offset = address - base_addr
        binary[offset:offset + len(content)] = content

    with open(output_path, 'wb') as f:
        f.write(binary)

    print(f"[+] Extracted {len(segments)} segments")
    print(f"[+] Base address: 0x{base_addr:08X}")
    print(f"[+] End address:  0x{end_addr:08X}")
    print(f"[+] Size: {total_size} bytes ({total_size // 1024} KB)")
    print(f"[+] Output: {output_path}")
    print()
    print("[!] Note: This binary contains RAM patches only, NOT the ROM.")
    print("[!] Load in Ghidra as Raw Binary, ARM:LE:32:v7, base address 0x{:08X}".format(base_addr))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.hcd> <output.bin>")
        sys.exit(1)
    hcd_to_bin(sys.argv[1], sys.argv[2])
