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
import struct
from pymodbus.client import ModbusTcpClient

# Add project root to path to allow module imports
sys.path.append('.')

from sfai25.KSB7958.ksconstants import STATCODE
from action_io_component.utils import unpack_f32, unpack_i32

def process_device(client, device_id, device_info):
    """Reads a block of data for a single device and parses it."""
    print(f"--- Device ID: {device_id} ---")

    all_addrs = []
    # Combine all addresses to find the required range for this device
    for group in ['values', 'status']:
        for item_info in device_info.get(group, {}).values():
            addr = item_info.get('addr')
            if isinstance(addr, list):
                all_addrs.extend(addr)
            else:
                all_addrs.append(addr)

    if not all_addrs:
        print("  - 이 장치에 정의된 주소가 없습니다.")
        return

    min_addr = min(all_addrs)
    max_addr = max(all_addrs)
    read_count = max_addr - min_addr + 1

    print(f"  - Reading block from {min_addr} to {max_addr} (count: {read_count})...")
    res = client.read_holding_registers(min_addr, count=read_count, slave=device_id)

    if res.isError():
        print("  - 블록 읽기 실패")
        return

    block = res.registers

    # Parse the fetched block for each sensor
    for name, info in device_info.get('values', {}).items():
        addr = info.get('addr')
        dtype = info.get('dtype')
        status_info = device_info.get('status', {}).get(f"{name}_status")

        value_str = f"  - {name}: "
        try:
            if isinstance(addr, list):  # Multi-register value (float32, int32)
                offset = addr[0] - min_addr
                reg1 = block[offset]
                reg2 = block[offset + 1]
                value = None
                if dtype == 'float32':
                    value = unpack_f32(reg1, reg2)
                elif dtype == 'int32':
                    value = unpack_i32(reg1, reg2)
                value_str += str(value)
            else:  # Single register value
                offset = addr - min_addr
                value = block[offset]
                value_str += str(value)

            # Check for status if it exists
            if status_info:
                status_addr = status_info['addr']
                status_offset = status_addr - min_addr
                status_val = block[status_offset]
                status_text = 'OK' if status_val == STATCODE.READY else 'ERROR'
                value_str += f" (Status: {status_text})"
            
            print(value_str)

        except IndexError:
            print(f"  - {name}: 파싱 오류 (주소 범위 문제)")
        except Exception as e:
            print(f"  - {name}: 파싱 중 알 수 없는 오류 발생: {e}")

class MockRegisterResponse:
    def __init__(self, registers):
        self._registers = registers

    @property
    def registers(self):
        return self._registers

    def isError(self):
        return False

class MockModbusClient:
    def __init__(self, sensor_map):
        self.sensor_map = sensor_map
        self.mock_data = {}
        self._initialize_mock_data()

    def _initialize_mock_data(self):
        # Helper to pack float into two 16-bit registers
        def pack_float(v):
            return struct.unpack('HH', struct.pack('f', v))

        # Helper to pack int32 into two 16-bit registers
        def pack_int32(v):
            return struct.unpack('HH', struct.pack('i', v))

        for device_id, device_info in self.sensor_map.get('devices', {}).items():
            all_addrs = []
            for group in ['values', 'status']:
                for item_info in device_info.get(group, {}).values():
                    addr = item_info.get('addr')
                    all_addrs.extend(addr if isinstance(addr, list) else [addr])
            
            if not all_addrs: continue
            min_addr, max_addr = min(all_addrs), max(all_addrs)
            self.mock_data[device_id] = {'min_addr': min_addr, 'regs': [0] * (max_addr - min_addr + 1)}

        # Inject some realistic float/int values and statuses
        # Device 2
        self._inject_value(2, 'outdoor_temp', pack_float(25.5))
        self._inject_status(2, 'outdoor_temp_status', 0) # Set status to READY (0)
        self._inject_value(2, 'outdoor_humidity', pack_float(60.2))
        self._inject_status(2, 'outdoor_humidity_status', 0) # Set status to READY (0)

        # Device 3
        self._inject_value(3, 'indoor_co2', pack_float(450.75))
        self._inject_status(3, 'indoor_co2_status', 0) # Set status to READY (0)

        # Device 4
        self._inject_value(4, 'fcu_remaining_time', pack_int32(3600))
        self._inject_value(4, 'heat_remaining_time', pack_int32(1800))
        self._inject_value(4, 'fcu_status', [10])

    def _inject_value(self, device_id, name, values):
        device_data = self.mock_data[device_id]
        addr = self.sensor_map['devices'][device_id]['values'][name]['addr']
        start_addr = addr[0] if isinstance(addr, list) else addr
        offset = start_addr - device_data['min_addr']
        for i, value in enumerate(values):
            device_data['regs'][offset + i] = value

    def _inject_status(self, device_id, name, status_val):
        device_data = self.mock_data[device_id]
        addr = self.sensor_map['devices'][device_id]['status'][name]['addr']
        offset = addr - device_data['min_addr']
        device_data['regs'][offset] = status_val

    def connect(self):
        print("--- Mock Modbus client connected. ---")
        return True

    def read_holding_registers(self, start_addr, count, slave):
        print(f"[SIM] Reading {count} registers from addr {start_addr} on device {slave}")
        if slave in self.mock_data:
            device_data = self.mock_data[slave]
            start_index = start_addr - device_data['min_addr']
            end_index = start_index + count
            return MockRegisterResponse(device_data['regs'][start_index:end_index])
        return MockRegisterResponse([0] * count) # Default empty response

    def close(self):
        print("--- Mock Modbus client closed. ---")


# --- Main Execution ---

# Load configurations
with open('sfai25/KSB7958/conf.json', 'r') as f:
    config = json.load(f)
with open('action_io_component/register_map_split_status.yaml', 'r') as f:
    sensor_map = yaml.safe_load(f)

# --- Simulation Setup ---
client = MockModbusClient(sensor_map)
client.connect()

# Explicitly process each device
devices = sensor_map.get('devices', {})
if 2 in devices:
    process_device(client, 2, devices[2])
if 3 in devices:
    process_device(client, 3, devices[3])
if 4 in devices:
    process_device(client, 4, devices[4])
if 5 in devices:
    process_device(client, 5, devices[5])

# Close the connection
client.close()
