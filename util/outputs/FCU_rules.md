|   time_band | actuator   | rule_name   |   priority | conditions                         | action   |
|------------:|:-----------|:------------|-----------:|:-----------------------------------|:---------|
|           2 | FCU        |             |         90 | time_band = 2 AND indoor_temp ≥ 30 | FCU:ON   |
|           2 | FCU        |             |         90 | time_band = 2 AND indoor_temp ≤ 27 | FCU:OFF  |
|           3 | FCU        |             |         90 | time_band = 3 AND indoor_temp ≥ 28 | FCU:ON   |
|           3 | FCU        |             |         90 | time_band = 3 AND indoor_temp ≤ 25 | FCU:OFF  |