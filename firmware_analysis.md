# BCM4345C0 Firmware and RAM Analysis

This document summarizes the firmware-related information and RAM mapping findings collected during the project.

The final interpretation of this work is that the Raspberry Pi 5 / BCM4345C0 setup allows local HCI/InternalBlue key-size reporting manipulation, but does not provide enough evidence or capability to demonstrate a complete LMP-level KNOB downgrade.

---

## Chip Information

| Field         | Value                 |
| ------------- | --------------------- |
| Chip family   | BCM4345C0 / CYW43455  |
| Chip ID       | `0x6119`              |
| Manufacturer  | Cypress Semiconductor |
| Platform used | Raspberry Pi 5        |
| Framework     | InternalBlue          |

---

## Memory Map from `fw_0x6119.py`

The following memory information was derived from the InternalBlue firmware description file for chip ID `0x6119`.

| Start      | End        | Type / Description                   |
| ---------- | ---------- | ------------------------------------ |
| `0x000000` | `0x090000` | ROM region                           |
| `0x0D0000` | `0x0D8000` | RAM / patch-related region           |
| `0x200000` | `0x228000` | Main RAM region used in the analysis |
| `0x260000` | `0x268000` | ROM / controller region              |
| `0x310000` | —          | Patchram target table                |
| `0x0D0000` | —          | Patchram value table                 |

Not all nominal memory regions were reliably readable in our Raspberry Pi 5 setup. The most useful region for RAM analysis was the main RAM range around:

```text
0x200000 - 0x228000
```

---

## Known Addresses from `fw_0x6119.py`

| Symbol                      | Address    | Notes                                          |
| --------------------------- | ---------- | ---------------------------------------------- |
| `CONNECTION_ARRAY_ADDRESS`  | `0x204BA8` | Base of the connection structure array         |
| `CONNECTION_STRUCT_LENGTH`  | `0x150`    | Size of each connection entry                  |
| `CONNECTION_MAX`            | `11`       | Maximum number of connection entries           |
| `BLOC_HEAD`                 | `0x200490` | Dynamic memory pools                           |
| `SENDLCP_CODE_BASE_ADDRESS` | `0x21F000` | LMP injection code area                        |
| `lmulp_sendLcp`             | `0x92062`  | ROM function address from firmware description |
| `PATCHRAM_TARGET_TABLE`     | `0x310000` | Patchram target table                          |
| `PATCHRAM_VALUE_TABLE`      | `0x0D0000` | Patchram value table                           |
| `PATCHRAM_NUMBER_OF_SLOTS`  | `128`      | Number of patchram slots                       |

---

## Connection Structure Mapping

During the project, we experimentally mapped relevant fields inside the active Bluetooth connection structure.

The general formula used to compute the reported key-size field was:

```text
key_len_addr =
    CONNECTION_ARRAY_ADDRESS
    + slot_index * CONNECTION_STRUCT_LENGTH
    + 0xA7
```

With the values above:

```text
key_len_addr =
    0x204BA8
    + slot_index * 0x150
    + 0xA7
```

Example addresses:

| Slot index | Reported key-size address |
| ---------- | ------------------------- |
| 0          | `0x204C4F`                |
| 1          | `0x204D9F`                |
| 2          | `0x204EEF`                |
| 7          | `0x20557F`                |

For the Samsung Galaxy Ace Style 2014 experiments, the stable reported key-size field was observed at:

```text
0x20557F
```

---

## Important Interpretation of `+0xA7`

The field at offset `+0xA7` was initially interpreted as a possible key-size control field because writing:

```text
writemem <key_len_addr> 01 --hex
```

caused InternalBlue to report:

```text
Effective Key Len: 1 byte
```

and caused the HCI command `Read Encryption Key Size` to return a key size of `0x01`.

However, later validation showed that this is not sufficient evidence of a real KNOB downgrade.

The decisive timing trace showed:

```text
Encryption Change
Read Encryption Key Size -> 16

Later, after RAM writes:
Read Encryption Key Size -> 0
Read Encryption Key Size -> 1
```

Therefore, the final interpretation is:

> `+0xA7` is a post-negotiation reporting field used by InternalBlue and HCI. Modifying it can forge the locally reported key size, but it does not prove that the LMP-negotiated entropy value `N` was reduced.

---

## Other Connection-Structure Fields

During earlier cryptographic analysis, additional connection-structure offsets were identified and compared against authentication-related values.

| Offset from slot base | Size | Interpreted content                   | Status                              |
| --------------------- | ---: | ------------------------------------- | ----------------------------------- |
| `+0x60`               | 16 B | Link Key `KL`                         | Experimentally observed             |
| `+0x70`               | 16 B | Authentication random value `AU_RAND` | Experimentally observed             |
| `+0x80`               |  4 B | `SRES`                                | Compared with authentication output |
| `+0x84`               | 12 B | `ACO`                                 | Compared with authentication output |
| `+0xA7`               |  1 B | Reported effective key length         | Validated as reporting field        |

These mappings were useful for understanding the controller RAM layout, but they do not by themselves provide a complete KNOB exploit.

---

## ROM and Patchram Limitations

A complete KNOB replication would require acting before or during LMP key-size negotiation. This would likely require one of the following:

* locating the firmware function that sends or parses LMP key-size negotiation packets;
* installing a firmware hook before key derivation;
* modifying LMP packets before encryption setup;
* or obtaining equivalent cryptographic evidence from over-the-air ciphertext.

In our Raspberry Pi 5 setup, these capabilities were not available.

Attempts to access ROM or rely on ROM-level analysis were not successful in practice:

* full `dumpmem` attempts were unreliable or did not complete;
* direct reads from ROM-like addresses timed out or produced no useful response;
* the extracted HCD firmware contained RAM patch data, not the full ROM code required for complete static analysis.

Therefore, the project could not identify or patch the firmware path responsible for LMP key-size negotiation.

---

## HCD Firmware Extraction

The HCD firmware extraction script was used to inspect the firmware patch file.

Observed extraction summary:

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Extracted segments | 322                                 |
| Base address       | `0x000D0200`                        |
| End address        | `0x0021AFA3`                        |
| Approximate size   | 1323 KB                             |
| Content            | RAM patch overlay, not complete ROM |

The extracted HCD was useful to understand patch layout, but insufficient for full firmware reverse engineering because the relevant ROM code was not available.

---

## Final Firmware-Level Conclusion

The firmware/RAM analysis produced useful original findings about the BCM4345C0 connection structure and the reported key-size field.

However, the available Raspberry Pi 5 setup did not expose the firmware functionality required to reproduce a complete KNOB attack.

Final conclusion:

> The BCM4345C0 RAM field at offset `+0xA7` can be modified to alter the key size reported by InternalBlue and HCI, but this is a reporting-level effect. A complete KNOB replication would require LMP-level visibility/modification, reliable ROM/patchram access, or external BR/EDR ciphertext capture.
