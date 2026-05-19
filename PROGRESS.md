# PROGRESS LOG — KNOB Attack on BCM4345C0

> **Format:** For each session, add a new entry at the top following the template below.  
> **Rule:** Never delete old entries. This is a cumulative log.

---

## Template for new entries

```
---
## Session — YYYY-MM-DD | Author: [Marco/Riccardo]

### What we did
-

### What we obtained
-

### Limitations encountered
-

### Next step
-
---
```

---      
## Session 2026-05-19 — Phase 3 continued: Samsung Galaxy Ace Style 2014 & Samsung Galaxy A34 5G 2024

### Devices Tested
- Samsung Galaxy Ace Style 2014 — SM-G310HN — BD Address: F8:84:F2:62:96:AA
- Samsung Galaxy A34 5G 2024 — BD Address: AC:80:FB:21:85:32

---

### Samsung Galaxy Ace Style 2014

#### Result
✅ KNOB attack confirmed — Effective Key Len reduced to 1 byte (8 bit)

#### Memory Location
- Connection ID: `---07---` (stable across reconnections once paired)
- Conn. Handle: `0xB`
- `Master of Conn.: False` — Samsung is master, RPi is slave
- Slot base: `0x2054D8`
- key_len_addr: `0x2054D8 + 0xA7 = 0x20557F`
- LMP Features: `0f000341bffecffe`

#### Notes
- Once paired, the Samsung consistently connects to the same slot (slot base `0x2054D8`)
  and obtains the same connection handle (`0xB`), making the key_len_addr stable
  and predictable across sessions — no memory search required after initial discovery
- `Master of Conn.: False` — attack succeeds regardless of master/slave role,
  confirming the vulnerability is independent of connection role

---

### Samsung Galaxy A34 5G 2024

#### Result
✅ KNOB attack confirmed — Effective Key Len reduced to 1 byte (8 bit)

#### Memory Location
- Connection ID: `---07---`
- Conn. Handle: `0xB`
- `Master of Conn.: False`
- Slot base: `0x2054D8` (same as Samsung 2014 — slot reused after disconnection)
- key_len_addr: `0x20557F`
- LMP Features: `46000000bf3e8dfe`

#### Important Note on Interpretation
The A34 is a 2024 device and may include patches against the full KNOB MitM attack
(three-device, over-the-air LMP interception). What this test demonstrates is that:
- The A34 does **not** detect nor react to the key length modification on the connected device
- It remains connected with key=1 without disconnecting or raising any error
- This is a behavioral vulnerability — the device accepts a degraded encryption session
  without any warning or countermeasure at the HCI/host level

A definitive assessment of whether the A34 would reject a key=1 negotiation in a true
MitM scenario would require the full three-device attack setup.

---

### Cross-Device Finding: offset +0xA7 is universal on BCM4345C0

The key length field offset `+0xA7` from the slot base has been verified on all
three tested devices:

| Device | BD Address | Slot Base | key_len_addr | Result |
|---|---|---|---|---|
| JBL Clip 2 | 40:EF:4C:8C:88:DF | variable | slot_base + 0xA7 | ✅ |
| Samsung Galaxy Ace Style 2014 | F8:84:F2:62:96:AA | `0x2054D8` | `0x20557F` | ✅ |
| Samsung Galaxy A34 5G 2024 | AC:80:FB:21:85:32 | `0x2054D8` | `0x20557F` | ✅ |

The offset `+0xA7` is constant across all devices and connection types on BCM4345C0.
This is an original finding not previously documented for this chip.  

## Session 2026-05-19 — Phase 3: First Complete Test on JBL Clip 2

### Objective
Perform the full KNOB attack on JBL Clip 2 (40:EF:4C:8C:88:DF) and verify
key length reduction to 1 byte.

### Result
✅ KNOB attack confirmed on JBL Clip 2 — Effective Key Len reduced to 1 byte (8 bit)

---

### Critical Finding: Active Connection Slots vs CONNECTION_ARRAY_ADDRESS

The value `CONNECTION_ARRAY_ADDRESS = 0x204BA8` from `fw_0x6119.py` is correct as
the array base, but InternalBlue always reports `Array Index: 00` for all connections
— this is a parser bug for this firmware version. The active JBL connection is not
necessarily located in slot 0.

### Technique to Find the Correct Memory Slot (JBL Clip 2)

1. Run `info connections` in InternalBlue and note the connection number
   (e.g. `---05---`, `---01---`) — this changes on every reconnection
2. Search for the pattern `55 55 55 55` in the first 0x20 bytes of each slot:
   - Slot N = `0x204BA8 + (N * 0x150)`
   - Slot 0: `0x204BA8`
   - Slot 1: `0x204CF8`
   - Slot 2: `0x204E48`
   - Slot 3: `0x204F98`
   - Slot 4: `0x2050E8`
   - Slot 5: `0x205238`
