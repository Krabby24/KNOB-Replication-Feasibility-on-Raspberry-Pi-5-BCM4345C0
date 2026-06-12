# PROGRESS LOG — KNOB Attack on BCM4345C0

> **Format:** For each session, add a new entry at the top following the template below.  
> **Rule:** Never delete old entries. This is a cumulative log.  

---

> **Important note on interpretation**
>
> This file is a chronological research log. It intentionally preserves the full evolution of the project, including early hypotheses and intermediate interpretations that were later corrected by subsequent experiments.
>
> In particular, early entries may describe the `+0xA7` connection-structure field as evidence of a successful KNOB downgrade. Later validation showed that this interpretation was incomplete: `+0xA7` controls the key size reported through InternalBlue and HCI, but it does not prove that the LMP-negotiated entropy value `N` was actually reduced.
>
> The final validated conclusion of the project is reported in `README.md` and in the final report:
>
> **With the available Raspberry Pi 5 / BCM4345C0 setup, we can demonstrate an HCI/InternalBlue key-size reporting false positive, but not a complete LMP-level KNOB replication.**



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
---  

  
# 2026-05-25 — Session

## 1. Session objective

The objective of this session was to perform a definitive validation of the current Raspberry Pi 5 / BCM4345C0 KNOB method.

Until the previous session, the main experimental result was that modifying the connection-structure field at offset `+0xA7` changed the value displayed by InternalBlue as:

```text
Effective Key Len
````

and also changed the value returned by the standard HCI command:

```bash
hcitool cmd 0x05 0x0008 <handle_lsb> <handle_msb>
```

At first, this looked like a successful KNOB downgrade because after writing `0x01` into `+0xA7`, both InternalBlue and HCI could report a key size of 1 byte.

However, the key question for today was:

> Does modifying `+0xA7` really change the negotiated Bluetooth encryption entropy `N`, or does it only modify a reporting/output field after encryption has already been established?

The goal was therefore to verify whether the current method can still be considered a real KNOB attack, or whether it must be reclassified as a false-positive reporting manipulation.

---

## 2. Theoretical reference point

A real KNOB attack requires the attacker to influence the value `N` used during the Bluetooth BR/EDR encryption key size negotiation.

The important theoretical chain is:

```text
LMP key size negotiation
        ↓
N is selected
        ↓
KC is reduced through Es(KC, N)
        ↓
K'C is used as the actual E0 encryption key
        ↓
encrypted traffic uses the weakened key
```

Therefore, for a real KNOB attack, the downgrade must happen **before** or **during** the LMP encryption setup.

A post-encryption modification of a RAM field that only changes what HCI reports is not enough.

The crucial distinction is:

```text
HCI/InternalBlue reports key size = 1
```

does **not necessarily imply**:

```text
LMP negotiated N = 1
```

or:

```text
the active E0 encryption key was derived with 1 byte of entropy
```

Today’s session focused exactly on proving or disproving this distinction experimentally.

---

## 3. Setup used in this session

The experimental setup was:

```text
Attack platform: Raspberry Pi 5
Bluetooth controller: BCM4345C0 / CYW43455 family
Framework: InternalBlue
Target device: Samsung Galaxy Ace Style 2014
Target BD_ADDR: F8:84:F2:62:96:AA
Windows tools: adb, Wireshark/tshark
Samsung setting: Bluetooth HCI snoop log enabled
RPi tools: btmon, hcitool, l2ping, InternalBlue
```

The Samsung target had Developer Options enabled, including Bluetooth HCI snoop logging.

ADB on Windows was verified successfully:

```powershell
.\adb.exe devices
```

Output:

```text
List of devices attached
4203adaecc058100        device
```

So the Samsung was correctly connected and authorized for ADB.

---

## 4. Samsung-side HCI snoop verification

### 4.1 Locating the Samsung btsnoop log

The expected path:

```text
/sdcard/btsnoop_hci.log
```

did not exist.

Because the Android shell on this old Samsung device did not include the `find` command, we manually inspected common paths.

The valid Samsung HCI snoop log was found at:

```text
/sdcard/Android/data/btsnoop_hci.log
```

It was copied to Windows as:

```powershell
.\adb.exe pull /sdcard/Android/data/btsnoop_hci.log .\samsung_btsnoop_plusA7_today.log
```

The extracted file was:

```text
samsung_btsnoop_plusA7_today.log
size: 136908 bytes
```

This confirmed that Samsung-side HCI logging was working.

---

### 4.2 First Samsung-side filter

The Samsung btsnoop log was analyzed with tshark:

```powershell
& "C:\Program Files\Wireshark\tshark.exe" -r .\samsung_btsnoop_plusA7_today.log -V | Select-String -Pattern "Read Encryption Key Size|Key Size|Key size|Encryption Change|Connection Complete|Disconnection|Disconnect|Status"
```

The relevant result was:

```text
Bluetooth HCI Event - Encryption Change [v1]
Status: Success
```

However, no `Read Encryption Key Size` command was visible in the Samsung-side log. The log therefore confirmed that the Samsung saw encryption being enabled, but it did not expose the negotiated key size through HCI. 

Initial conclusion:

```text
Samsung btsnoop log is valid.
Samsung sees Encryption Change.
Samsung does not issue HCI Read Encryption Key Size.
Therefore Samsung btsnoop is inconclusive for the real value of N.
```

---

### 4.3 Samsung HCI timeline

A full HCI timeline was extracted with:

```powershell
& "C:\Program Files\Wireshark\tshark.exe" -r .\samsung_btsnoop_plusA7_today.log -Y "bthci_evt || bthci_cmd" -T fields -e frame.number -e frame.time_relative -e _ws.col.Info > .\samsung_hci_timeline.txt
```

The important part of the Samsung timeline was:

```text
633.540771   Rcvd Connect Complete
633.614990   Rcvd Link Key Request
633.615600   Sent Link Key Request Reply
633.658325   Rcvd Encryption Change [v1]
760.794281   Rcvd Disconnect Complete
```

This confirms that the Samsung-side log captured the real connection and encryption setup.

However, there was still no:

```text
Sent Read Encryption Key Size
Rcvd Command Complete (Read Encryption Key Size)
```

Therefore the Samsung HCI log could not directly tell us whether `N = 1` or `N = 16`. 

Conclusion:

```text
Samsung-side HCI logging is valid but inconclusive for key size.
The Samsung stack did not query the key size through HCI during this test.
```

---

## 5. RPi vendor diagnostic / btmon validation

Since the Samsung btsnoop log did not expose the key size, we moved to Raspberry Pi-side vendor diagnostics.

The goal was to capture the exact timing of:

```text
Encryption Change
Read Encryption Key Size
```

and determine whether key size 1 appears before or after encryption activation.

---

### 5.1 Baseline vendor diagnostic run

With vendor diagnostics enabled, btmon showed the connection progressing normally.

The key baseline sequence was:

```text
Encryption Change
Encryption: Enabled with E0
Read Encryption Key Size
Key size: 16
```

This showed that immediately after encryption was enabled, the RPi controller reported:

```text
Key size: 16
```

not 1. 

This is important because the first read after `Encryption Change` is the closest HCI-level observation we have to the encryption setup.

Baseline conclusion:

```text
Immediately after Encryption Change, the controller reports key size 16.
```

---

### 5.2 Post-encryption +0xA7 manipulation run

We then performed the critical test:

1. Establish a normal encrypted connection.
2. Observe `Encryption Change`.
3. Observe first `Read Encryption Key Size`.
4. Modify the connection-structure key-size field `+0xA7`.
5. Read HCI key size again.

The vendor diagnostic log showed the decisive sequence:

```text
7.516985   Encryption Change
7.517704   Read Encryption Key Size → Key size: 16

40.384067  Read Encryption Key Size → Key size: 0

