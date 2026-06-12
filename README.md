# KNOB Replication Feasibility on Raspberry Pi 5 / BCM4345C0

> Experimental analysis of KNOB attack replication limits on Raspberry Pi 5 / BCM4345C0-CYW43455.
> University project — Bluetooth BR/EDR security.
> Authors: Marco Stocco and Riccardo Citron.

---

## Overview

This repository documents an experimental feasibility study of the KNOB attack on the Raspberry Pi 5 Bluetooth controller, based on the Broadcom/Cypress BCM4345C0/CYW43455 family.

The original objective was to reproduce a complete KNOB-style Bluetooth BR/EDR entropy downgrade, i.e., to force the negotiated encryption key size from 16 bytes to 1 byte. During the project, we initially observed an apparent downgrade: modifying a RAM field at offset `+0xA7` inside the active connection structure caused both InternalBlue and the standard HCI command `Read Encryption Key Size` to report a 1-byte key size.

However, later validation showed that this effect is not sufficient evidence of a real KNOB downgrade. In a decisive timing trace, the controller reported `Key size: 16` immediately after `Encryption Change`; altered values such as `0` and `1` appeared only later, after direct RAM writes to the local reporting field.

Therefore, the final conclusion of this project is:

> With the available Raspberry Pi 5 / BCM4345C0 setup, we can demonstrate an HCI/InternalBlue key-size reporting false positive, but not a complete LMP-level KNOB replication.

This repository preserves the experimental process, memory-mapping work, validation traces, tested RAM candidates, and final findings.

---

## Final Result

### What we demonstrated

* The Raspberry Pi 5 / BCM4345C0 controller RAM can be inspected and partially modified through InternalBlue.
* The active connection structure contains a field at offset `+0xA7` that controls the key size reported by InternalBlue and by HCI `Read Encryption Key Size`.
* Writing `0x01` to this field can make the local controller report a 1-byte key size.
* The reported key size can also be changed to invalid values, such as `0`, showing that the HCI-reported value is mutable controller state.
* Timing validation shows that the first key-size read immediately after `Encryption Change` remains 16 bytes.
* Therefore, the apparent downgrade is a post-encryption HCI/InternalBlue reporting artifact.

### What we did not demonstrate

* We did not prove that the LMP-negotiated entropy value `N` was reduced to 1.
* We did not modify LMP key-size negotiation packets before encryption setup.
* We did not obtain a reliable firmware hook before key derivation.
* We did not capture over-the-air BR/EDR ciphertext to prove brute-forceability.
* We do not claim a complete KNOB attack replication with this setup.

---

## Main Contributions

1. **BCM4345C0 connection-structure analysis**
   We experimentally mapped relevant fields inside the active Bluetooth connection structure.

2. **Identification of the reported key-size field**
   The field at offset `+0xA7` was identified as the value used by InternalBlue and HCI to report the effective key length.

3. **HCI/InternalBlue false-positive validation**
   We showed that HCI and InternalBlue can report a 1-byte key size even when this does not prove an LMP-level downgrade.

4. **Timing-based validation**
   The decisive trace showed:

   ```text
   Encryption Change
   Read Encryption Key Size -> 16

   Later, after RAM writes:
   Read Encryption Key Size -> 0
   Read Encryption Key Size -> 1
   ```

5. **Upstream RAM candidate search**
   We tested multiple RAM candidates that could have acted as upstream key-size inputs. None caused a natural 1-byte key-size result without directly modifying the `+0xA7` reporting field.

6. **Feasibility assessment**
   We identified the missing capabilities required for a complete KNOB replication on this platform: LMP-level visibility/modification, reliable firmware patching, or external BR/EDR ciphertext capture.

---

## Repository Structure

```text
.
├── README.md
├── PROGRESS.md
├── firmware_analysis.md
├── vulnerability_table.md
├── KNOB_PoC_BCM4345C0.py
├── hcd_to_bin.py
└── .gitignore
```

This repository is being reorganized for final submission. Some file names may still reflect earlier project phases, when the initial apparent downgrade had not yet been invalidated by the later false-positive analysis.

