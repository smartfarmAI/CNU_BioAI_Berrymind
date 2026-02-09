|   time_band | actuator   |   priority | conditions                         | action                                                                                            |
|------------:|:-----------|-----------:|:-----------------------------------|:--------------------------------------------------------------------------------------------------|
|           1 | SKY_WINDOW |         90 | time_band = 1 AND indoor_temp ≥ 20 | {'actuator': 'SKY_WINDOW', 'state': 'OPEN', 'duration_sec': 30, 'pause_sec': 300, 'temp_diff': 2} |
|           2 | SKY_WINDOW |         90 | time_band = 2 AND indoor_temp ≥ 20 | {'actuator': 'SKY_WINDOW', 'state': 'OPEN', 'duration_sec': 20, 'pause_sec': 300, 'temp_diff': 2} |
|           3 | SKY_WINDOW |         90 | time_band = 3 AND indoor_temp ≥ 24 | {'actuator': 'SKY_WINDOW', 'state': 'OPEN', 'duration_sec': 20, 'pause_sec': 300, 'temp_diff': 2} |
|           4 | SKY_WINDOW |         90 | time_band = 4 AND indoor_temp ≤ 25 | {'actuator': 'SKY_WINDOW', 'state': 'CLOSE', 'duration_sec': 20, 'pause_sec': 300}                |
|           5 | SKY_WINDOW |         90 | time_band = 5 AND indoor_temp ≤ 20 | {'actuator': 'SKY_WINDOW', 'state': 'CLOSE', 'duration_sec': 20, 'pause_sec': 300}                |
|           6 | SKY_WINDOW |         90 | time_band = 6 AND indoor_temp ≤ 15 | {'actuator': 'SKY_WINDOW', 'state': 'CLOSE', 'duration_sec': 20, 'pause_sec': 300}                |
|           7 | SKY_WINDOW |         90 | time_band = 7 AND indoor_temp ≤ 15 | {'actuator': 'SKY_WINDOW', 'state': 'CLOSE', 'duration_sec': 20, 'pause_sec': 300}                |
|           8 | SKY_WINDOW |         90 | time_band = 8 AND indoor_temp ≥ 20 | {'actuator': 'SKY_WINDOW', 'state': 'CLOSE', 'duration_sec': 10, 'pause_sec': 300}                |
|         nan | SKY_WINDOW |        100 | rain = 1                           | {'actuator': 'SKY_WINDOW', 'state': 'CLOSE', 'pause_sec': 300}                                    |
|         nan | SKY_WINDOW |        100 | wind_speed ≥ 14                    | {'actuator': 'SKY_WINDOW', 'state': 'CLOSE', 'pause_sec': 300}                                    |