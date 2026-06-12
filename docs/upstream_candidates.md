# Upstream RAM Candidate Search

After validating that the `+0xA7` field behaves as a post-negotiation reporting field, we searched for a possible upstream RAM value that could influence the actual Bluetooth key-size negotiation before encryption setup.

The goal was to find a field that, when set to `0x01`, would make the controller naturally report a 1-byte key size **without directly modifying `+0xA7`**.

---

## Search Rationale

A real KNOB downgrade must affect the entropy value `N` used during LMP key-size negotiation.

Since the normal key size is 16 bytes, we searched for memory values equal to:

```text
0x10
```

which corresponds to 16 in decimal.

The search followed two strategies:

1. **Dynamic candidates**
   RAM locations that changed to `0x10` after establishing a Bluetooth connection.

2. **Static candidates**
   RAM locations that were already `0x10` before the connection and remained stable afterward.

The dynamic search was useful because the known `+0xA7` reporting field also appeared among the values that became `0x10` after connection setup. This confirmed that the diff was capturing connection-related state.

The static search was necessary because an upstream default key-size parameter could already be initialized to `0x10` before connection establishment and would therefore not appear in a pre/post diff.

---

## Filtering Criteria

Raw `0x10` matches produced many false positives. We filtered candidates manually by inspecting the surrounding memory context.

Candidates were discarded when they appeared to be:

* pointer-like fields;
* SDP or L2CAP buffers;
* code-like or literal-pool regions;
* values inside larger constants such as `0x00001000`;
* structural fields that broke the connection or destabilized the controller when modified.

---

## Test Criterion

A candidate was considered interesting only if it satisfied the following condition:

```text
candidate = 0x01
    ↓
connection established
    ↓
InternalBlue / HCI naturally report key size = 1
    ↓
without directly writing +0xA7
```

No tested candidate satisfied this condition.

---

## Candidate Summary

| Address / Region                               | Origin                                    | Action                             | Observed Result                                                                              | Classification                   |
| ---------------------------------------------- | ----------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------- |
| `+0xA7` / `0x20557F`                           | Dynamic candidate; known connection field | Directly written to `0x01`         | InternalBlue and HCI report 1 byte, but timing validation shows this happens post-encryption | Reporting field / false positive |
| `0x2002A8`                                     | Dynamic candidate, became `0x10`          | Attempted write                    | Write did not persist; value was not controllable with simple `writemem`                     | Not persistent                   |
| `0x2002CC`                                     | Dynamic candidate, became `0x10`          | Attempted write                    | Write did not persist or was restored                                                        | Not persistent                   |
| `0x206484`                                     | Dynamic candidate                         | Written to `0x01`                  | Write persisted, but final key size remained 16 bytes                                        | Writable, no effect              |
| `0x219190` / `0x219192`                        | Dynamic candidates                        | Context inspected                  | Surrounding bytes decoded as pointer-like field                                              | Discarded                        |
| `0x21D66E` / `0x21D675`                        | Dynamic candidates                        | Context inspected                  | Surrounding memory showed SDP/L2CAP-like data                                                | Discarded                        |
| `0x20EBC0`                                     | Stable `0x0010` field                     | Characterized with multiple writes | Freely writable, but no evidence of control over negotiated key size                         | Writable, no confirmed effect    |
| `0x20EBC2`                                     | Stable `0x0010` field near `0x20EBC0`     | Written to `0x01`                  | Restored to `0x10` during connection establishment; final key size remained 16 bytes         | Restored by firmware             |
| `0x201FE8`                                     | Stable aligned `0x10` candidate           | Attempted write                    | Value did not become expected `0x01`; context appeared code/literal-pool-like                | Not controllable / discarded     |
| `0x20360C`                                     | Stable aligned `0x10` candidate           | Written to `0x01`                  | Write persisted, but final key size remained 16 bytes                                        | Writable, no effect              |
| `0x208A64`                                     | Stable candidate in structured region     | Written to small values            | Connection failed or controller became unstable                                              | Unsafe structural field          |
| `0x20A135`, `0x20A14D`, `0x20A165`, `0x20A17D` | Stable byte-level hits                    | Context inspected                  | Values were part of larger `0x00001000` constants                                            | Discarded                        |
| `0x200704`                                     | Stable aligned `0x10` candidate           | Written to `0x01`                  | Write persisted, but final key size remained 16 bytes                                        | Writable, no effect              |
| `0x201858`                                     | Stable aligned candidate                  | Tested                             | No useful effect on reported key size                                                        | No effect                        |
| `0x203660`                                     | Clean stable aligned `0x10` candidate     | Written to `0x01`                  | Connection succeeded, but InternalBlue and HCI still reported 16 bytes                       | Tested, no effect                |
| `0x20F75C`                                     | Clean stable aligned `0x10` candidate     | Written to `0x01`                  | Connection succeeded, but key size remained 16 bytes                                         | Tested, no effect                |
| `0x210D1E`                                     | Isolated stable `0x0010` candidate        | Written to `0x01`                  | Connection succeeded, but key size remained 16 bytes                                         | Tested, no effect                |
| `0x210D1C`                                     | Isolated stable `0x0010` candidate        | Written to `0x01`                  | Connection succeeded, but key size remained 16 bytes                                         | Tested, no effect                |

---

## Interpretation

The candidate search did not identify a RAM field that behaves as an upstream key-size input.

Several fields were writable and persistent, but modifying them did not change the final reported key size. Other fields were restored by firmware, appeared to belong to unrelated protocol buffers, or caused instability.

The most important result is:

> No tested candidate produced a natural key size of 1 byte without directly modifying the `+0xA7` reporting field.

---

## Conclusion

The upstream candidate search supports the final conclusion of the project:

> With the available Raspberry Pi 5 / BCM4345C0 setup, static RAM-field modification is not sufficient to reproduce a complete KNOB downgrade.

A complete replication would require capabilities beyond this search, such as:

* LMP-level packet visibility;
* LMP-level packet modification;
* reliable firmware patching before key derivation;
* or over-the-air BR/EDR ciphertext capture.
