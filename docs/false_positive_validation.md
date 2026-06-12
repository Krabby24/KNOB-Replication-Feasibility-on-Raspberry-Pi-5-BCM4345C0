# False Positive Validation

This document summarizes the main validated finding of the project: the apparent KNOB downgrade obtained by modifying the `+0xA7` field is an HCI/InternalBlue reporting false positive, not proof of a complete LMP-level KNOB attack.

---

## Initial Observation

During early experiments, we identified a field in the active BCM4345C0 connection structure at offset:

```text
+0xA7
```

For the Samsung Galaxy Ace Style 2014 stable connection slot, this corresponded to:

```text
0x20557F
```

Writing:

```text
writemem 0x20557F 01 --hex
```

caused InternalBlue to report:

```text
Effective Key Len: 1 byte
```

The standard HCI command:

```bash
hcitool cmd 0x05 0x0008 <handle_lsb> <handle_msb>
```

also returned a key size of `0x01`.

At first, this looked compatible with a successful KNOB-style downgrade.

---

## Why This Was Not Sufficient

A real KNOB attack requires the Bluetooth controllers to negotiate a reduced encryption entropy value `N` during the LMP key-size negotiation, before the final encryption key is derived and before encryption is enabled.

Therefore:

```text
HCI reports key size = 1
```

does not automatically imply:

```text
LMP negotiated N = 1
```

especially when the local controller RAM can be modified directly.

---

## Timing Validation

The decisive validation was performed with Raspberry Pi-side `btmon` / vendor diagnostic traces.

The relevant sequence was:

```text
7.516985   Encryption Change
7.517704   Read Encryption Key Size -> Key size: 16

40.384067  Read Encryption Key Size -> Key size: 0

50.359434  Read Encryption Key Size -> Key size: 1
```

Interpretation:

* immediately after `Encryption Change`, the controller reports 16 bytes;
* values `0` and `1` appear only tens of seconds later;
* those altered values appear after direct RAM writes to the reporting field.

Therefore, the values `0` and `1` are post-encryption reporting artifacts.

---

## Invalid Reported Values

The controller could also be made to report invalid or nonsensical key sizes after RAM modification, such as:

```text
0 byte
255 byte
```

These values cannot represent valid Bluetooth BR/EDR negotiated encryption key sizes.

This reinforces the conclusion that `HCI Read Encryption Key Size` is reading a mutable controller-maintained reporting field, not independently verifying the real cryptographic entropy of the active link.

---

## Traffic Continuity

After modifying the reported key-size field, L2CAP traffic could still continue.

If the RAM write had changed the live cryptographic key only on the Raspberry Pi side, the Raspberry Pi and the target would no longer share the same encryption state, and encrypted traffic would be expected to fail.

This does not prove the exact negotiated entropy, but it is consistent with the interpretation that the modification affects reporting rather than the live encryption key.

---

## Final Classification

The `+0xA7` field is classified as:

```text
post-negotiation reporting field
```

It controls:

```text
InternalBlue Effective Key Len
HCI Read Encryption Key Size response
```

It does not prove:

```text
LMP negotiated N = 1
active BR/EDR encryption key has 1 byte of entropy
complete KNOB replication
```

---

## Final Statement

The correct interpretation is:

> On Raspberry Pi 5 / BCM4345C0, the `+0xA7` field can be modified to forge the key size reported by InternalBlue and HCI. However, timing validation shows that immediately after encryption setup the controller still reports 16 bytes. Therefore, the apparent 1-byte downgrade is an HCI/InternalBlue reporting false positive, not proof of a complete KNOB attack.
