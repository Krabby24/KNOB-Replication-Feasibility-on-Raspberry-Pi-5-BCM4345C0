# KNOB Attack on Raspberry Pi 5 — BCM4345C0
> CVE-2019-9506 | Bluetooth BR/EDR Key Negotiation Attack  
> Security of Advanced Networking and Services — Master's Course Project  
> Authors: **Marco Stocco** & **Riccardo Citron**

---

## Overview

This project implements and demonstrates the **KNOB attack (Key Negotiation Of Bluetooth)** on the Cypress BCM4345C0 chip, as found in the Raspberry Pi 3+, 4, and 5.

The KNOB attack forces two Bluetooth BR/EDR devices to negotiate an encryption key with only **1 byte (8 bits) of entropy**, reducing the brute-force keyspace to 256 possible keys. The attack operates at the LMP layer — before the host stack is involved — making it transparent to both victim devices and their operating systems.

**Attack platform:** Raspberry Pi 5 (BCM4345C0, chip ID 0x6119, firmware 003.001.025 build 0382)  
**Framework:** [InternalBlue](https://github.com/seemoo-lab/internalblue)  
**Reference:** [KNOB Attack — USENIX Security 2019](https://knobattack.com)

---

## Repository Structure

```
knob-attack-rpi5/
├── README.md                       # This file
├── PROGRESS.md                     # Session-by-session progress log
├── .gitignore
├── src/
│   └── KNOB_PoC_BCM4345C0.py       # Main PoC script
├── docs/
│   ├── firmware_analysis.md        # BCM4345C0 RAM map findings
│   └── vulnerability_table.md      # Tested devices and results
├── captures/                       # btmon/pcap captures (gitignored)
└── tools/
    └── hcd_to_bin.py               # HCD firmware extraction utility
```

---

## Roadmap

### Phase 0 — Environment Setup ✅ COMPLETED
- Raspberry Pi 5 setup, InternalBlue installation and Python 3.13 compatibility fixes
- RAM read/write verified (`hexdump`, `writemem` confirmed working)
- Chip confirmed: BCM4345C0, Cypress Semiconductor, HCI 5.0
- `min_encrypt_key_size` kernel parameter override confirmed working

### Phase 1 — Firmware Analysis ✅ COMPLETED
- ROM dump blocked by hardware protection on RPi 5 (Spectra mitigations prevent writeRAM in ROM range, error 0x12). RAM range 0x200000–0x227FFF fully readable.
- **Original finding:** key length field offset within connection struct = `+0xA7` (universally confirmed on all 5 tested devices)
- **Original finding:** `key_len_addr` for slot 0 (Samsung, iPhone) = `0x20557F`; slot 1 (iPhone 6S) = `0x2056CF`
- **Original finding:** complete BCM4345C0 connection struct RAM map — see `docs/firmware_analysis.md`
- Global entropy variable: not found (requires ROM access)

### Phase 2 — PoC Development ✅ COMPLETED
- `KNOB_PoC_BCM4345C0.py` written and functional
- Uses `writemem` to patch `effective_key_len` field at `slot_base + 0xA7`
- Tested against 5 real Bluetooth devices

### Phase 3 — Attack Execution ✅ COMPLETED
- KNOB attack demonstrated on **5 real devices** — see vulnerability table below
- LMP traffic captured with `btmon` for all sessions
- `Read Encryption Key Size` host blindness demonstrated (host reads 16, firmware uses 1)
- E0 encryption confirmed on all BR/EDR devices via btmon

### Phase 4 — Cryptographic Key Derivation 🔄 IN PROGRESS
- E1 verified: SRES and ACO computed from KL+AU_RAND+BTADD_S and confirmed against captured LMP_sres packets — **3 independent sessions**
- EN_RAND not extractable via software on BCM4345C0 — documented as original finding
- KC not persistently stored in accessible RAM after E3 computation — documented
- **Remaining:** complete K'C derivation using synthetic EN_RAND (following KNOB paper methodology, Section 4.3); generate all 256 K'C candidates for brute force demonstration

### Phase 5 — Original Contributions ✅ SUBSTANTIALLY COMPLETED
- Extended vulnerability table: 5 devices including **iPhone 16 Pro (2024)**, **MacBook 2022** and **iPad A16 2026**— not in original KNOB paper
- BCM4345C0 RAM map fully documented with cryptographic proof
- EN_RAND non-extractability documented as security finding
- AES-CCM vulnerability confirmed on modern Apple devices

### Phase 6 — Documentation & Repository ⏳ IN PROGRESS
- PROGRESS.md maintained session-by-session
- Final README, demo video, and public repository release pending Phase 4 completion

---

## Vulnerability Table

| Device | BD Address | Encryption | Vulnerable | `key_len_addr` | RPi Role | Notes |
|---|---|---|---|---|---|---|
| JBL Clip 2 | 40:EF:4C:8C:88:DF | E0 | ✅ | variable | Master | slot variable |
| Samsung Galaxy Ace Style 2014 | F8:84:F2:62:96:AA | E0 | ✅ | `0x20557F` | Slave | slot stable, KL stable |
| Samsung Galaxy A34 5G (2024) | AC:80:FB:21:85:32 | E0 | ✅ | `0x20557F` | Slave | slot stable |
| iPhone 6S | 00:B3:62:93:89:12 | E0 | ✅ | `0x2056CF` | Slave | slot 1 |
| **iPhone 16 Pro (2024)** | 90:B7:90:09:34:92 | AES-CCM | ✅ | `0x20557F` | Slave | **Secure Connections — original finding** |
| **MacBook 2022** | a8:8f:d9:35:0c:fe | AES-CCM | ✅ | `0x20557F` | Slave | **Secure Connections — original finding** |
| **iPad A16 (iPadOS 26)** | 30:C0:AE:2D:B4:BE | AES-CCM | ✅ | 0x20557F | Slave | **Secure Connections - original finding** |

---

## Original Findings — BCM4345C0

All findings below are original contributions not previously published for this chip.

### 1. Connection Struct RAM Map (cryptographically verified)

| Offset from `slot_base` | Size | Content |
|---|---|---|
| `+0x60` | 16B | KL (Link Key) |
| `+0x70` | 16B | AU_RAND |
| `+0x80` | 4B | SRES |
| `+0x84` | 12B | ACO |
| `+0xA7` | 1B | **Effective Key Length** ← attack target |

Verified with `SRES, ACO = E1(KL, AU_RAND, BTADD_S)` against 3 independent sessions. Full mathematical proof in `docs/firmware_analysis.md`.

### 2. Key Finding: `+0xA7` Offset Universal on BCM4345C0
The `effective_key_len` field is always at `slot_base + 0xA7` regardless of: remote device type, encryption mode (E0 or AES-CCM), master/slave role, iOS/Android/Linux host, or device year (2014–2024).

### 3. Scratch Area / E3 Working Memory at `0x21D244`
A 320-byte zone (`0x21D244–0x21D384`) identified as the E3/SAFER+ working area. AU_RAND appears here transiently during encryption setup. Contents change completely per session with high entropy. First published identification of this zone.

### 4. Second AU_RAND Copy at `0x21DBF0`
AU_RAND is staged at a fixed address `0x21DBF0` outside the connection struct. Stable across sessions, changes with each new connection.

### 5. EN_RAND Not Extractable via Software
EN_RAND is generated and consumed internally by the BCM4345C0 firmware during E3 computation in a few milliseconds. It is never exposed to the HCI host, not persistently stored in accessible RAM, and not capturable via BlueZ `vendor_diag`, InternalBlue LMP monitor, btsnoop, or any tested software method. KC is similarly not persistent after E3. This is documented as a security finding: the firmware design prevents session key extraction even on a KNOB-vulnerable chip.

### 6. iPhone 16 Pro (2024) with AES-CCM Vulnerable
The KNOB attack succeeds on iPhone 16 Pro using AES-CCM (Secure Connections), demonstrating that the vulnerability extends to current Apple devices 7 years after the original disclosure. With L=1 and AES-CCM, the 256 K'C candidates are `0xXX00...00` (trivial brute force).

### 7. `Public RAND` in InternalBlue = AU_RAND (not EN_RAND)
The `Public RAND` field shown by InternalBlue's `info connections` is AU_RAND, not EN_RAND as incorrectly assumed in all informal writeups referencing InternalBlue. Confirmed by cross-referencing with captured LMP_au_rand packets.

---

## Key Technical Values — BCM4345C0

| Symbol | Value | Source |
|---|---|---|
| `CONNECTION_ARRAY_ADDRESS` | `0x204BA8` | fw_0x6119.py |
| `CONNECTION_STRUCT_LENGTH` | `0x150` | fw_0x6119.py |
| Key length offset in struct | `+0xA7` | **Found by us** |
| `key_len_addr` slot 0 | `0x20557F` | **Found by us** |
| `key_len_addr` slot 1 | `0x2056CF` | **Found by us** |
| Accessible RAM range | `0x200000–0x227FFF` | **Found by us** |
| E3 scratch area | `0x21D244–0x21D384` | **Found by us** |
| AU_RAND staging address | `0x21DBF0` | **Found by us** |
| Samsung Ace 2014 KL | `f28bc3dc14fc8432aafbab1a4bc44c26` | **Found by us** |
| iPhone 6S KL | `877779624ab464c66a93c4092608b255` | **Found by us** |

---

## BCM4345C0 Hardware Constraints

**ROM**: Not accessible via InternalBlue on RPi 5. Both readMem and writeRAM return error 0x12 for addresses below 0x1F0000. This is a hardware-level protection (Spectra mitigations) blocking both read and write access to ROM. Not present on RPi 3+ or RPi 4.

**RAM:** Fully readable and writable in range `0x200000–0x227FFF` (163,840 bytes). `writemem` works correctly — confirmed by KNOB attack on 5 devices.

**Patchram:** Functional. `writemem` patches survive for the duration of a connection and are reset on reconnection or reboot.

---

## References

- [KNOB Attack Paper — USENIX Security 2019](https://www.usenix.org/conference/usenixsecurity19/presentation/antonioli)
- [francozappa/knob — Original PoC](https://github.com/francozappa/knob)
- [seemoo-lab/internalblue](https://github.com/seemoo-lab/internalblue)
- [Polypyus — Binary Diffing Tool](https://github.com/seemoo-lab/polypyus)
- [InternalBlue: The Perfect Bluetooth Research Device (Classen, 2021)](https://naehrdine.blogspot.com/2021/02/internalblue-perfect-bluetooth-research.html)
