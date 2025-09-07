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

from ksconstants import STATCODE
from utils import unpack_f32, unpack_i32

def process_device(client, device_id, device_info):
    """Reads a block of data for a single device and parses it."""
    print(f"--- Device ID: {device_id} ---")
    
    sensor_data = {}
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
        return []

    min_addr = min(all_addrs)
    max_addr = max(all_addrs)
    read_count = max_addr - min_addr + 1

    print(f"  - Reading block from {min_addr} to {max_addr} (count: {read_count})...")
    res = client.read_holding_registers(min_addr, count=read_count, device_id=device_id)

    if res.isError():
        print("  - 블록 읽기 실패")
        return []

    block = res.registers

    # Parse the fetched block for each sensor
    for name, info in device_info.get('values', {}).items():
        addr = info.get('addr')
        dtype = info.get('dtype')
        status_info = device_info.get('status', {}).get(f"{name}_status")
        
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
                sensor_data[name] = value
                print(f"  - {name}: {value}")
            else:  # Single register value
                offset = addr - min_addr
                value = block[offset]
                sensor_data[name] = value
                print(f"  - {name}: {value}")

            # Add status if it exists
            if status_info:
                status_addr = status_info['addr']
                status_offset = status_addr - min_addr
                status_val = block[status_offset]
                status_text = '정상' if status_val == STATCODE.READY else '비정상'
                sensor_data[f"{name}_status"] = status_text
                print(f"    상태: {status_text}")
        

        except IndexError:
            print(f"  - {name}: 파싱 오류 (주소 범위 문제)")
        except Exception as e:
            print(f"  - {name}: 파싱 중 알 수 없는 오류 발생: {e}")
    
    return sensor_data

# --- Main Execution ---

def main():
    # Load configurations
    with open('conf.json', 'r') as f:
        config = json.load(f)
    with open('register_map_split_status.yaml', 'r') as f:
        sensor_map = yaml.safe_load(f)

    # Connect to Modbus server
    client = ModbusTcpClient(config['modbus_ip'], port=config['modbus_port'])
    if not client.connect():
        print("Modbus 서버에 연결할 수 없습니다.")
        exit()

    # Process all devices and collect data
    all_sensor_data = {}
    devices = sensor_map.get('devices', {})
    
    # Process each device and collect data
    for dev_id in [2, 3, 4, 5]:
        if dev_id in devices:
            print(f"\nProcessing device {dev_id}...")
            device_data = process_device(client, dev_id, devices[dev_id])
            if device_data:  # Only extend if we got data back
                all_sensor_data.update(device_data)
    
    # Print the final JSON output
    print("\n=== Sensor Data ===")
    print(json.dumps(all_sensor_data, ensure_ascii=False, indent=2))
    
    # Close the connection
    client.close()

if __name__ == "__main__":
    main()