50.359434  Read Encryption Key Size → Key size: 1
```

This proves that:

```text
Key size 16 appears immediately after encryption is enabled.
Key size 0 appears much later.
Key size 1 appears even later.
```

The altered values `0` and `1` therefore appear tens of seconds after encryption has already been enabled. 

Time differences:

```text
40.384067 - 7.516985 ≈ 32.87 seconds after Encryption Change
50.359434 - 7.516985 ≈ 42.84 seconds after Encryption Change
```

Therefore, in this run, the modified values are definitively post-encryption.

---

## 6. Crucial conclusion about `+0xA7`

The session confirmed the most important result of the project so far:

```text
+0xA7 is not sufficient evidence of real KNOB.
```

More specifically:

```text
+0xA7 controls the key size reported by InternalBlue and by HCI Read Encryption Key Size.
```

but:

```text
directly modifying +0xA7 after encryption is enabled does not prove that the LMP-negotiated N was reduced.
```

The decisive evidence is:

```text
Immediately after Encryption Change:
    HCI reports key size 16

Later, after RAM writes:
    HCI reports key size 0
    HCI reports key size 1
```

This means that the HCI-reported key size is forgeable from RAM.

Therefore, the previous interpretation:

```text
InternalBlue Effective Key Len = 1
HCI Read Encryption Key Size = 1
therefore KNOB succeeded
```

is no longer valid.

The correct interpretation is:

```text
InternalBlue/HCI key size can be manipulated after encryption.
This is a reporting/output manipulation, not proof of real encryption downgrade.
```

---

## 7. Why this disproves the previous apparent success

The previous apparent success was based on:

```text
writemem connection_struct + 0xA7 = 01
        ↓
InternalBlue shows Effective Key Len = 1
        ↓
HCI Read Encryption Key Size returns 1
```

Today’s vendor diagnostic trace shows that this is not enough.

If `+0xA7` were truly the input to the encryption key-size negotiation, we would expect to see:

```text
Encryption Change
Read Encryption Key Size → 1
```

immediately after encryption setup.

Instead, we observed:

```text
Encryption Change
Read Encryption Key Size → 16
```

and only later:

```text
Read Encryption Key Size → 0
Read Encryption Key Size → 1
```

Thus, `+0xA7` behaves as a post-negotiation field used for reporting.

Final classification:

```text
+0xA7
→ output/reporting field
→ controls InternalBlue Effective Key Len display
→ controls HCI Read Encryption Key Size response
→ can be forged after encryption
→ not proven to be an upstream input to LMP N
```

---

## 8. Search for upstream RAM candidates

After closing the direct `+0xA7` method as a false positive, we tested the remaining clean RAM candidates that had previously been identified as possible upstream key-size sources.

The valid test criterion was:

```text
Do NOT write +0xA7.
Write candidate = 1 before connection.
Connect Samsung.
Check whether Effective Key Len / HCI key size naturally become 1.
```

A candidate is only interesting if it makes the final reported key size become 1 **without directly writing the reporting field**.

---

## 9. Candidate 1: `0x203660`

### 9.1 Context

The hexdump around `0x203660` was:

```text
00203640: ac 95 26 00  26 47 01 00  00 00 c4 09  d8 95 26 00
00203650: 01 00 00 00  00 00 00 00  00 00 00 00  00 00 00 01
00203660: 10 00 00 00  06 00 00 00  06 00 00 00  03 00 00 00
00203670: 00 00 00 00  06 06 06 02  05 01 01 00  20 00 80 00
```

The candidate field was:

```text
0x203660 = 10 00 00 00 = 0x00000010
```

### 9.2 Test

We wrote:

```text
writemem 0x203660 01 --hex
```

Then connected the Samsung and checked InternalBlue / HCI.

### 9.3 Result

The connection succeeded, but:

```text
Effective Key Len remained 16
HCI key size remained 0x10
```

Conclusion:

```text
0x203660 is not an upstream input controlling N.
```

---

## 10. Candidate 2: `0x20F75C`

### 10.1 Context

The hexdump around `0x20F75C` was:

```text
0020f730: 06 00 10 18  9f 02 00 00  06 00 10 18  7c 0a 00 00
0020f740: 06 00 10 18  02 00 00 00  04 00 08 00  04 00 00 00
0020f750: 04 00 08 00  08 00 00 00  04 00 08 00  10 00 00 00
0020f760: 04 00 08 00  a4 50 00 00  00 00 10 10  06 0d 00 00
```

The candidate field was:

```text
0x20F75C = 10 00 00 00 = 0x00000010
```

The area looked like a structured numeric table.

### 10.2 Test

We wrote:

```text
writemem 0x20F75C 01 --hex
```

Then connected the Samsung.

### 10.3 Result

The connection succeeded, but:

```text
Effective Key Len remained 16
HCI key size remained 0x10
```

Conclusion:

```text
0x20F75C is not an upstream input controlling N.
```

---

## 11. Candidate 3: `0x210D1E`

### 11.1 Context

The hexdump around `0x210D00` was:

```text
00210d00: 00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
00210d10: 00 00 00 00  00 00 00 00  00 00 00 00  10 00 10 00
00210d20: 00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
...
```

This was one of the cleanest remaining candidates because the surrounding area was almost entirely zero.

The two fields were:

```text
0x210D1C = 0x0010
0x210D1E = 0x0010
```

We tested the second halfword first:

```text
0x210D1E
```

### 11.2 Test

We wrote:

```text
writemem 0x210D1E 01 --hex
```

Then connected the Samsung.

### 11.3 Result

The connection succeeded, but:

```text
Effective Key Len remained 16
HCI key size remained 0x10
```

Conclusion:

```text
0x210D1E is not an upstream input controlling N.
```

---

## 12. Candidate 4: `0x210D1C`

### 12.1 Test

After `0x210D1E` failed, we tested the paired halfword:

```text
0x210D1C
```

We wrote:

```text
writemem 0x210D1C 01 --hex
```

Then connected the Samsung.

### 12.2 Result

Again:

```text
Effective Key Len remained 16
HCI key size remained 0x10
```

Conclusion:

```text
0x210D1C is not an upstream input controlling N.
```

---

## 13. Final status of remaining clean RAM candidates

At the end of the session, the remaining clean upstream candidates had the following result:

```text
0x203660  → tested → key size remains 16
0x20F75C  → tested → key size remains 16
0x210D1E  → tested → key size remains 16
0x210D1C  → tested → key size remains 16
```

Together with previous sessions, this means the static RAM-variable approach is essentially exhausted.

Current conclusion:

```text
No tested static RAM candidate accessible through RPi5/InternalBlue behaves as an upstream input that forces N = 1.
```

---

## 14. Overall conclusion of the session

The main result of the session is that the previous apparent KNOB method based on directly writing `+0xA7` is now experimentally disproven as a valid proof of real KNOB.

The strongest evidence is:

```text
Immediately after Encryption Change:
    HCI Read Encryption Key Size → 16

Much later, after RAM writes:
    HCI Read Encryption Key Size → 0
    HCI Read Encryption Key Size → 1
```

Therefore:

```text
+0xA7 manipulation is post-encryption reporting manipulation.
```

It does not demonstrate that the LMP-negotiated entropy `N` was reduced.

Additionally:

```text
Samsung-side btsnoop confirms encryption but does not expose key size.
Vendor diagnostic confirms HCI key size 16 immediately after encryption.
Remaining upstream RAM candidates do not affect key size.
```

Final technical statement:

```text
With the current Raspberry Pi 5 / BCM4345C0 / InternalBlue-only setup, we cannot demonstrate a complete KNOB attack equivalent to the public paper/repository implementations.
```

More precisely:

```text
The simple writable-RAM-variable approach does not produce a real key-size downgrade.
The +0xA7 method produces a convincing but invalid HCI/InternalBlue false positive.
```

---

## 15. What would be required for a real KNOB replication

A complete KNOB replication would require at least one of the following:

```text
1. LMP-level visibility:
   Capture LMP_encryption_key_size_req and prove whether N = 1 or N = 16.

2. LMP-level modification:
   Modify the outgoing or incoming LMP key-size negotiation packet before encryption setup.

3. ROM / patchram access:
   Locate and patch the firmware function responsible for LMP key-size negotiation.

