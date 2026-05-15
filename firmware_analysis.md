# BCM4345C0 Firmware Analysis

## Chip Information

| Field | Value |
|---|---|
| Chip name | BCM4345C0 (CYW43455) |
| Chip ID | 0x6119 |
| Build date | Aug 19 2014 |
| Manufacturer | Cypress Semiconductor (305) |
| HCI Version | 5.0 |
| Devices | Raspberry Pi 3+, 4, 5 |

---

## Memory Map (from fw_0x6119.py)

| Start | End | Type |
|---|---|---|
| `0x000000` | `0x090000` | ROM (read-only) |
| `0x0D0000` | `0x0D8000` | RAM |
| `0x200000` | `0x228000` | RAM |
| `0x260000` | `0x268000` | ROM |
| `0x310000` | `0x310000` | Patchram target table |
| `0xD0000` | `0xD0000` | Patchram value table |

---

## Known Addresses (from fw_0x6119.py)

| Symbol | Address | Notes |
|---|---|---|
| `DEVICE_NAME` | `0x204954` | "Marco" string |
| `CONNECTION_ARRAY_ADDRESS` | `0x204BA8` | Start of connection struct array |
| `CONNECTION_STRUCT_LENGTH` | `0x150` | Size of each connection entry |
| `CONNECTION_MAX` | `11` | Max simultaneous connections |
| `BLOC_HEAD` | `0x200490` | Dynamic memory pools |
| `SENDLCP_CODE_BASE_ADDRESS` | `0x21F000` | LMP injection code area |
| `lmulp_sendLcp` | `0x92062` | LMP send function (ROM) |
| `PATCHRAM_TARGET_TABLE` | `0x310000` | |
| `PATCHRAM_VALUE_TABLE` | `0xD0000` | |
| `PATCHRAM_NUMBER_OF_SLOTS` | `128` | |

---

## Original Findings — This Project

### Connection Struct Key Length Field

During an active BR/EDR connection with a Windows 11 laptop (`A8:59:5F:E6:C8:EA`):

- `CONNECTION_ARRAY_ADDRESS` = `0x204BA8`
- Key length field offset within struct = `+0xA7`
- Key length address (Array Index 0) = **`0x204C4F`**

**Verification:** Writing `0x01` to `0x204C4F` changes `Effective Key Len` to 1 byte in `info connections`. Writing `0x10` restores it to 16 bytes. ✅

**Formula for any connection:**
```
key_len_addr = CONNECTION_ARRAY_ADDRESS + (array_index * CONNECTION_STRUCT_LENGTH) + 0xA7
            = 0x204BA8 + (index * 0x150) + 0xA7
```

| Array Index | Key Length Address |
|---|---|
| 0 | `0x204C4F` |
| 1 | `0x204D9F` |
| 2 | `0x204EEF` |
| ... | ... |

---

## Unknown Addresses — ROM Required

| Symbol | Notes |
|---|---|
| `lm_SendLmpEncryptKeySizeReq` | ROM function, address unknown |
| Global key entropy variable | Not found in RAM scan |

### Why ROM is Inaccessible on RPi 5

The BCM4345C0 on RPi 5 has hardware-level protection that prevents ROM reading via HCI commands. This protection exists independently of the firmware HCD file:

- `dumpmem` with current firmware: times out after 2+ hours
- `dumpmem` with pre-Spectra firmware (commit 96eefffcc): same result
- Direct `hexdump 0x91F00` (ROM address): `readMem: No response to readRAM HCI command`

This protection is **not present on RPi 3+ or RPi 4** based on InternalBlue documentation. A ROM dump from those devices would contain identical ROM content (same chip, same build date Aug 19 2014).

---

## HCD Firmware Extraction

Script: `tools/hcd_to_bin.py`

- Extracted 322 segments from `BCM4345C0.hcd`
- Base address: `0x000D0200`
- End address: `0x0021AFA3`
- Size: ~1323 KB
- Content: RAM patch overlay only — does NOT contain ROM code
- Ghidra analysis of HCD alone is insufficient — ROM required for function analysis
