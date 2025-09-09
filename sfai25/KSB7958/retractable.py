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
idx = 67
client = ModbusTcpClient(config['modbus_ip'], port=config['modbus_port'])
client.connect()

def getcommand(cmd):
    ctbl = {
        CMDCODE.OFF: "중지",
        CMDCODE.OPEN: "열림",
        CMDCODE.CLOSE: "닫힘",
        CMDCODE.TIMED_OPEN: "시간열림",
        CMDCODE.TIMED_CLOSE: "시간닫힘"
    }
    return ctbl[cmd] if cmd in ctbl else "없는 명령"

def sendcommand(cmd, sec = None):
    global opid, idx, client
    opid += 1
    reg = [cmd, opid]

    if sec is not None:
        reg.extend(struct.unpack('HH', struct.pack('i', sec)))

    print (getcommand(cmd), "명령을 전송합니다. ", reg)
    client.write_registers(500 + idx, reg, device_id=4)

def getstatus(stat):
    ctbl = {
        STATCODE.READY : "중지된 상태",
        STATCODE.OPENING : "여는중",
        STATCODE.CLOSING : "닫는중"
    }
    return ctbl[stat] if stat in ctbl else "없는 상태"

def getremaintime(reg1, reg2):
    return struct.unpack('i', struct.pack('HH', reg1, reg2))[0]

def readstatus(readtime = False):
    global opid, idx, client
    reg = client.read_holding_registers(200 + idx, count=4, device_id=4)
    if not reg.isError():
        if reg.registers[0] == opid:
            print ("OPID {0} 번 명령으로 {1} 입니다.".format(opid, getstatus(reg.registers[1])))
            if reg.registers[1] != 0 and readtime:
                print("작동 남은 시간은 {} 입니다.".format(getremaintime(reg.registers[2], reg.registers[3])))
        else:
            print ("OPID가 매치되지 않습니다. 레지스터값은 {0}, 기대하고 있는 값은 {1} 입니다.".format(reg.registers[0], opid))
    else:
        print("상태 읽기 실패")

# Initialize
sendcommand (CMDCODE.OFF)
time.sleep(5) # 잠시 대기
readstatus()

# OPEN
sendcommand (CMDCODE.OPEN)
for _ in range(1, 10):
    time.sleep(1) # 작동 여부 확인전에 잠시 대기
    readstatus()

# OFF
sendcommand (CMDCODE.OFF)
time.sleep(5) # 잠시 대기
readstatus()

# CLOSE
sendcommand (CMDCODE.CLOSE)
for _ in range(1, 10):
    time.sleep(1) # 작동 여부 확인전에 잠시 대기
    readstatus()

# OFF
sendcommand (CMDCODE.OFF)
time.sleep(5) # 잠시 대기
readstatus()

# TIMED OPEN - 10 초 작동
sendcommand (CMDCODE.TIMED_OPEN, 10)
for _ in range(1, 15):
    time.sleep(1) # 작동 여부 확인전에 잠시 대기
    readstatus(True)

# TIMED CLOSE - 10 초 작동
sendcommand (CMDCODE.TIMED_CLOSE, 10)
for _ in range(1, 15):
    time.sleep(1) # 작동 여부 확인전에 잠시 대기
    readstatus(True)

# 종료확인 
sendcommand (CMDCODE.OFF)
time.sleep(5) # 잠시 대기
readstatus()