4. External BR/EDR ciphertext capture:
   Capture encrypted over-the-air traffic and prove that it can be brute-forced with only 256 candidate keys.

5. A different platform:
   Use a chipset/firmware where InternalBlue supports LMP hooks, ROM access, or patchram more fully.
```

Without one of these, we can only modify HCI-visible state, not prove the actual cryptographic downgrade.

---

## 16. Recommended project pivot

Given today’s results, the project should be reframed.

Not:

```text
We successfully replicated KNOB on RPi5.
```

But:

```text
We investigated the feasibility of replicating KNOB on Raspberry Pi 5 / BCM4345C0 and discovered that the apparent key-size downgrade obtained through InternalBlue is a post-encryption HCI reporting false positive.
```

Possible new project title:

```text
Experimental Validation of KNOB Replication Limits on Raspberry Pi 5 / BCM4345C0
```

or:

```text
From Apparent KNOB Downgrade to HCI Reporting False Positive on BCM4345C0
```

Core contribution:

```text
We show that modifying the RPi5 controller RAM can forge HCI Read Encryption Key Size results, including invalid values such as 0 and altered values such as 1, without proving that the real LMP-negotiated encryption entropy was changed.
```

This is a valid cybersecurity result because it demonstrates the danger of relying only on HCI/InternalBlue output as proof of a link-layer cryptographic downgrade.

---

## 17. Suggested statement for supervisor

A concise version to communicate to the project supervisor:

```text
During the KNOB replication attempt on Raspberry Pi 5, we initially obtained an apparent downgrade by modifying the InternalBlue Effective Key Len field. However, further validation showed that this field is only a reporting/output field. In the vendor diagnostic trace, immediately after Encryption Change the controller reports Key size = 16. Only later, after RAM writes to the connection structure, HCI Read Encryption Key Size reports altered values such as 0 or 1. Therefore the current method does not prove a real KNOB downgrade.

We then tested the remaining clean RAM candidates that could have acted as upstream key-size inputs, but none caused the negotiated/reported key size to become 1 without directly writing the reporting field. With the current RPi5/InternalBlue-only setup, we therefore cannot complete a full KNOB replication as in the public papers/repositories. Further progress would require LMP-level packet modification, ROM/patchram access, or external ciphertext capture.

We propose to reframe the project as an experimental analysis of why KNOB replication is not achievable with this setup and as a demonstration of an HCI-level false positive in key-size validation.
```

---

## 18. Final session status

```text
Direct +0xA7 KNOB claim:
    closed as false positive

Samsung HCI verification:
    valid log, encryption visible, key size not exposed

RPi vendor diagnostic:
    key size 16 immediately after Encryption Change
    key size 0/1 only later after RAM writes

Static upstream RAM candidates:
    exhausted among clean candidates tested

Current feasibility:
    real KNOB not demonstrated with current setup

Next required capability:
    LMP visibility/modification, ROM/patchram, or ciphertext capture
```

```
```


## 2026-05-23 — Session

# KNOB Attack on Raspberry Pi 5 / BCM4345C0: Research Session Report

## 1. Starting Point

The goal of today’s session was to determine whether our current Raspberry Pi 5 setup can perform a real KNOB downgrade on a Bluetooth BR/EDR connection, i.e. reduce the actual encryption-key entropy from 16 bytes to 1 byte.

The target setup is:

```text
Attack platform: Raspberry Pi 5
Bluetooth chip: Cypress CYW43455 / BCM4345C0
Firmware family: chip id 0x6119
Framework: InternalBlue
Main target device: Samsung Galaxy Ace Style 2014
Target BD_ADDR: F8:84:F2:62:96:AA
```

The theoretical KNOB attack requires the devices to negotiate a small entropy value `N` during the LMP encryption key size negotiation. In the real attack, both controllers must compute the final encryption key `K'C = Es(KC, N)` using `N = 1`. Merely changing what the host or HCI reports after encryption is already active is not sufficient. The original KNOB paper is explicit that the entropy negotiation happens between Bluetooth controllers over LMP, that the host is not directly involved, and that the attacker must change the negotiated entropy before both controllers compute and use `K'C`. 

The core research question for today was therefore:

> Is the field `connection_struct + 0xA7` the real input used by firmware to set encryption entropy, or is it only an output/reporting field?

This became the central turning point of the session.

---

## 2. The Original Assumption About `+0xA7`

Before today’s deeper tests, we had mapped the BCM4345C0 connection structure and identified the following relevant fields:

```text
connection_array_base = 0x204BA8
connection_struct_size = 0x150
effective_key_len offset = +0xA7
```

For Samsung in slot 7:

```text
key_len_addr = 0x204BA8 + 7 * 0x150 + 0xA7
             = 0x20557F
```

Earlier RAM analysis had shown that `+0xA7` contained the value displayed by InternalBlue as:

```text
Effective Key Len: 16 byte
```

Writing:

```text
writemem 0x20557F 01
```

made InternalBlue display:

```text
Effective Key Len: 1 byte
```

Initially this looked like a successful KNOB downgrade. The hypothesis was:

```text
firmware reads +0xA7
        ↓
uses this value as N
        ↓
computes K'C with that entropy
        ↓
link encryption becomes weak
```

Today we tested that assumption directly.

---

## 3. Why `+0xA7` Is Not the Real Input

### 3.1 Post-encryption write to `+0xA7`

We first established a normal encrypted BR/EDR connection to the Samsung phone. InternalBlue showed:

```text
Remote BT address: f8:84:f2:62:96:aa
Conn. Handle: 0xB
Effective Key Len: 16 byte
Link Key: 03359eaafa82f88792ea2d7b2d3a003d
```

Then we wrote:

```text
writemem 0x20557F 01
```

After this write, InternalBlue showed:

```text
Effective Key Len: 1 byte
Link Key: 03
```

The fact that the Link Key display became only `03` is important. It strongly suggests that InternalBlue uses the effective key length field to decide how many bytes to print, rather than showing evidence that the real link key changed.

Then we queried the standard HCI command:

```bash
sudo hcitool cmd 0x05 0x0008 0B 00
```

The controller returned:

```text
01 08 14 00 0B 00 01
```

Decoded:

```text
status = 0x00 success
handle = 0x000B
reported key size = 0x01
```

So both InternalBlue and HCI reported 1 byte.

However, this write happened after encryption was already active. At that point, `K'C` should already have been computed. If this write had changed the actual live encryption key only on the RPi side, the Samsung would still be using the old key and the encrypted link should break.

It did not.

---

### 3.2 L2CAP traffic continued after changing `+0xA7`

We used `l2ping` to generate real Bluetooth L2CAP traffic over the encrypted link.

After setting `+0xA7` to `0x01`, the connection continued to exchange L2CAP Echo Requests and Echo Responses. This means the encrypted link remained functional after the reported key size was modified.

This is a strong indication that the active encryption key was not changed by the post-encryption RAM write.

The reasoning is:

```text
If +0xA7 changed the live cryptographic key only on RPi:
    RPi would encrypt/decrypt with a different key
    Samsung would still use the original key
    L2CAP traffic should fail

Observed:
    L2CAP traffic continued

Conclusion:
    +0xA7 does not control the already-active encryption key
```

The btmon log confirms that L2CAP Echo Response packets continued while `HCI Read Encryption Key Size` reported key size 0 in a later invalid-value test, showing that the link remained alive even when the reported key size was nonsensical. 

---

### 3.3 Invalid values: `0x00` and `0xff`

The decisive tests were the invalid-value experiments.

We wrote:

```text
writemem 0x20557F ff
```

InternalBlue then reported:

```text
Effective Key Len: 255 byte (2040 bit)
```

and `HCI Read Encryption Key Size` returned:

```text
... 0B 00 FF
```

This is impossible as a real Bluetooth encryption key size. BR/EDR key entropy is negotiated between 1 and 16 bytes. A reported value of `0xff` cannot represent a valid negotiated key size.

Then we wrote:

```text
writemem 0x20557F 00
```

