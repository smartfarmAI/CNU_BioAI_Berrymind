import yaml, random, time, schedule
from dataclasses import dataclass, field
from typing import Dict, Any
from loguru import logger

@dataclass
class SensorMock:
    conf_path: str = "conf.yaml"
    bounds: Dict[str, Dict[str, float]] = field(default_factory=dict)
    values: Dict[str, float] = field(default_factory=dict)

    def load(self) -> None:
        with open(self.conf_path, "r", encoding="utf-8") as f:
            self.bounds = yaml.safe_load(f).get("bounds", {})
        logger.info(f"Loaded bounds: {list(self.bounds.keys())}")

    def tick(self) -> None:
        if not self.bounds:
            self.load()
        self.values = {}
        for k, v in self.bounds.items():
            if "choices" in v:  # 0/1 같은 discrete choice
                self.values[k] = random.choice(v["choices"])
            else:               # min/max 범위값
                self.values[k] = round(random.uniform(v["min"], v["max"]), 2)
        logger.info(f"Updated values: {self.values}")

    def get(self, key: str) -> Any:
        return self.values.get(key)

if __name__ == "__main__":
    sensor = SensorMock()
    sensor.tick()                         # 최초 1회 갱신
    schedule.every(1).minutes.do(sensor.tick)
    while True:
        schedule.run_pending()
        time.sleep(1)