3. Verify presence of JBL BD address (`df 88 8c 4c ef 40`) at offset +0x20 of the slot
4. Key length field is at `slot_base + 0xA7`
5. Execute `writemem <slot_base + 0xA7> 01 --hex`

### Experimentally Verified Examples

| Session | Connection ID | Slot | key_len_addr | Result |
|---|---|---|---|---|
| 1 | ---05--- | 5 | `0x2052DF` | ✅ Key = 1 byte |
| 2 | ---01--- | 1 | `0x204D9F` | ✅ Key = 1 byte |

### General Formula
slot_base = 0x204BA8 + (slot_index * 0x150)
key_len_addr = slot_base + 0xA7

### Operational Notes
- The connection ID number in InternalBlue does NOT directly correspond to the slot index
- The correct slot is identified by searching for pattern `55 55 55 55` + JBL BD address
- The modification is volatile — resets on every disconnection/reboot
- `min_encrypt_key_size` must be reapplied after every reboot

### Next Steps
- Test on Samsung Galaxy 2014 (not in the original paper → original contribution)
- Phase 4: E0 brute force on captured traffic  

## Session — 2026-05-17 | Author: Marco

### What we did
- Disabled BlueZ min key size enforcement: `echo 1 > /sys/kernel/debug/bluetooth/hci0/min_encrypt_key_size`
- Wrote and tested KNOB_PoC_BCM4345C0.py v1, v2, v3, v4 — progressively improved automation
- Attempted automatic LMP injection via HCI vendor command `0xfc58` (Broadcom send LMP)
- Established BR/EDR connections with Windows 11 laptop (A8:59:5F:E6:C8:EA) and JBL Clip 2 (40:EF:4C:8C:88:DF)
- Captured multiple btmon logs: `knob_test_windows.log`, `knob_jbl_test.log`, `knob_v4_test.log`
- Analyzed timing of LMP negotiation via btmon logs
- Researched original KNOB paper PoC methodology
- Identified BCM4345C0 ROM hardware protection as root cause of injection failure

### What we obtained

**Technical findings:**
- `0xfc58` vendor command is accepted by BCM4345C0 firmware with `Status: Success` when sent at ~20ms after Connect Complete, but does not affect key size negotiation
- JBL Clip 2 uses E0 encryption (old, brute-forceable) — confirmed in btmon log (`Encryption: Enabled with E0`)
- Windows 11 laptop uses AES-CCM — patched against KNOB
- Timing analysis: encryption established ~113ms after Connect Complete on JBL, ~140ms on Windows laptop
- `sendlmp` CLI command gives error `0x12` when connection is already in encrypted state
- Original KNOB paper PoC used Nexus 5 with **custom Android Bluetooth stack** — not Linux/BlueZ. This explains why direct LMP injection is not possible with our setup without kernel modifications

**Root cause identified:**
BlueZ on Linux manages BR/EDR authentication and encryption autonomously via the management socket layer, faster than any userspace tool can intercept. Without kernel patches or ROM access, LMP injection before encryption setup is not achievable with InternalBlue on RPi 5.

**Viable alternative approach confirmed:**
Writing `0x01` to `0x204C4F` (key length field at offset `+0xA7` in connection struct) after connection is established successfully changes `Effective Key Len` to 1 byte. This demonstrates the chip does not protect this memory field and allows E0 brute force in Phase 4.

### Limitations encountered
- `0xfc58` vendor command accepted but ineffective for key negotiation interception
- LMP injection via `sendlmp` requires connection to be in pre-encryption LMP state — window is ~113ms and BlueZ fills it before InternalBlue can act
- ROM hardware protection on RPi 5 prevents reading `lm_SendLmpEncryptKeySizeReq` address
- Original paper PoC methodology not reproducible on Linux/BlueZ without kernel patches

### Compromise vs real attack
Our approach demonstrates the **effect** of KNOB on BCM4345C0 by modifying the key length field post-connection, rather than intercepting the LMP negotiation (true MitM). This is a limitation imposed by the RPi 5 hardware ROM protection and BlueZ architecture. The finding is still valid: the chip does not protect key length in RAM, and E0 traffic with key=1 is brute-forceable.

### Next step
- Phase 2 complete: use `writemem 0x204C4F 01 --hex` approach as the PoC
- Phase 3: connect JBL Clip 2, lower key to 1, generate audio traffic, capture with btmon
- Phase 4: compile `e0/` module from francozappa/knob, brute force captured traffic
- Update KNOB_PoC_BCM4345C0.py to reflect writemem approach
- Update repo with all findings
  
## Session — 2026-05-15 | Author: Marco