InternalBlue reported:

```text
Effective Key Len: 0 byte
```

and HCI returned:

```text
... 0B 00 00
```

The connection remained stable, and L2CAP traffic continued.

This is the crucial proof:

> The controller’s HCI `Read Encryption Key Size` response is reading a mutable RAM field, not verifying the real cryptographic entropy of the active link.

Therefore:

```text
HCI reports 1
≠ proof that KNOB succeeded
```

This is one of the most important findings of the project.

---

### 3.4 Final conclusion on `+0xA7`

We now classify:

```text
+0xA7 = reported/effective key size state field
```

not:

```text
+0xA7 = input variable used to construct LMP_encryption_key_size_req
```

More precisely:

```text
+0xA7 is an output/reporting field written by firmware and read by:
    - InternalBlue info connections
    - HCI Read Encryption Key Size
```

It can be forged after negotiation. It does not prove that the negotiated LMP entropy was reduced.

A correct report statement would be:

> On BCM4345C0/RPi5, the connection-structure field at offset `+0xA7` controls the key size reported to InternalBlue and to the standard HCI `Read Encryption Key Size` command. However, writing arbitrary values to this byte after encryption is enabled does not immediately disrupt encrypted L2CAP traffic, even for invalid values such as `0x00`. Therefore, `HCI Read Encryption Key Size` alone is insufficient evidence of a successful KNOB downgrade on this platform.

This finding invalidates the earlier interpretation that the tested devices were confirmed vulnerable. With the evidence available today, we have not yet proven that the Samsung, JBL, iPhones, or iPad actually accepted `N = 1`. We proved that the RPi controller-side reported key size can be forged.

---

## 4. Updated Experimental Model

After the `+0xA7` result, we adopted a stricter model:

```text
unknown upstream source
        ↓
firmware builds / accepts LMP_encryption_key_size_req
        ↓
LMP negotiation determines N
        ↓
firmware computes K'C = Es(KC, N)
        ↓
firmware writes final/reported N into +0xA7
        ↓
InternalBlue and HCI report that value
```

Therefore, to perform real KNOB, we must influence something upstream of `+0xA7`, ideally one of:

```text
local_max_key_size
local_min_key_size
preferred_key_size
proposed_key_size
pending_negotiated_key_size
LMP TX buffer containing encryption_key_size_req
```

The Nexus 6P KNOB PoC used a RAM variable at `0x204147` on BCM4358A3. Our question became whether BCM4345C0 has an equivalent RAM variable. The existing project prompt already identified this as the key unresolved question. 

---

## 5. RAM Snapshot Work

### 5.1 Why `dumpmem` was not usable

We attempted to use InternalBlue `dumpmem`, but the command tried to create a template and read ROM sections:

```text
No template found. Need to read ROM sections as well!
```

This is incompatible with the RPi5/BCM4345C0 setup, where ROM reads fail or hang. This reinforced one of the earlier platform limitations:

```text
ROM is not readable
patchRom is unavailable
LMP monitor hooks are unavailable
dumpmem is unreliable because it tries to include ROM
```

The uploaded project notes already identify the relevant accessible RAM regions and the fact that ROM access on RPi5 is unavailable. 

### 5.2 Controlled hexdump snapshot

We switched to controlled `hexdump` snapshots of reliably readable RAM:

```text
0x000D0000 - 0x000D8000
0x00200000 - 0x00228000
```

Other nominal RAM regions such as:

```text
0x00260000
0x00280000
0x00318000
```

caused InternalBlue hexdump to hang, so they were excluded from the clean snapshot.

The final clean pre/post snapshot covered:

```text
196608 bytes
```

The parsed result was:

```text
bytes PRE  : 196608
bytes POST : 196608
common     : 196608
changed    : 1929
changed groups: 417
```

This gave us a valid, comparable pre/post memory diff.

---

## 6. Dynamic Candidates: Bytes That Became `0x10`

From the clean pre/post diff, we identified addresses that changed to `0x10` after connection establishment. These included:

```text
0x2002A8
0x2002CC
0x20557F
0x205590
0x206484
0x20649C
0x20F7A6
0x219190
0x219192
0x21C181
0x21C5A5
0x21D66E
0x21D675
0x21DEFD
```

The known `+0xA7` field was among them:

```text
0x20557F
```

which confirmed that the diff was meaningful.

We then inspected and tested several candidates.

### 6.1 `0x2002A8` and `0x2002CC`

These were initially thought to be candidates because they became `0x10` post-connection.

However, in the pre-connection state they contained `0x0A`, and attempts to write `0x01` did not persist. The value either remained `0x0A` or was immediately restored.

Classification:

```text
0x2002A8 → write not persistent / not testable with simple writemem
0x2002CC → write not persistent / not testable with simple writemem
```

### 6.2 `0x206484`

This address was zero before connection. We wrote:

```text
writemem 0x206484 01
```

The write persisted before and after connection. However, Samsung still connected with:

```text
Effective Key Len: 16 byte
HCI Read Encryption Key Size: 0x10
```

Classification:

```text
0x206484 → writable, persistent, no effect on N
```

### 6.3 `0x219190` and `0x219192`

Context inspection showed:

```text
0x219190: 28 56 20 00
```

which is a little-endian pointer:

```text
0x00205628
```

Therefore these were not safe entropy candidates.

Classification:

```text
0x219190 → pointer field, discarded
0x219192 → part of same pointer, discarded
```

### 6.4 `0x21D66E` and `0x21D675`

Context inspection showed SDP/L2CAP-like data patterns:

```text
35 xx
19 11 xx
09 xx xx
```

These are typical of Bluetooth SDP records and not LMP key-size negotiation fields.

Classification:

```text
0x21D66E → buffer / protocol data, discarded
0x21D675 → buffer / protocol data, discarded
```

---

## 7. Static Candidates: Stable `0x10` Fields

The dynamic candidate set did not reveal the upstream variable. We then considered that the true input might be stable at `0x10` both before and after connection, so it would not appear in a pre/post diff.

A first naive byte-level search produced many false positives, including bytes inside:

```text
0x00001000
pointers
SDP buffers
DRHT structures
literal pools / code-like regions
```

We improved the filter by looking for aligned values:

```text
u32 == 0x00000010
u16 == 0x0010
```

The cleaner report found:

```text
stable aligned u32 == 0x10: 9
stable aligned u16 == 0x10: 26
```

The top u32 candidates included:

```text
0x200704
0x201858
0x201968
0x201A5C
0x201FE8
0x20360C
0x203660
0x20AA90
0x20F75C
```

The cleaned candidate list is documented in the uploaded report. 

---

## 8. Static Candidate Tests

### 8.1 `0x20EBC0 / 0x20EBC2`

This became the most interesting intermediate structure.

Initial state:

```text
0x20EBC0: 10 00 10 00
```

This means two adjacent u16 values:

```text
0x20EBC0 = 0x0010
0x20EBC2 = 0x0010
```

We first wrote:

```text
writemem 0x20EBC0 01
```

In one early test, both fields appeared to become:

```text
01 00 01 00
```

This initially suggested coupling between the two fields.

However, a later ordered characterization showed a different and more reliable behavior:

```text
write 00 → 00 00 10 00
write 01 → 01 00 10 00
write 02 → 02 00 10 00
...
write 0F → 0F 00 10 00
write 10 → 10 00 10 00
write 11 → 11 00 10 00
write FF → FF 00 10 00
```

Therefore, the corrected interpretation is:

```text
0x20EBC0 = freely writable field
0x20EBC2 = stable 0x0010 field
```

When we wrote `0x20EBC2 = 0x01` before connection, the connection succeeded but the field was restored to `0x0010` during connection establishment, and Samsung still negotiated:

```text
Effective Key Len: 16 byte
```

Classification:

```text
0x20EBC0 → writable field, no evidence that it controls N
0x20EBC2 → more interesting intermediate field, but firmware restores it to 0x10 during connection
```

This area remains useful as a timing sensor, but not as a confirmed input.

### 8.2 `0x201FE8`

