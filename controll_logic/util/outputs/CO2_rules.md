|   time_band | actuator   |   priority | conditions                                                  | action                              |
|------------:|:-----------|-----------:|:------------------------------------------------------------|:------------------------------------|
|           1 | CO2        |        100 | time_band = 1 AND indoor_CO2 ≤ 350 AND rain = 1             | {'actuator': 'CO2', 'state': 'ON'}  |
|           1 | CO2        |        100 | time_band = 1 AND indoor_CO2 > 390 AND rain = 1             | {'actuator': 'CO2', 'state': 'OFF'} |
|           1 | CO2        |         99 | time_band = 1 AND indoor_CO2 ≤ 350 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'ON'}  |
|           1 | CO2        |         99 | time_band = 1 AND indoor_CO2 > 520 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'OFF'} |
|           1 | CO2        |         90 | time_band = 1 AND indoor_CO2 ≤ 350                          | {'actuator': 'CO2', 'state': 'ON'}  |
|           1 | CO2        |         90 | time_band = 1 AND indoor_CO2 > 650                          | {'actuator': 'CO2', 'state': 'OFF'} |
|           2 | CO2        |        100 | time_band = 2 AND indoor_CO2 ≤ 300 AND rain = 1             | {'actuator': 'CO2', 'state': 'ON'}  |
|           2 | CO2        |        100 | time_band = 2 AND indoor_CO2 > 330 AND rain = 1             | {'actuator': 'CO2', 'state': 'OFF'} |
|           2 | CO2        |         99 | time_band = 2 AND indoor_CO2 ≤ 300 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'ON'}  |
|           2 | CO2        |         99 | time_band = 2 AND indoor_CO2 > 440 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'OFF'} |
|           2 | CO2        |         90 | time_band = 2 AND indoor_CO2 ≤ 300                          | {'actuator': 'CO2', 'state': 'ON'}  |
|           2 | CO2        |         90 | time_band = 2 AND indoor_CO2 > 550                          | {'actuator': 'CO2', 'state': 'OFF'} |
|           3 | CO2        |        100 | time_band = 3 AND indoor_CO2 ≤ 200 AND rain = 1             | {'actuator': 'CO2', 'state': 'ON'}  |
|           3 | CO2        |        100 | time_band = 3 AND indoor_CO2 > 300 AND rain = 1             | {'actuator': 'CO2', 'state': 'OFF'} |
|           3 | CO2        |         99 | time_band = 3 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'ON'}  |
|           3 | CO2        |         99 | time_band = 3 AND indoor_CO2 > 400 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'OFF'} |
|           3 | CO2        |         90 | time_band = 3 AND indoor_CO2 ≤ 200                          | {'actuator': 'CO2', 'state': 'ON'}  |
|           3 | CO2        |         90 | time_band = 3 AND indoor_CO2 > 500                          | {'actuator': 'CO2', 'state': 'OFF'} |
|           4 | CO2        |        100 | time_band = 4 AND indoor_CO2 ≤ 200 AND rain = 1             | {'actuator': 'CO2', 'state': 'ON'}  |
|           4 | CO2        |        100 | time_band = 4 AND indoor_CO2 > 240 AND rain = 1             | {'actuator': 'CO2', 'state': 'OFF'} |
|           4 | CO2        |         99 | time_band = 4 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'ON'}  |
|           4 | CO2        |         99 | time_band = 4 AND indoor_CO2 > 320 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'OFF'} |
|           4 | CO2        |         90 | time_band = 4 AND indoor_CO2 ≤ 200                          | {'actuator': 'CO2', 'state': 'ON'}  |
|           4 | CO2        |         90 | time_band = 4 AND indoor_CO2 > 400                          | {'actuator': 'CO2', 'state': 'OFF'} |
|           5 | CO2        |        100 | time_band = 5 AND indoor_CO2 ≤ 180 AND rain = 1             | {'actuator': 'CO2', 'state': 'ON'}  |
|           5 | CO2        |        100 | time_band = 5 AND indoor_CO2 > 180 AND rain = 1             | {'actuator': 'CO2', 'state': 'OFF'} |
|           5 | CO2        |         99 | time_band = 5 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'ON'}  |
|           5 | CO2        |         99 | time_band = 5 AND indoor_CO2 > 240 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'OFF'} |
|           5 | CO2        |         90 | time_band = 5 AND indoor_CO2 ≤ 200                          | {'actuator': 'CO2', 'state': 'ON'}  |
|           5 | CO2        |         90 | time_band = 5 AND indoor_CO2 > 300                          | {'actuator': 'CO2', 'state': 'OFF'} |
|           6 | CO2        |        100 | time_band = 6 AND indoor_CO2 ≤ 180 AND rain = 1             | {'actuator': 'CO2', 'state': 'ON'}  |
|           6 | CO2        |        100 | time_band = 6 AND indoor_CO2 > 180 AND rain = 1             | {'actuator': 'CO2', 'state': 'OFF'} |
|           6 | CO2        |         99 | time_band = 6 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'ON'}  |
|           6 | CO2        |         99 | time_band = 6 AND indoor_CO2 > 240 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'OFF'} |
|           6 | CO2        |         90 | time_band = 6 AND indoor_CO2 ≤ 200                          | {'actuator': 'CO2', 'state': 'ON'}  |
|           6 | CO2        |         90 | time_band = 6 AND indoor_CO2 > 300                          | {'actuator': 'CO2', 'state': 'OFF'} |
|           7 | CO2        |        100 | time_band = 7 AND indoor_CO2 ≤ 180 AND rain = 1             | {'actuator': 'CO2', 'state': 'ON'}  |
|           7 | CO2        |        100 | time_band = 7 AND indoor_CO2 > 180 AND rain = 1             | {'actuator': 'CO2', 'state': 'OFF'} |
|           7 | CO2        |         99 | time_band = 7 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'ON'}  |
|           7 | CO2        |         99 | time_band = 7 AND indoor_CO2 > 240 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'OFF'} |
|           7 | CO2        |         90 | time_band = 7 AND indoor_CO2 ≤ 200                          | {'actuator': 'CO2', 'state': 'ON'}  |
|           7 | CO2        |         90 | time_band = 7 AND indoor_CO2 > 300                          | {'actuator': 'CO2', 'state': 'OFF'} |
|           8 | CO2        |        100 | time_band = 8 AND indoor_CO2 ≤ 200 AND rain = 1             | {'actuator': 'CO2', 'state': 'ON'}  |
|           8 | CO2        |        100 | time_band = 8 AND indoor_CO2 > 270 AND rain = 1             | {'actuator': 'CO2', 'state': 'OFF'} |
|           8 | CO2        |         99 | time_band = 8 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'ON'}  |
|           8 | CO2        |         99 | time_band = 8 AND indoor_CO2 > 360 AND solar_radiation ≤ 50 | {'actuator': 'CO2', 'state': 'OFF'} |
|           8 | CO2        |         90 | time_band = 8 AND indoor_CO2 ≤ 200                          | {'actuator': 'CO2', 'state': 'ON'}  |
|           8 | CO2        |         90 | time_band = 8 AND indoor_CO2 > 450                          | {'actuator': 'CO2', 'state': 'OFF'} |