### What we did
- Attempted ROM dump using `dumpmem` command in InternalBlue
- Attempted firmware downgrade to pre-Spectra version (commit 96eefffcc) to enable faster ROM reading
- Searched for global key entropy variable in RAM using targeted `hexdump` scans across address ranges: `0x203700`, `0x203780`, `0x204000`, `0x204100`, `0x204200`, `0x204300`, `0x204400`, `0x204500`, `0x204600`, `0x204700`, `0x204780`, `0x204900`, `0x204A00`
- Used diff method: hexdump before/after BT connection to identify connection-related bytes
- Attempted ROM read at `0x91F00` (near `lmulp_sendLcp`) both with original and downgraded firmware
- Established BR/EDR connection between RPi 5 and Windows 11 laptop (Acer, `A8:59:5F:E6:C8:EA`) using `bluetoothctl` with `agent NoInputNoOutput`

### What we obtained
- **Original finding #1:** Confirmed key length field is at offset `+0xA7` from `CONNECTION_ARRAY_ADDRESS` inside the connection struct
- **Original finding #2:** Key length address for active connection at Array Index 0 = `0x204C4F`
- **Verified:** Writing `0x01` to `0x204C4F` changes `Effective Key Len` to 1 byte in `info connections` — confirmed working
- **Verified:** Value restored to `0x10` (16 bytes) correctly after test
- **Confirmed:** bluetoothctl `agent NoInputNoOutput` + `sspmode 0` required for Windows 11 pairing

### Limitations encountered
- ROM dump (`dumpmem`) with pre-Spectra firmware: did not complete even after 2+ hours — RPi 5 has hardware-level ROM read protection independent of firmware version
- ROM read at specific address (`hexdump 0x91F00`): times out with both original and downgraded firmware — HCI command refused at hardware level
- Global entropy variable not found in RAM scan — likely a constant in ROM or passed as immediate value in ARM instructions
- Phone (Android) pairing failed repeatedly with `Authentication Failed (0x05)` — Windows 11 laptop required instead

### Next step
- Phase 2: Write `KNOB_PoC_BCM4345C0.py` using `sendlmp` to inject `LMP_encryption_key_size_req` with key size = 1 during active BR/EDR connection
- Phase 3: Test against multiple target devices, capture with `btmon`, build vulnerability table
- Optional: Obtain ROM dump from RPi 3+ or RPi 4 (same BCM4345C0, potentially accessible ROM) to find global entropy variable and `lm_SendLmpEncryptKeySizeReq` address

---

## Session — 2026-05-14 | Author: Marco

### What we did
- Read and analyzed `fw_0x6119.py` firmware description file for BCM4345C0
- Researched blog post `unam.re/blog/knob-with-raspberry-pi` — confirmed KNOB on RPi works but addresses not published in text (only in screenshots)
- Checked InternalBlue issues #32 and #57 for BCM4345C0 KNOB attempts
- Checked InternalBlue `examples/rpi3/KNOB_PoC.py` — confirmed it targets BCM43430A1 (RPi 3 base), not BCM4345C0
- Attempted ROM dump with `dumpmem` after firmware downgrade — ran for 120+ minutes without completing, SSH session dropped
- Cleaned up: deleted 1.5GB `btsnoop.log` left by InternalBlue during dump attempt
- Restored original firmware after failed downgrade

### What we obtained
- Confirmed `lmulp_sendLcp` at `0x92062` (from fw_0x6119.py)
- Confirmed `SENDLCP_CODE_BASE_ADDRESS = 0x21F000`
- Confirmed `sendlmp` command available and functional in InternalBlue on BCM4345C0
- Confirmed no public BCM4345C0 ROM dump or KNOB addresses exist anywhere online
- Confirmed blog post used BCM43430A1 (different chip), not BCM4345C0

### Limitations encountered
- `dumpmem` with pre-Spectra firmware: still too slow on RPi 5 (120+ min, no completion)
- No public BCM4345C0 ROM dump found online
- SSH timeout during long-running dump operation

### Next step
- Establish stable BR/EDR connection for RAM analysis
- Use targeted `hexdump` to find global entropy variable without full ROM dump

---

## Session — 2026-05-13 | Author: Marco

### What we did
- Full InternalBlue setup on Raspberry Pi 5
- Applied Python 3.13 compatibility fixes to `cli.py`
- Verified RAM read/write with `hexdump 0x200400` and `writemem`
- Extracted HCD firmware to binary with `hcd_to_bin.py`
- Attempted Ghidra analysis of extracted HCD — confirmed it contains only RAM patches, not ROM
- Researched all known KNOB PoC addresses for other chips

### What we obtained
- InternalBlue fully operational on BCM4345C0 ✅
- RAM read/write confirmed working ✅
- HCD extraction: 322 segments, base `0xD0200`, size 1323KB
- Confirmed no public BCM4345C0 KNOB addresses exist

### Limitations encountered
- Ghidra analysis of HCD useless without ROM — all function strings are in ROM, not in HCD
- Nexus 5/6P KNOB addresses confirmed incompatible with BCM4345C0

### Next step
- Attempt ROM dump via `dumpmem` after firmware downgrade
- Research blog post at `unam.re/blog/knob-with-raspberry-pi`