Context showed:

```text
30 bf 00 bf 00 bf 70 47 ...
```

This resembles Thumb code or a literal pool. When writing `0x01`, the value did not become `0x01`; it became `0x68`.

Classification:

```text
0x201FE8 → not controllable / likely code or literal-pool-adjacent
```

### 8.3 `0x20360C`

Context:

```text
02 00 00 00
04 00 00 00
08 00 00 00
10 00 00 00
```

This looked promising as a clean table of numeric values.

We wrote:

```text
writemem 0x20360C 01
```

The value persisted after connection:

```text
0x20360C = 01 00 00 00
```

However:

```text
0x20EBC0/C2 = 10 00 10 00
Effective Key Len = 16 byte
```

Classification:

```text
0x20360C → writable, persistent, no effect on N
```

### 8.4 `0x208A64`

This field was inside a structure containing pointers and `"DRHT"`-like metadata nearby. Writing:

```text
0x208A64 = 01
```

prevented Bluetooth connection. Writing:

```text
0x208A64 = 08
```

also broke the controller badly enough that a reboot was required.

Classification:

```text
0x208A64 → connection-critical structural field, unsafe to modify
```

### 8.5 `0x20A135 / 0x20A14D / 0x20A165 / 0x20A17D`

These initially appeared as stable `0x10` byte candidates. Context inspection showed they were actually bytes inside aligned values:

```text
00 10 00 00 = 0x00001000
```

These likely represent buffer sizes or offsets, not key sizes.

Classification:

```text
0x20A135, 0x20A14D, 0x20A165, 0x20A17D
→ discarded as 0x1000 fields, not 16-byte entropy fields
```

### 8.6 `0x200704`

This was a clean aligned u32 candidate.

We wrote:

```text
writemem 0x200704 01
```

The value persisted before and after connection:

```text
0x200704 = 01 00 00 00
```

But Samsung still connected with:

```text
Effective Key Len: 16 byte
0x20EBC0/C2 = 10 00 10 00
```

Classification:

```text
0x200704 → writable, persistent, no effect on N
```

### 8.7 `0x201858`

This candidate was also tested and produced no useful effect.

Classification:

```text
0x201858 → no effect on N
```

---

## 9. Current Candidate Status

The current state of the candidate search is:

```text
+0xA7 / 0x20557F
    → confirmed reporting/output field
    → not real input

0x2002A8
    → write not persistent

0x2002CC
    → write not persistent

0x206484
    → writable, persistent, no effect

0x219190 / 0x219192
    → pointer, discarded

0x21D66E / 0x21D675
    → SDP/L2CAP buffer, discarded

0x20EBC0
    → writable field, likely not key-size input

0x20EBC2
    → intermediate 0x0010 field
    → restored to 0x10 during connection
    → still interesting as timing sensor

0x201FE8
    → code/literal-pool-like, not controllable

0x20360C
    → writable, persistent, no effect

0x208A64
    → connection-critical; writing 1 or 8 breaks connection

0x20A135 / 0x20A14D / 0x20A165 / 0x20A17D
    → actually 0x00001000 fields, discarded

0x200704
    → writable, persistent, no effect

0x201858
    → no effect
```

Still to inspect/test carefully:

```text
0x203660
0x20F75C
0x210D1C / 0x210D1E
possibly 0x20EBC2 timing behavior
```

---

## 10. Important btmon Timing

A btmon trace during connection showed:

```text
Connect Complete:       t = 110.677284
Encryption Change:      t = 110.781149
```

So the time between connection completion and encryption becoming active was approximately:

```text
104 ms
```

This matters because any race-style `writeMem` approach must occur before the firmware computes or loads the final encryption key. This window is narrow and may be too short for reliable HCI-based memory writes.

---

## 11. What We Have Demonstrated Today

### 11.1 Strong findings

We demonstrated:

```text
1. +0xA7 is not sufficient to perform KNOB.
2. +0xA7 controls reported key size, not proven cryptographic entropy.
3. HCI Read Encryption Key Size can be forged by RAM write.
4. Invalid HCI key sizes such as 0x00 and 0xff can be reported.
5. L2CAP traffic can continue while HCI reports impossible key sizes.
6. Several plausible RAM candidates do not affect negotiation.
7. Some fields are structural and can break the controller.
8. 0x20EBC2 is an interesting intermediate field but is restored to 16 during connection.
```

The most important conceptual result is:

> A reported key size of 1 byte is not sufficient evidence of a real KNOB downgrade when the attacker has RAM write access to the controller.

This is the main scientific turning point of today’s work.

### 11.2 What we have not demonstrated

We have not yet demonstrated:

```text
1. that the Samsung accepted LMP N = 1;
2. that any tested device computed K'C with 1 byte of entropy;
3. that encrypted traffic can be brute-forced in 256 attempts;
4. that we can modify the real LMP encryption_key_size_req packet;
5. that we have found the BCM4345C0 equivalent of Nexus 6P's 0x204147.
```

Therefore, we should not currently claim:

```text
"KNOB confirmed on Samsung / JBL / iPhone / iPad"
```

The correct claim is:

```text
"The RPi5/BCM4345C0 controller-side reported key size can be modified to arbitrary values, including 1, 0, and 255, but this does not by itself prove a real KNOB downgrade."
```

---

## 12. Remaining Work

The next steps should be:

### 12.1 Finish the clean static-candidate tests

Still inspect/test carefully:

```text
0x203660
0x20F75C
0x210D1C / 0x210D1E
```

Avoid:

```text
pointers
DRHT structures
SDP/L2CAP buffers
fields that caused reboot
```

### 12.2 Characterize `0x20EBC2` timing

The most informative next experiment is to poll:

```text
0x20EBC0 / 0x20EBC2
```

during connection establishment after setting:

```text
0x20EBC2 = 0x01
```

Goal:

```text
observe exactly when it returns to 0x10
```

If it returns to `0x10` well before `Encryption Change`, we may test whether a race-write after restoration can affect the negotiation.

If it returns to `0x10` immediately or atomically with LMP negotiation, HCI-based `writemem` is probably too slow.

### 12.3 Look for transient buffers

Static pre/post snapshots may miss variables that exist only briefly. The real source may be:

```text
temporary stack variable
LMP TX buffer
runtime connection negotiation struct
ROM constant copied just-in-time
```

Therefore, a future strategy should involve high-frequency polling of selected RAM areas during:

```text
Connect Complete
→ authentication
→ encryption setup
→ Encryption Change
```

### 12.4 Consider HCD / patchram reverse engineering

If RAM-variable search fails, the next serious path is static reverse engineering:

```text
extract HCD patchram
parse patchram table
identify ROM patch targets
compare with similar Broadcom/Cypress chips
try function matching with known KNOB PoC targets
```

This may be the only way to recover LMP-related hook points without a ROM dump.

---

## 13. Current Research Interpretation

At the end of today’s session, our best model is:

```text
true source of N is still unknown
        ↓
firmware initializes intermediate runtime fields such as 0x20EBC2 to 16
        ↓
firmware performs LMP entropy negotiation
        ↓
firmware computes K'C using negotiated N
        ↓
firmware writes final/reported value into connection_struct + 0xA7
        ↓
HCI/InternalBlue report that value
```

The source is probably not a simple static RAM byte among the candidates tested so far. It may be:

```text
a ROM constant
a transient stack/local variable
a short-lived LMP packet buffer
a runtime field outside the reliably dumpable RAM regions
a structure initialized too late for pre-connection writemem
```

---

## 14. Suggested Report Claim

A safe and strong claim for the repository/report is:

> We initially identified `connection_struct + 0xA7` as the field controlling the key size displayed by InternalBlue. However, controlled experiments showed that this field is not sufficient to prove or perform a real KNOB downgrade. After overwriting it post-negotiation, both InternalBlue and the standard HCI `Read Encryption Key Size` command report arbitrary values, including invalid sizes such as `0x00` and `0xff`, while encrypted L2CAP traffic remains functional. Therefore, on BCM4345C0/RPi5, the HCI-reported key size can be forged through controller RAM modification and cannot be used alone as evidence that the actual link-layer encryption key entropy was reduced.

