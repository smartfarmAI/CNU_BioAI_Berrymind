|   time_band | actuator       |   priority | conditions                              | action                                                                                   |
|------------:|:---------------|-----------:|:----------------------------------------|:-----------------------------------------------------------------------------------------|
|           3 | SHADING_SCREEN |         90 | time_band = 3 AND solar_radiation ≥ 400 | {'actuator': 'SHADING_SCREEN', 'state': 'CLOSE', 'duration_sec': 150, 'pause_sec': 1800} |
|           3 | SHADING_SCREEN |         90 | time_band = 3 AND solar_radiation < 400 | {'actuator': 'SHADING_SCREEN', 'state': 'OPEN', 'duration_sec': 50}                      |
|           4 | SHADING_SCREEN |         90 | time_band = 4 AND solar_radiation ≤ 400 | {'actuator': 'SHADING_SCREEN', 'state': 'OPEN', 'duration_sec': 150, 'pause_sec': 1800}  |
|         nan | SHADING_SCREEN |        100 | DAT = 0                                 | {'actuator': 'SHADING_SCREEN', 'state': 'CLOSE', 'duration_sec': 498}                    |
|         nan | SHADING_SCREEN |        100 | DAT = 1                                 | {'actuator': 'SHADING_SCREEN', 'state': 'CLOSE', 'duration_sec': 450}                    |
|         nan | SHADING_SCREEN |        100 | DAT = 2                                 | {'actuator': 'SHADING_SCREEN', 'state': 'CLOSE', 'duration_sec': 400}                    |
|         nan | SHADING_SCREEN |        100 | DAT = 3                                 | {'actuator': 'SHADING_SCREEN', 'state': 'CLOSE', 'duration_sec': 350}                    |
|         nan | SHADING_SCREEN |        100 | DAT = 4                                 | {'actuator': 'SHADING_SCREEN', 'state': 'CLOSE', 'duration_sec': 300}                    |
|         nan | SHADING_SCREEN |        100 | DAT = 5                                 | {'actuator': 'SHADING_SCREEN', 'state': 'CLOSE', 'duration_sec': 250}                    |
|         nan | SHADING_SCREEN |        100 | DAT = 6                                 | {'actuator': 'SHADING_SCREEN', 'state': 'CLOSE', 'duration_sec': 200}                    |
|         nan | SHADING_SCREEN |        100 | DAT = 7                                 | {'actuator': 'SHADING_SCREEN', 'state': 'CLOSE', 'duration_sec': 150}                    |
|         nan | SHADING_SCREEN |         99 | rain = 1                                | {'actuator': 'SHADING_SCREEN', 'state': 'OPEN', 'duration_sec': 150, 'pause_sec': 3600}  |