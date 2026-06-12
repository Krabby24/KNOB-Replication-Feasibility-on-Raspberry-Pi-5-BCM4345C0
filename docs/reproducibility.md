# Reproducibility Notes

This document describes how to reproduce the main experiments performed during the project.

The goal is not to provide a complete KNOB exploit. The goal is to reproduce the analysis showing that the `+0xA7` field on the Raspberry Pi 5 / BCM4345C0 controller affects HCI/InternalBlue key-size reporting, but does not prove a real LMP-level entropy downgrade.

---

## Scope

These steps allow reproducing:

* connection establishment between Raspberry Pi 5 and a BR/EDR target;
* InternalBlue inspection of active connections;
* local RAM modification of the reported key-size field;
* HCI `Read Encryption Key Size` verification;
* `btmon` timing analysis;
* target-side Android HCI snoop extraction, when available.

These steps do **not** provide:

* LMP-level packet modification;
* a firmware hook before key derivation;
* a complete KNOB exploit;
* over-the-air BR/EDR ciphertext capture;
* cryptographic proof of a 1-byte entropy link key.

---

## Hardware

Main setup used during the project:

```text
Attacker-controlled platform: Raspberry Pi 5
Bluetooth controller: BCM4345C0 / CYW43455 family
Main target: Samsung Galaxy Ace Style 2014
Target BD address: F8:84:F2:62:96:AA
```

Other devices were also used during earlier exploratory phases, but the final validation was based primarily on the Samsung target.

---

## Software Tools

On Raspberry Pi:

```text
InternalBlue
btmon
hcitool
bluetoothctl
l2ping
```

On Windows:

```text
ADB
Wireshark
tshark
PowerShell
```

---

## 1. Start InternalBlue

On the Raspberry Pi:

```bash
cd ~/internalblue
source venv/bin/activate
sudo -E venv/bin/internalblue
```

Inside InternalBlue, inspect active connections:

```text
info connections
```

---

## 2. Connect the Target Device

From a normal Raspberry Pi shell:

```bash
bluetoothctl
power on
agent NoInputNoOutput
default-agent
connect F8:84:F2:62:96:AA
```

After connection, return to InternalBlue and run:

```text
info connections
```

Record:

* connection handle;
* remote Bluetooth address;
* reported effective key length;
* connection slot / memory location if known.

---

## 3. Locate the Reported Key-Size Field

During the Samsung experiments, the reported key-size field was observed at:

```text
0x20557F
```

This corresponds to:

```text
active_connection_structure + 0xA7
```

The general form used during the analysis was:

```text
key_len_addr =
    connection_array_base
    + slot_index * connection_struct_size
    + 0xA7
```

The exact address may change depending on the active connection slot and device.

---

## 4. Modify the Reported Key-Size Field

Inside InternalBlue:

```text
writemem 0x20557F 01 --hex
```

Then verify:

```text
info connections
```

Expected reporting-level observation:

```text
Effective Key Len: 1 byte
```

Important:

> This does not prove a real KNOB downgrade. It only shows that the local reported key-size field was modified.

---

## 5. Query HCI Read Encryption Key Size

From a Raspberry Pi shell, use the connection handle reported by InternalBlue.

For handle `0x000B`:

```bash
sudo hcitool cmd 0x05 0x0008 0B 00
```

For handle `0x000C`:

```bash
sudo hcitool cmd 0x05 0x0008 0C 00
```

The final byte of the response is the key size reported by the controller.

Example reporting-level result after modifying `+0xA7`:

```text
... 0B 00 01
```

This means HCI reports key size `0x01`.

Again:

> HCI reporting `0x01` does not prove that LMP negotiated `N = 1`.

---

## 6. Collect Timing Evidence with btmon

Start a trace:

```bash
sudo btmon -w knob_validation_trace.btsnoop
```

Then establish a clean connection and query key size at controlled times.

The decisive validation pattern observed during the project was:

```text
7.516985   Encryption Change
7.517704   Read Encryption Key Size -> Key size: 16

40.384067  Read Encryption Key Size -> Key size: 0

50.359434  Read Encryption Key Size -> Key size: 1
```

Interpretation:

* immediately after `Encryption Change`, the controller reports 16 bytes;
* altered values appear only later;
* therefore, the later values are post-encryption reporting artifacts.

---

## 7. Generate L2CAP Traffic

To check whether the link remains functional after reporting-field modification:

```bash
l2ping -i hci0 -s 600 -c 30 F8:84:F2:62:96:AA
```

Observed behavior:

* L2CAP traffic can continue after modifying the reported key-size field;
* this is consistent with reporting manipulation rather than live key replacement.

---

## 8. Extract Samsung HCI Snoop Log

Enable Bluetooth HCI snoop logging on the Android target through Developer Options.

On the Samsung Galaxy Ace Style 2014, the log was found at:

```text
/sdcard/Android/data/btsnoop_hci.log
```

Pull it with ADB:

```bash
adb pull /sdcard/Android/data/btsnoop_hci.log samsung_btsnoop.log
```

Analyze with tshark:

```bash
tshark -r samsung_btsnoop.log \
  -Y "bthci_evt || bthci_cmd" \
  -T fields \
  -e frame.number \
  -e frame.time_relative \
  -e _ws.col.Info
```

Expected useful events:

```text
Connect Complete
Link Key Request
Link Key Request Reply
Encryption Change
Disconnect Complete
```

In our validation, the Samsung log did not contain a target-side `HCI Read Encryption Key Size` command. Therefore, it confirmed the connection and encryption timeline, but did not reveal the target-side key size.

---

## 9. Reproducibility Warning

The following observation is reproducible at the reporting level:

```text
write +0xA7 = 0x01
    -> InternalBlue reports key size 1
    -> HCI Read Encryption Key Size reports key size 1
```

The following observation was **not** demonstrated:

```text
LMP negotiated N = 1
    -> active BR/EDR encryption key has 1 byte of entropy
    -> complete KNOB attack succeeded
```

Any reproduction of this repository should preserve this distinction.

---

## Final Reproducibility Statement

This repository supports reproducing the HCI/InternalBlue reporting false positive discovered during the project.

It does not provide a complete KNOB exploit.