---

## Important Note on PROGRESS.md

`PROGRESS.md` is a chronological research log. It intentionally preserves the full evolution of the project, including early interpretations that were later corrected.

Some older entries may describe the `+0xA7` method as a successful KNOB downgrade. Those entries should be read historically. The final validated conclusion is the one stated in this README and in the final report:

> `+0xA7` controls HCI/InternalBlue reporting, but does not prove a real LMP-level KNOB downgrade.

---

## Experimental Setup

Main setup:

```text
Attacker-controlled platform: Raspberry Pi 5
Bluetooth controller: BCM4345C0 / CYW43455 family
Framework: InternalBlue
Main target: Samsung Galaxy Ace Style 2014
Target BD address: F8:84:F2:62:96:AA
Linux tools: btmon, hcitool, bluetoothctl, l2ping
Windows tools: ADB, Wireshark, tshark
Target-side logging: Android Bluetooth HCI snoop log
```

The Raspberry Pi acted as the controlled Bluetooth peer. The Samsung device acted as the target. The experiments were performed through local controller RAM inspection, HCI tracing, target-side HCI snoop logging, and timing analysis.

---

## Key Experimental Evidence

The critical validation trace showed:

```text
7.516985   Encryption Change
7.517704   Read Encryption Key Size -> Key size: 16

40.384067  Read Encryption Key Size -> Key size: 0

50.359434  Read Encryption Key Size -> Key size: 1
```

Interpretation:

* Immediately after encryption is enabled, the controller reports 16 bytes.
* Values `0` and `1` appear only tens of seconds later.
* Those values are observed after direct RAM writes to the reporting field.
* Therefore, the observed 1-byte report is post-encryption reporting manipulation, not proof that the LMP negotiation used `N = 1`.

---

## Upstream Candidate Search

After identifying `+0xA7` as a reporting field, we searched for upstream RAM fields that could influence the key-size negotiation before encryption setup.

The tested candidates included, among others:

```text
0x2002A8
0x2002CC
0x206484
0x20EBC0
0x20EBC2
0x201FE8
0x20360C
0x208A64
0x200704
0x201858
0x203660
0x20F75C
0x210D1E
0x210D1C
```

No tested candidate caused the controller to naturally report a 1-byte key size without directly modifying the `+0xA7` reporting field.

---

## Current Status

| Question                                          | Result |
| ------------------------------------------------- | ------ |
| Can we modify the local reported key size?        | Yes    |
| Can InternalBlue report 1 byte?                   | Yes    |
| Can HCI `Read Encryption Key Size` report 1 byte? | Yes    |
| Is this sufficient proof of KNOB?                 | No     |
| Did we observe LMP negotiating `N = 1`?           | No     |
| Did we capture BR/EDR ciphertext for brute force? | No     |
| Did we identify a working upstream RAM input?     | No     |
| Did we demonstrate a complete KNOB replication?   | No     |
| Did we identify a reporting false positive?       | Yes    |

---

## Final Report

The final scientific report is available in:
```text
report/KNOB_RPi5_BCM4345C0_Report.pdf
```
---

## Reproducibility Notes

The experiments require:

* Raspberry Pi 5 with onboard BCM4345C0/CYW43455 Bluetooth controller;
* InternalBlue configured for the local controller;
* Linux Bluetooth tools (`btmon`, `hcitool`, `bluetoothctl`, `l2ping`);
* a BR/EDR target device;
* optional Android HCI snoop logging for target-side validation.

This repository does not provide a turnkey KNOB exploit. The scripts and notes are intended to document the experimental process and the feasibility analysis.

---

## Ethical and Safety Notice

This repository is intended for academic research and defensive security analysis. The experiments were performed on devices under our control. The repository does not provide a complete working KNOB exploit and should not be used to attack third-party devices.

---

## AI Assistance Disclosure

AI-based tools were used as support for command-line troubleshooting, code drafting, log interpretation, and writing refinement. All experiments, controller interactions, collected logs, technical decisions, and final conclusions were performed, verified, and critically reviewed by the authors.
