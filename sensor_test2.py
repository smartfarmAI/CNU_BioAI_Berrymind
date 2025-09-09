#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#
# Copyright (c) 2025 tombraid@snu.ac.kr
# All right reserved.
#

import json
import yaml
import sys
from pymodbus.client import ModbusTcpClient

# Add project root to path to allow module imports
sys.path.append('.')

from sfai25.KSB7958.ksconstants import STATCODE
from action_io_component.utils import unpack_f32, unpack_i32


# Load Modbus configuration
with open('sfai25/KSB7958/conf.json', 'r') as f:
    config = json.load(f)

# Load sensor map
with open('action_io_component/register_map_split_status.yaml', 'r') as f:
    sensor_map = yaml.safe_load(f)

# Since we are not connected to a real sensor, we will simulate the client.
# To test with a real sensor, comment out the following mock classes and 
# uncomment the client connection lines.

class MockRegisterResponse:
    def __init__(self, registers):
        self._registers = registers

    @property
    def registers(self):
        return self._registers

    def isError(self):
        return False

class MockModbusClient:
    def connect(self):
        print("Mock Modbus client connected.")
        return True

    def read_holding_registers(self, start_addr, count, slave):
        print(f"[SIM] Reading {count} registers from addr {start_addr} on device {slave}")
        # Simulate some realistic data
        if slave == 2 and start_addr == 203: # outdoor_temp
            return MockRegisterResponse([17766, 16672, 1]) # ~25.5 degrees, status OK
        if slave == 4 and start_addr == 203: # fcu_opid
            return MockRegisterResponse([101])
        # Default response
        return MockRegisterResponse([0] * count)

    def close(self):
        print("Mock Modbus client closed.")

# --- Simulation Setup ---
client = MockModbusClient()

# --- Real Device Setup (currently commented out) ---
# client = ModbusTcpClient(config['modbus_ip'], port=config['modbus_port'])

if not client.connect():
    print("Modbus 서버에 연결할 수 없습니다.")
    exit()

devices = sensor_map.get('devices', {})
for device_id, device_info in devices.items():
    print(f"--- Device ID: {device_id} ---")
    values = device_info.get('values', {})
    statuses = device_info.get('status', {})

    for name, info in values.items():
        addr = info.get('addr')
        dtype = info.get('dtype')

        # Handle multi-register values (e.g., float32, int32)
        if isinstance(addr, list):
            start_addr = addr[0]
            num_regs = len(addr)
            status_info = statuses.get(f"{name}_status")
            
            read_count = num_regs
            # If there's a corresponding status register and it's contiguous, read it too.
            if status_info and status_info.get('addr') == start_addr + num_regs:
                read_count += 1

            res = client.read_holding_registers(start_addr, count=read_count, slave=device_id)

            if res.isError():
                print(f"  - {name}: 정보 읽기 실패")
            else:
                regs = res.registers
                value = None
                if dtype == 'float32' and len(regs) >= 2:
                    value = unpack_f32(regs[0], regs[1])
                elif dtype == 'int32' and len(regs) >= 2:
                    value = unpack_i32(regs[0], regs[1])
                else:
                    value = regs[0] # Fallback for unexpected cases
                
                status_text = ""
                if status_info and read_count > num_regs and len(regs) >= read_count:
                    status_val = regs[num_regs]
                    status_text = f" (상태: {'정상' if status_val == STATCODE.READY else '비정상'})"
                
                print(f"  - {name}: {value}{status_text}")

        # Handle single-register values (no dtype specified)
        else:
            res = client.read_holding_registers(addr, count=1, slave=device_id)
            if res.isError():
                print(f"  - {name}: 정보 읽기 실패")
            else:
                value = res.registers[0]
                print(f"  - {name}: {value}")

client.close()

