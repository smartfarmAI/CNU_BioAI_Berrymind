#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024 tombraid@snu.ac.kr
# All right reserved.
#
import time
import struct
import json
from pymodbus.client import ModbusTcpClient
from ksconstants import STATCODE, CMDCODE, PRIVCODE

# Load configuration
with open('conf.json', 'r') as f:
    config = json.load(f)

opid = 1
client = ModbusTcpClient(config['modbus_ip'], port=config['modbus_port'])
client.connect()

def getcommand(cmd):
    ctbl = {
        CMDCODE.OFF: "중지",
        CMDCODE.ONCE_WATER: "1회관수",
        CMDCODE.JUST_WATER: "원수관수",
        CMDCODE.NUT_WATER: "양액관수"
    }
    return ctbl[cmd] if cmd in ctbl else "없는 명령"

def sendcommand(cmd, sec = None, ec = None, ph = None):
    global opid, client
    opid += 1

    if cmd == CMDCODE.JUST_WATER:
        reg = [cmd, opid, 1, 1] 
        reg.extend(struct.unpack('HH', struct.pack('i', sec)))
    elif cmd == CMDCODE.NUT_WATER:
        reg = [cmd, opid, 1, 1] 
        reg.extend(struct.unpack('HH', struct.pack('i', sec)))
        reg.extend(struct.unpack('HH', struct.pack('f', ec)))
        reg.extend(struct.unpack('HH', struct.pack('f', ph)))
    else:
        reg = [cmd, opid] 

    print (getcommand(cmd), "명령을 전송합니다. ", reg)
    client.write_registers(504, reg, device_id=5)
    
def getstatus(stat):
    ctbl = {
        STATCODE.READY : "중지된 상태",
        STATCODE.PREPARING : "준비중",
        STATCODE.SUPPLYING : "관수중",
        STATCODE.FINISHING : "정지중"
    }
    return ctbl[stat] if stat in ctbl else "없는 상태"

def getremaintime(reg1, reg2):
    return struct.unpack('i', struct.pack('HH', reg1, reg2))[0]

def getobservation(reg1, reg2):
    return struct.unpack('f', struct.pack('HH', reg1, reg2))[0]

def readstatus(readtime = False):
    global opid, client
    reg = client.read_holding_registers(401, count=6, device_id=5)
    if not reg.isError():
        if reg.registers[3] == opid:
            print ("OPID {0} 번 명령으로 {1} 입니다.".format(opid, getstatus(reg.registers[0])))
            if reg.registers[0] == 1:
                print("양액기 에러입니다. 에러코드는 {} 입니다.".format(reg.registers[2]))
            elif reg.registers[0] != 0 and readtime:
                print("관수구역은 {0}이고, 남은시간은 {1} 입니다.".format(reg.registers[1], getremaintime(reg.registers[4], reg.registers[5])))
        else:
            print ("OPID가 매치되지 않습니다. 레지스터값은 {0}, 기대하고 있는 값은 {1} 입니다.".format(reg.registers[3], opid))
    else:
        print("상태 읽기 실패")


# 양액기에 연결된 센서값 읽기
reg = client.read_holding_registers(204, count=3, device_id=5)
if not reg.isError():
    ec_val = getobservation(reg.registers[0], reg.registers[1])
    print ("EC : ", ec_val, reg.registers)
    ec = ec_val
else:
    print("EC 센서값 읽기 실패")
    ec = 0.0


reg = client.read_holding_registers(213, count=3, device_id=5)
if not reg.isError():
    ph_val = getobservation(reg.registers[0], reg.registers[1])
    print ("pH : ", ph_val, reg.registers)
    ph = ph_val
else:
    print("pH 센서값 읽기 실패")
    ph = 0.0


reg = client.read_holding_registers(225, count=3, device_id=5)
if not reg.isError():
    print ("유량 : ", getobservation(reg.registers[0], reg.registers[1]), reg.registers)
else:
    print("유량 센서값 읽기 실패")



# Initialize
sendcommand (CMDCODE.OFF)
time.sleep(5) # 잠시 대기
readstatus()

# 1회 관수 : ONCE_WATER : Not USE : 대회를 위해서 적절한 명령이 아니기 때문에 사용하지 않습니다.
sendcommand (CMDCODE.ONCE_WATER)
for _ in range(1, 10):
    readstatus(True)
    time.sleep(1)
sendcommand (CMDCODE.OFF)
time.sleep(5) # 잠시 대기
readstatus()

#"""
# 원수 관수 : JUST_WATER : 맹물을 관수합니다.
sendcommand (CMDCODE.JUST_WATER, 30)
for _ in range(1, 40):
    readstatus(True)
    time.sleep(1)
#"""

#""" 
# 양액 관수 : NUT_WATER : 양액을 관수합니다.
sendcommand (CMDCODE.NUT_WATER, 30, ec, ph)
for _ in range(1, 40):
    readstatus(True)
    time.sleep(1)
#"""

# 종료 확인 
sendcommand (CMDCODE.OFF)
time.sleep(5) # 잠시 대기
readstatus()

