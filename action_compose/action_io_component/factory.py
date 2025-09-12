import yaml
from pathlib import Path
from pymodbus.client import ModbusTcpClient
from switch_actuator import SwitchActuator
from retractable_actuator import RetractableActuator
from nutsupply_actuator import NutSupplyActuator

def load_conf(path="act_conf.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))

def build_client(host="192.168.0.10", port=502):
    cli = ModbusTcpClient(host=host, port=port)
    assert cli.connect(), "Modbus connect failed"
    return cli

def build_actuator(kind: str, client, reg: dict):
    if kind in {"FCU_FAN","FCU_PUMP","CO2","FAN","FOG"}:
        return SwitchActuator(client, reg)
    if kind in {"SKY_WINDOW_LEFT","SKY_WINDOW_RIGHT","SHADING_SCREEN","HEAT_CURTAIN"}:
        return RetractableActuator(client, reg)
    if kind in {"NUTRIENT_PUMP"}:
        return NutSupplyActuator(client, reg)
    raise ValueError(f"unknown device kind: {kind}")
