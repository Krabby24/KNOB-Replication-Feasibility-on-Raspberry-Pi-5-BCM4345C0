# Captures and Logs

This directory is reserved for capture-related documentation.

Raw Bluetooth captures, full `btmon` traces, memory dumps, and device logs are not committed to this repository by default because they may be large, hardware-specific, or contain device identifiers.

The final report and the documentation files in `docs/` include the relevant extracted evidence, including:

- the key false-positive validation timeline;
- relevant `Encryption Change` and `Read Encryption Key Size` events;
- Samsung-side HCI snoop timeline excerpts;
- RAM candidate summaries;
- interpretation of the collected traces.

## Main Evidence Preserved in Documentation

The decisive false-positive validation sequence was:

```text
7.516985   Encryption Change
7.517704   Read Encryption Key Size -> Key size: 16

40.384067  Read Encryption Key Size -> Key size: 0

50.359434  Read Encryption Key Size -> Key size: 1