A second safe claim is:

> We performed a systematic RAM search for an upstream BCM4345C0 variable equivalent to the Nexus 6P KNOB PoC RAM variable. Several dynamic and static candidates were tested. None of the tested candidates successfully forced a final negotiated key size of 1 byte. Some fields were writable but had no effect, while others were structural and caused connection failure. The most interesting intermediate field found so far is `0x20EBC2`, which stores `0x0010` and is restored by firmware during connection establishment.

Final status:

```text
Real KNOB not yet achieved.
False-positive KNOB evidence disproven.
Firmware/reporting behavior mapped more accurately.
Search for upstream source still open.
```
  

## 2026-05-21 — Session Marco Stocco + Riccardo Citron

### Session Objective
Complete Phase 4 of the project: derive the session key K'C with 1 byte of entropy from the real cryptographic parameters captured during the KNOB attack on the Samsung Galaxy Ace Style 2014. In parallel, extend vulnerability testing to new Apple devices with Riccardo Citron.

---

### Original Findings Discovered Today

#### Finding #10 — Complete BCM4345C0 Connection Struct RAM Map, Cryptographically Verified
The RAM structure of the BCM4345C0 chip's connection struct (fw 003.001.025 build 0382) has been mapped with absolute precision and cryptographically verified across **3 independent sessions**:

| Offset from slot_base | Size | Content | Status |
|---|---|---|---|
| +0x60 | 16B | KL (Link Key) | ✅ verified |
| +0x70 | 16B | AU_RAND | ✅ verified |
| +0x80 | 4B | SRES | ✅ verified vs LMP_sres |
| +0x84 | 12B | ACO | ✅ verified vs E1 computation |
| +0xA7 | 1B | Effective Key Len | ✅ verified |

For each session we computed `SRES, ACO = E1(KL, AU_RAND, BTADD_S)` and compared against values read directly from RAM — perfect match in all 3 sessions. This constitutes a **cryptographic proof of the RAM map**, never before published for this chip.

Verified sessions:
- Session 1: AU_RAND=`531245d6...`, SRES=`2b819d2e` ✅, ACO=`493fde1d...` ✅
- Session 2: AU_RAND=`df67ca8b...`, SRES=`759b89dd` ✅, ACO=`376aad38...` ✅
- Session 3: AU_RAND=`4fe2a831...`, SRES=`f9ccfc43` ✅, ACO=`81238759...` ✅

#### Finding #11 — Public RAND in InternalBlue = AU_RAND (not EN_RAND)
The `Public RAND` field shown by `info connections` in InternalBlue is **AU_RAND**, not EN_RAND as erroneously assumed in all online writeups citing InternalBlue. Confirmed by comparing the value shown by InternalBlue with the one at offset +0x70 in the connection struct and with LMP_au_rand packets captured in the pcap.

This corrects a mistaken assumption present in the informal InternalBlue documentation circulating online.

#### Finding #12 — Second Copy of AU_RAND at 0x21DBF0
Through systematic RAM dumping of BCM4345C0 (range 0x200000–0x227FFF, 163840 bytes) and multi-session diff analysis, a **second occurrence of AU_RAND** was identified at fixed address `0x21DBF0`. This area is stable across sessions and distinct from the connection struct at `0x205550`.

#### Finding #13 — Cryptographic Scratch Area at 0x21D244–0x21D384
The RAM region `0x21D244–0x21D384` has been identified as the **E3/SAFER+ algorithm working area** of the BCM4345C0 firmware. Characteristics:
- High entropy in all sessions
- Content changes completely each session
- AU_RAND appears within the region during/after the E3 computation
- Values change on a millisecond timescale during the encryption handshake

This is the first published mapping of the BCM4345C0 cryptographic scratch area.

#### Finding #14 — KC Not Persisted in RAM After E3
Through systematic RAM dumps across 3 sessions and full diff analysis of accessible RAM (0x200000–0x227FFF), it was determined that **KC is not persisted in the connection struct** after E3 consumes it. The firmware computes KC, uses it to initialize E0/AES-CCM, then overwrites it or does not save it to an accessible location. This is a security finding: the Broadcom firmware design prevents software extraction of session keys even on chips vulnerable to KNOB.

#### Finding #15 — EN_RAND Not Accessible via Software on BCM4345C0
All known software methods to obtain EN_RAND on BCM4345C0/RPi5 were systematically tested:
- BlueZ `vendor_diag` + Wireshark: does not work on UART-attached Broadcom (debugfs interface absent or unusable)
- InternalBlue `monitor start` + tshark on bluetooth0: Patchram hooks are installed ~14 seconds after the connection, EN_RAND already exchanged
- Samsung Ace 2014 HCI btsnoop: EN_RAND does not pass to the host HCI on any tested chip
- `HCI_Refresh_Encryption_Key` (opcode 0x0438): not supported by the BCM4345C0 controller
- `sendlmp LMP_encryption_mode_req/stop_encryption`: ignored by Samsung (RPi is slave)
- RAM dump at critical timing: scratch area overwritten before dump completes
- ROM analysis: ROM not readable on RPi5 (Spectra mitigations, error 0x12)

**Documented conclusion:** EN_RAND is generated and consumed internally by the BCM4345C0 firmware during E3 and is not accessible via any software interfaces available on Raspberry Pi OS. No public paper or writeup has ever extracted EN_RAND via software from BCM4345C0.

#### Finding #16 — iPhone 16 Pro (2024) with AES-CCM Vulnerable to KNOB
The KNOB attack was successfully demonstrated on **iPhone 16 Pro (2024)** using AES-CCM (Secure Connections). This extends the confirmed vulnerability to the latest Apple devices, not present in the original USENIX 2019 paper's list. The original paper tested devices up to 2019; this is the first public report of KNOB confirmed on iPhone 16 Pro.

**Technical details:** with AES-CCM and L=1, the 256 K'C candidates take the form `0xXX000000000000000000000000000000` (most significant byte variable, rest zero) — computationally trivial brute force.

#### Finding #17 — Offset +0xA7 Universal on BCM4345C0, Confirmed on 5 Devices
The `+0xA7` offset for the `effective_key_len` field in the BCM4345C0 connection struct has been confirmed on all tested devices:

| Device | Encryption | Offset | Confirmed |
|---|---|---|---|
| Samsung Galaxy Ace Style 2014 | E0 | +0xA7 | ✅ |
| Samsung Galaxy A34 5G 2024 | E0 | +0xA7 | ✅ |
| JBL Clip 2 | E0 | +0xA7 | ✅ |
| iPhone 6S | E0 | +0xA7 | ✅ |
| iPhone 16 Pro | AES-CCM | +0xA7 | ✅ |
| MacBook Air M2 2022 | AES-CCM | +0xA7 | ✅ |
| iPad A16 (iPadOS 26) | AES-CCM | +0xA7 | ✅ |  

Independent of: encryption type, master/slave role, iOS/Android version, device year.

---

### Updated Vulnerability Table

| Device | BD Address | Encryption | Vulnerable | key_len_addr | RPi Role | Notes |
|---|---|---|---|---|---|---|
| JBL Clip 2 | 40:EF:4C:8C:88:DF | E0 | ✅ | variable | Master | variable slot |
| Samsung Galaxy Ace Style 2014 | F8:84:F2:62:96:AA | E0 | ✅ | 0x20557F | Slave | stable slot, stable KL |
| Samsung Galaxy A34 5G 2024 | AC:80:FB:21:85:32 | E0 | ✅ | 0x20557F | Slave | stable slot |
| iPhone 6S | 00:B3:62:93:89:12 | E0 | ✅ | 0x2056CF | Slave | slot 1, KL=`877779624ab464c66a93c4092608b255` |
| iPhone 16 Pro 2024 | 90:B7:90:09:34:92 | AES-CCM | ✅ | 0x20557F | Slave | Secure Connections, slot 7 |
| MacBook Air M2 2022 | A8:8F:D9:35:0C:FE | AES-CCM | ✅ | 0x20557F | Slave | Secure Connections |
| iPad A16 (iPadOS 26) | 30:C0:AE:2D:B4:BE | AES-CCM | ✅ | 0x20557F | Slave | Secure Connections |

