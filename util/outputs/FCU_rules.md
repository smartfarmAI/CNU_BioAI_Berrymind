|   time_band | actuator   |   priority | conditions                         | action                              |
|------------:|:-----------|-----------:|:-----------------------------------|:------------------------------------|
|           2 | FCU        |         90 | time_band = 2 AND indoor_temp ≥ 30 | {'actuator': 'FCU', 'state': 'ON'}  |
|           2 | FCU        |         90 | time_band = 2 AND indoor_temp ≤ 27 | {'actuator': 'FCU', 'state': 'OFF'} |
|           3 | FCU        |         90 | time_band = 3 AND indoor_temp ≥ 28 | {'actuator': 'FCU', 'state': 'ON'}  |
|           3 | FCU        |         90 | time_band = 3 AND indoor_temp ≤ 25 | {'actuator': 'FCU', 'state': 'OFF'} |