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
