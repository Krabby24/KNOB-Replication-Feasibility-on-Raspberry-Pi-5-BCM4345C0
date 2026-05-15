# KNOB Attack on Raspberry Pi 5 — BCM4345C0
> CVE-2019-9506 | Bluetooth BR/EDR Key Negotiation Attack  
> Security of Advanced Networking and Services — Master's Course Project  
> Authors: **Marco** & **Riccardo Citron**

---

## Overview

This project implements and demonstrates the **KNOB attack (Key Negotiation Of Bluetooth)** on the Cypress BCM4345C0 chip, as found in the Raspberry Pi 3+, 4, and 5.

The KNOB attack forces two Bluetooth BR/EDR devices to negotiate an encryption key with only **1 byte (8 bits) of entropy**, reducing the brute-force keyspace to 256 possible keys. The attack operates at the LMP layer — before the host stack is involved — making it transparent to both victim devices.

**Attack platform:** Raspberry Pi 5 (BCM4345C0, chip ID 0x6119)  
**Framework:** [InternalBlue](https://github.com/seemoo-lab/internalblue)  
**Reference:** [KNOB Attack — USENIX Security 2019](https://knobattack.com)

---

## Repository Structure

```
knob-attack-rpi5/
├── README.md               # This file
├── PROGRESS.md             # Session-by-session progress log
├── .gitignore
├── src/
│   ├── KNOB_PoC_BCM4345C0.py     # Main PoC script (Phase 2)
│   └── knob_sendlmp.py           # sendlmp-based attack script
├── docs/
│   ├── firmware_analysis.md      # BCM4345C0 memory map findings
│   └── vulnerability_table.md   # Tested devices and results
├── captures/               # btmon .pcap captures (gitignored)
└── tools/
    └── hcd_to_bin.py       # HCD firmware extraction utility
```

---

## Roadmap

### Phase 0 — Environment Setup ✅ COMPLETED
- Raspberry Pi 5 setup, InternalBlue installation
- Python 3.13 compatibility fixes applied
- RAM read/write verified (`hexdump`, `writemem` confirmed working)
- Chip confirmed: BCM4345C0, Cypress Semiconductor, HCI 5.0

### Phase 1 — Firmware Analysis ⚠️ PARTIALLY COMPLETED
- ROM dump attempted — blocked by hardware protection on RPi 5
- Firmware downgrade to pre-Spectra attempted — ROM still inaccessible
- **Original finding:** key length field offset within connection struct = `+0xA7`
- **Original finding:** key length address for active connection = `0x204C4F` (Array Index 0)
- Global entropy variable: not found (requires ROM access)
- See `PROGRESS.md` and `docs/firmware_analysis.md` for full details

### Phase 2 — PoC Development 🔄 IN PROGRESS
- Write `KNOB_PoC_BCM4345C0.py` using `sendlmp` approach
- Adapted from HCICore instead of ADBCore (RPi uses BlueZ, not Android)

### Phase 3 — Attack Execution ⏳ NOT STARTED
- Test against multiple target devices
- Capture LMP traffic with `btmon`
- Build vulnerability table

### Phase 4 — E0 Brute Force ⏳ NOT STARTED
- Compile `e0/` module from francozappa/knob
- Brute-force session key from captured pcap
- Demonstrate traffic decryption

### Phase 5 — Original Contribution ⏳ NOT STARTED
- Extended vulnerability table (devices not in original paper)
- BLE variant test
- BCM4345C0 memory map documentation

### Phase 6 — Documentation & Repo ⏳ NOT STARTED
- Complete README, demo video, final report
- Make repository public

---

## Hardware & Environment

| Component | Details |
|---|---|
| Attack device | Raspberry Pi 5 |
| Bluetooth chip | Cypress CYW43455 (BCM4345C0) |
| Chip ID | 0x6119 (003.001.025) |
| HCI Version | 5.0 |
| BD Address | 88:A2:9E:9D:7C:29 |
| RPi OS | Raspberry Pi OS Bookworm (64-bit) |
| Python | 3.13 (with compatibility patches) |
| InternalBlue | ~/internalblue/ (venv) |

---

## Key Technical Findings — BCM4345C0

| Finding | Value | Status |
|---|---|---|
| `CONNECTION_ARRAY_ADDRESS` | `0x204BA8` | Known (fw_0x6119.py) |
| `CONNECTION_STRUCT_LENGTH` | `0x150` | Known (fw_0x6119.py) |
| Key length field offset in struct | `+0xA7` | **Found by us** |
| Key length address (Array Index 0) | `0x204C4F` | **Found by us** |
| `lmulp_sendLcp` address | `0x92062` | Known (fw_0x6119.py) |
| Global entropy variable | Unknown | ROM required |
| `lm_SendLmpEncryptKeySizeReq` address | Unknown | ROM required |

---

## BCM4345C0 ROM Access — Known Limitation

The RPi 5 hardware prevents ROM reading via InternalBlue regardless of firmware version. Both the current firmware and a pre-Spectra downgrade were tested — ROM reads time out at the HCI level. This appears to be a hardware-level protection not present on RPi 3+ or RPi 4. A ROM dump from one of those devices would contain identical ROM content and could be used to find the remaining addresses.

---

## References

- [KNOB Attack Paper — USENIX 2019](https://www.usenix.org/conference/usenixsecurity19/presentation/antonioli)
- [francozappa/knob — Original PoC](https://github.com/francozappa/knob)
- [seemoo-lab/internalblue](https://github.com/seemoo-lab/internalblue)
- [Polypyus — Binary Diffing Tool](https://github.com/seemoo-lab/polypyus)