---

### Activities Completed Today

#### Part 1 — Cryptographic Analysis Samsung Ace 2014 (Phase 4)

**09:00–10:00 — KC Search in Connection Struct**
Attempted to locate KC (E3 output) in the connection struct through RAM dump analysis. Identified that the block at offset +0x80 contains SRES (4B) and ACO (12B), not KC. KC is not persisted in the struct after E3 consumes it.

**10:00–11:00 — InternalBlue LMP Monitor Fix**
Identified and resolved the `monitor start` command issue: InternalBlue launches `wireshark -k -i bluetooth0` but tshark terminates immediately with the `-k` flag (GUI-only). Fix applied directly to `~/internalblue/venv/lib/python3.13/site-packages/internalblue/cli.py` by modifying the subprocess to use `tshark -i bluetooth0 -w /tmp/lmp_monitor.pcap`. Added poll timer logging for debug (`_pollTimer: exit code = None` confirms process is alive).

**11:00–12:00 — EN_RAND Capture Attempts via LMP Monitor**
With monitor active and tshark capturing: Patchram hooks (0xFC4D) are installed ~14 seconds after the connection, after EN_RAND has already been exchanged. Structural problem: hooks are not pre-installed before the connection.

**12:00–13:00 — Samsung btsnoop Analysis and HCI Attempts**
Pulled and analyzed Samsung Ace 2014 btsnoop: contains only `Encryption Change`, EN_RAND does not pass to the host HCI. Attempted `HCI_Refresh_Encryption_Key` (0x0438): not supported by the controller. Attempted `sendlmp`: ignored by Samsung.

**13:00–14:30 — Systematic RAM Dump and Diff Analysis**
Full BCM4345C0 RAM dump (163840 bytes, 0x200000–0x227FFF) via `dumpmem -r`. Diff analysis across 3 independent sessions. Discoveries: cryptographic scratch area at 0x21D244, second AU_RAND copy at 0x21DBF0, SRES+ACO mathematically verified for 3 sessions. KC not found — non-persistence in accessible RAM confirmed.

**14:30–15:00 — sendlmp Re-keying Attempt**
Sent `LMP_encryption_mode_req` (opcode 15) and `LMP_stop_encryption` (opcode 16) via `sendlmp --slave`. Samsung ignores both messages — correct behavior from the protocol's perspective (slave should not send these messages). No re-keying triggered.

#### Part 2 — New Apple Device Testing (with Riccardo Citron)

Tests completed on iPhone 6S, iPhone 16 Pro, and MacBook Air M2 2022. Results documented in the vulnerability table. Main finding: iPhone 16 Pro and MacBook Air M2 2022 with AES-CCM are vulnerable — extending the vulnerability to 2022–2024 devices.

---

### Obstacles Encountered and Analysis

**Main obstacle: EN_RAND not extractable via software**
All known methods and some new ones were attempted. The conclusion is that the BCM4345C0 firmware is designed (intentionally or not) such that EN_RAND is generated and consumed internally without ever being exposed to the host or in accessible RAM locations after E3 completes. This is paradoxically a robustness point in an otherwise KNOB-vulnerable chip.

**Secondary obstacle: scratch area timing**
The E3 working area (0x21D244) is overwritten within milliseconds. Manual dumps via InternalBlue CLI lack the temporal resolution needed to capture KC during computation.

**Tertiary obstacle: LMP monitor timing**
The `monitor start` Patchram hooks are installed after the encryption handshake, not before. Would require a hook pre-installation mechanism before the connection, not supported by InternalBlue's current HCICore architecture.

---

### Phase 4 Current Status

**Completed:**
- ✅ Connection struct RAM map cryptographically verified (3 sessions)
- ✅ E1 verified: SRES and ACO computed and confirmed
- ✅ EN_RAND not extractable: documented as original finding
- ✅ KC not persisted in RAM: documented

**To be completed:**
- 🔄 K'C computation using synthetic EN_RAND (original paper methodology, Section 4.3)
- 🔄 Generation of all 256 K'C candidates for brute force
- 🔄 Formal documentation of "EN_RAND not extractable on BCM4345C0" finding

---

### Next Objectives

#### Priority 1 — Complete Phase 4 (K'C computation)
Use synthetic EN_RAND to complete the E1→E3→Es chain, exactly as done in the original KNOB paper (Table 2, Section 4.3). Explicitly document that EN_RAND is synthetic and explain why — this is academically correct and constitutes in itself an original finding on EN_RAND non-extractability from BCM4345C0.

Script to complete in `~/knob_work/knob/e0/`:
```python
KL      = bytearray.fromhex('f28bc3dc14fc8432aafbab1a4bc44c26')
AU_RAND = bytearray.fromhex('<from current session>')
EN_RAND = bytearray.fromhex('<synthetic, chosen>')  # document as synthetic
BTADD_S = bytearray.fromhex('aa9662f284f8')

SRES, ACO = e1(KL, AU_RAND, BTADD_S)
KC        = e3(KL, EN_RAND, ACO)
Kc_prime  = Kc_to_Kc_prime(KC, 1)

# Generate all 256 K'C candidates
for i in range(256):
    kc_mod = bytearray(KC); kc_mod[0] = i
    print(f'{i:3d}: {Kc_to_Kc_prime(kc_mod, 1).hex()}')
```

