|   time_band | actuator   |   priority | conditions                         | action                                                                    |
|------------:|:-----------|-----------:|:-----------------------------------|:--------------------------------------------------------------------------|
|           1 | FOG        |         90 | time_band = 1 AND indoor_temp ≥ 28 | {'actuator': 'FOG', 'state': 'ON', 'duration_sec': 60, 'pause_sec': 1800} |
|           1 | FOG        |         90 | time_band = 1 AND indoor_temp < 28 | {'actuator': 'FOG', 'state': 'OFF'}                                       |
|           2 | FOG        |         90 | time_band = 2 AND indoor_temp ≥ 26 | {'actuator': 'FOG', 'state': 'ON', 'duration_sec': 60, 'pause_sec': 600}  |
|           2 | FOG        |         90 | time_band = 2 AND indoor_temp < 26 | {'actuator': 'FOG', 'state': 'OFF'}                                       |
|           3 | FOG        |         90 | time_band = 3 AND indoor_temp ≥ 26 | {'actuator': 'FOG', 'state': 'ON', 'duration_sec': 120, 'pause_sec': 600} |
|           3 | FOG        |         90 | time_band = 3 AND indoor_temp < 26 | {'actuator': 'FOG', 'state': 'OFF'}                                       |
|           4 | FOG        |         90 | time_band = 4 AND indoor_temp ≥ 28 | {'actuator': 'FOG', 'state': 'ON', 'duration_sec': 60, 'pause_sec': 1800} |
|           4 | FOG        |         90 | time_band = 4 AND indoor_temp < 28 | {'actuator': 'FOG', 'state': 'OFF'}                                       |
|         nan | FOG        |        100 | indoor_humidity ≥ 85               | {'actuator': 'FOG', 'state': 'OFF'}                                       |