#### Priority 2 — SRES/ACO Verification on Other Devices
Replicate the cryptographic verification (Finding #10) on JBL Clip 2, iPhone 6S, iPhone 16 Pro, and MacBook Air M2 2022 to confirm that the +0xA7 map and RAM structure are universal regardless of the remote device.

#### Priority 3 — Apple Watch Testing
Not tested today — potential original finding (not in the KNOB 2019 paper's list).

#### Priority 4 — KNOB_PoC_BCM4345C0.py Automation
Complete the script with:
- Auto-discovery of slot by BD address
- Automatic writemem
- Post-attack verification
- Structured output for documentation

#### Priority 5 — Final Documentation
- Complete README with methodology and findings
- Update vulnerability_table.md
- Attack demo video
- Academic submission consideration

---

### Files Modified Today

| File | Change |
|---|---|
| `~/internalblue/venv/lib/python3.13/site-packages/internalblue/cli.py` | LMP monitor fix: use tshark instead of Wireshark GUI; added poll timer logging |
| `~/knob_work/bcm4345_ram.bin_0x200000` | RAM dump session 1 (163840 bytes) |
| `~/knob_work/bcm4345_ram2.bin_0x200000` | RAM dump session 2 |
| `~/knob_work/bcm4345_ram3.bin_0x200000` | RAM dump session 3 |
| `~/knob_work/btsnoop_samsung.log` | Samsung Ace 2014 btsnoop analyzed |
| `docs/vulnerability_table.md` | Updated with iPhone 6S, iPhone 16 Pro, MacBook Air M2 2022 |

---

### Technical References for Next Session

**E3 scratch area address:** `0x21D244–0x21D384`
**Second AU_RAND copy:** `0x21DBF0`
**Samsung Ace 2014 KL (stable):** `f28bc3dc14fc8432aafbab1a4bc44c26`
**Samsung BTADD_S (little-endian):** `aa9662f284f8`
**iPhone 6S KL:** `877779624ab464c66a93c4092608b255`
**E0 Python module:** `~/knob_work/knob/e0/` (e1.py, e3.py, es.py — all working with Python 3.13)
  
## Session 2026-05-20 — Phase 4: E0 Brute Force & Cryptographic Key Derivation

### Devices Tested
- Samsung Galaxy Ace Style 2014 — SM-G310HN — BD Address: F8:84:F2:62:96:AA (primary target)
- JBL Clip 2 — 40:EF:4C:8C:88:DF (referenced, not used today)

---

### Part 1 — E0 Encryption Confirmed on Samsung Ace Style 2014

#### Result
✅ E0 encryption confirmed on Samsung Galaxy Ace Style 2014

From btmon log `knob_samsung_ace_phase4_v2.log`:
```
> HCI Event: Encryption Change (0x08) plen 4   #47 [hci0] 9.387126
        Encryption: Enabled with E0 (0x01)
        Key size: 16  ← host reads this ONCE before writemem
```

Timeline proof from log:
- writemem (key→1): timestamp 21.889297
- First L2CAP Echo Request: timestamp 92.330685

Traffic was generated **70 seconds after** writemem with key=1 active.
Host reads Key size once at connection time and never re-reads it — the host
believes key=16 while firmware uses key=1. This is the core KNOB vulnerability.

---

### Part 2 — Key Size Reduction Confirmed During l2ping Traffic

20 L2CAP Echo Request/Response cycles completed with Effective Key Len = 1 byte,
Samsung remained connected without error or disconnection.
btmon shows traffic after writemem — confirms behavioral vulnerability.

---

### Part 3 — E0 Brute Force Tool Setup

#### francozappa/knob e0/ module setup on RPi5
- Cloned: `~/knob_work/knob/`
- Fixed Python 2→3 incompatibilities:
  - `bf.py`: replaced `imap` with `map`
  - `Makefile`: replaced `python2` with `python3`
  - `constants.py`: updated `E0_IMPL_PATH` to `/home/marco/knob_work/knob/e0/e0`
- Installed: `bitstring` via pip
- `bf_tests.py` passes with Python 3.13 ✅

---

### Part 4 — Critical Finding: btmon Cannot Capture E0 Ciphertext

btmon/HCI receives traffic ALREADY DECRYPTED by the BCM4345C0 chip.
The chip decrypts all traffic before passing it to the host via HCI.
Therefore, E0 ciphertext is NOT available via btmon for brute force.
Ubertooth One would be required for over-the-air capture.

---

### Part 5 — Cryptographic Key Derivation Attempt (Mathematical Brute Force)

#### Goal
Compute K'C (the actual 1-byte entropy session key) using:
- E1(KL, AU_RAND, BTADD_S) → SRES + ACO
- E3(KL, EN_RAND, ACO) → KC
- Es(KC, N=1) → K'C

#### Critical Finding: Public RAND in InternalBlue = AU_RAND (NOT EN_RAND)

**This is an original finding.** Previous sessions incorrectly assumed
`Public RAND` = EN_RAND. Today we proved via LMP packet capture that:
- `Public RAND` shown in `info connections` = **AU_RAND** (LMP_au_rand, opcode 11)
- EN_RAND is a different parameter exchanged in LMP_start_encryption_req (opcode 0x24)

Proof: Packet 90 in `lmp_monitor.pcap`:
```
opcode byte 0x17 → opcode = 0x17 >> 1 = 11 = LMP_au_rand
payload = 3a8fbe4e32d349750fb211d923c7e7ca = Public RAND value ✅
```

#### SRES Verification

For session with AU_RAND = `3a8fbe4e32d349750fb211d923c7e7ca`:
- BTADD_S must be used in **little-endian** format: `aa9662f284f8` (not `f884f26296aa`)
- E1(KL, AU_RAND, BTADD_S_le) → SRES = `d1e5d27b` ✅ (verified in LMP_sres packet 93)

#### RAM Structure Discovery — Connection Struct Offsets (BCM4345C0)

From hexdump of slot base (e.g. `0x205628`):

| Offset | Size | Content |
|--------|------|---------|
| +0x60  | 16B  | KL (Link Key) |
| +0x70  | 16B  | AU_RAND |
| +0x80  | 4B   | SRES |
| +0x84  | 12B  | ACO |
| +0x90+ | ?    | EN_RAND (NOT FOUND — likely not stored after encryption setup) |

ACO verified for session: `bece53e50ac191b28985174f` ✅

---

### Part 6 — LMP Packet Capture via Broadcom Vendor Diagnostics

#### Setup
```bash
echo 1 | sudo tee /sys/kernel/debug/bluetooth/hci0/vendor_diag
sudo ln -s /usr/bin/tshark /usr/bin/wireshark
sudo wireshark -i bluetooth-monitor -w /tmp/lmp_monitor.pcap &
```

**Key insight:** Must use `bluetooth-monitor` interface (NOT `bluetooth0`) to capture
Broadcom vendor diagnostic packets containing LMP.

#### h4bcm Wireshark Dissector
- Plugin `h4bcm.dll` found in release folder of h4bcm_wireshark_dissector repo
- Installed to `C:\Users\marco\AppData\Roaming\Wireshark\plugins\4.6\`
- NOT compatible with Wireshark 4.6.4 (compiled for older versions)
- Packets visible as raw bytes under `Opcode: Vendor Diagnostic (11)` in HCI_MON

#### LMP Packet Format (Broadcom Diagnostic)
```
[0x0000000b] [dir(1)] [padding(3)] [handle(1)] [BD_addr_partial(4)] [handle2(2)] [len(2)] [opcode_byte(1)] [payload...]
```
- opcode_byte = (lmp_opcode << 1) | tid
- LMP_au_rand: opcode=11, byte=0x16/0x17
- LMP_sres: opcode=12, byte=0x18/0x19
- LMP_start_encryption_req: opcode=0x24, byte=0x48/0x49

---

### Part 7 — What Is Still Missing

**EN_RAND** is the only missing parameter.

EN_RAND is exchanged in `LMP_start_encryption_req` which occurs in the first ~500ms
of connection setup. It has NOT been captured in any pcap yet because:
1. `vendor_diag` resets after each reboot/reconnection
2. The encryption setup happens faster than the capture window in our current workflow

#### Solution for Next Session
The EXACT sequence to capture EN_RAND:
```bash
# Step 1: Enable vendor_diag FIRST
echo 1 | sudo tee /sys/kernel/debug/bluetooth/hci0/vendor_diag

# Step 2: Start capture
sudo wireshark -i bluetooth-monitor -w /tmp/lmp_enrand.pcap &

# Step 3: Disconnect Samsung (if connected)
# bluetoothctl: disconnect F8:84:F2:62:96:AA

# Step 4: Reconnect Samsung  
# bluetoothctl: connect F8:84:F2:62:96:AA

# Step 5: IMMEDIATELY stop capture (within 2 seconds of connection)
sudo kill $(pgrep -f wireshark)

# Step 6: Analyze - look for opcode 0x48/0x49 (LMP_start_encryption_req)
# EN_RAND = 16 bytes after the opcode byte
```

Then compute K'C:
```python
SRES, ACO = e1(KL, AU_RAND, BTADD_S_le)  # BTADD_S in little-endian
KC = e3(KL, EN_RAND, ACO)
Kc_prime = Kc_to_Kc_prime(KC, 1)
# Verify: Kc_prime[0] == 0xf2 (first byte visible in InternalBlue after writemem)
```

---

### Summary of Original Findings from Today

1. **Public RAND in InternalBlue = AU_RAND** (not EN_RAND as previously assumed)
2. **BTADD_S must be little-endian** for E1 computation on BCM4345C0
3. **RAM struct offsets confirmed**: KL@+0x60, AU_RAND@+0x70, SRES@+0x80, ACO@+0x84
4. **EN_RAND is NOT stored in RAM** after encryption setup completes
5. **Broadcom vendor_diag LMP capture works** via `bluetooth-monitor` interface
6. **LMP packet format decoded**: opcode = byte >> 1, BTADD in little-endian in packets
7. **SRES verified mathematically**: E1(KL, AU_RAND, BTADD_S_le) = SRES from LMP_sres packet ✅
8. **ACO computed and verified**: from E1 output ✅
9. **btmon cannot capture E0 ciphertext** — chip decrypts before HCI

### Next Step
Capture EN_RAND from LMP_start_encryption_req using the exact sequence above,
then complete K'C computation and demonstrate mathematical brute force of all 256 candidates.  

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
