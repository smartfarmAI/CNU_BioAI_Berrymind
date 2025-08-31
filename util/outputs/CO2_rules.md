|   time_band | actuator   | rule_name                                           |   priority | conditions                                                  | action   |
|------------:|:-----------|:----------------------------------------------------|-----------:|:------------------------------------------------------------|:---------|
|           1 | CO2        | time_band 1 : Fundamental permise : rain : CO2 ON   |        100 | time_band = 1 AND indoor_CO2 ≤ 350 AND rain = 1             | CO2:ON   |
|           1 | CO2        | time_band 1 : Fundamental permise : rain : CO2 OFF  |        100 | time_band = 1 AND indoor_CO2 > 390 AND rain = 1             | CO2:OFF  |
|           1 | CO2        | time_band 1 : Fundamental permise : solar : CO2 ON  |         99 | time_band = 1 AND indoor_CO2 ≤ 350 AND solar_radiation ≤ 50 | CO2:ON   |
|           1 | CO2        | time_band 1 : Fundamental permise : solar : CO2 OFF |         99 | time_band = 1 AND indoor_CO2 > 520 AND solar_radiation ≤ 50 | CO2:OFF  |
|           1 | CO2        |                                                     |         90 | time_band = 1 AND indoor_CO2 ≤ 350                          | CO2:ON   |
|           1 | CO2        |                                                     |         90 | time_band = 1 AND indoor_CO2 > 650                          | CO2:OFF  |
|           2 | CO2        | time_band 2 : Fundamental permise : rain : CO2 ON   |        100 | time_band = 2 AND indoor_CO2 ≤ 300 AND rain = 1             | CO2:ON   |
|           2 | CO2        | time_band 2 : Fundamental permise : rain : CO2 OFF  |        100 | time_band = 2 AND indoor_CO2 > 330 AND rain = 1             | CO2:OFF  |
|           2 | CO2        | time_band 2 : Fundamental permise : solar : CO2 ON  |         99 | time_band = 2 AND indoor_CO2 ≤ 300 AND solar_radiation ≤ 50 | CO2:ON   |
|           2 | CO2        | time_band 2 : Fundamental permise : solar : CO2 OFF |         99 | time_band = 2 AND indoor_CO2 > 440 AND solar_radiation ≤ 50 | CO2:OFF  |
|           2 | CO2        |                                                     |         90 | time_band = 2 AND indoor_CO2 ≤ 300                          | CO2:ON   |
|           2 | CO2        |                                                     |         90 | time_band = 2 AND indoor_CO2 > 550                          | CO2:OFF  |
|           3 | CO2        | time_band 3 : Fundamental permise : rain : CO2 ON   |        100 | time_band = 3 AND indoor_CO2 ≤ 200 AND rain = 1             | CO2:ON   |
|           3 | CO2        | time_band 3 : Fundamental permise : rain : CO2 OFF  |        100 | time_band = 3 AND indoor_CO2 > 300 AND rain = 1             | CO2:OFF  |
|           3 | CO2        | time_band 3 : Fundamental permise : solar : CO2 ON  |         99 | time_band = 3 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | CO2:ON   |
|           3 | CO2        | time_band 3 : Fundamental permise : solar : CO2 OFF |         99 | time_band = 3 AND indoor_CO2 > 400 AND solar_radiation ≤ 50 | CO2:OFF  |
|           3 | CO2        |                                                     |         90 | time_band = 3 AND indoor_CO2 ≤ 200                          | CO2:ON   |
|           3 | CO2        |                                                     |         90 | time_band = 3 AND indoor_CO2 > 500                          | CO2:OFF  |
|           4 | CO2        | time_band 4 : Fundamental permise : rain : CO2 ON   |        100 | time_band = 4 AND indoor_CO2 ≤ 200 AND rain = 1             | CO2:ON   |
|           4 | CO2        | time_band 4 : Fundamental permise : rain : CO2 OFF  |        100 | time_band = 4 AND indoor_CO2 > 240 AND rain = 1             | CO2:OFF  |
|           4 | CO2        | time_band 4 : Fundamental permise : solar : CO2 ON  |         99 | time_band = 4 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | CO2:ON   |
|           4 | CO2        | time_band 4 : Fundamental permise : solar : CO2 OFF |         99 | time_band = 4 AND indoor_CO2 > 320 AND solar_radiation ≤ 50 | CO2:OFF  |
|           4 | CO2        |                                                     |         90 | time_band = 4 AND indoor_CO2 ≤ 200                          | CO2:ON   |
|           4 | CO2        |                                                     |         90 | time_band = 4 AND indoor_CO2 > 400                          | CO2:OFF  |
|           5 | CO2        | time_band 5 : Fundamental permise : rain : CO2 ON   |        100 | time_band = 5 AND indoor_CO2 ≤ 180 AND rain = 1             | CO2:ON   |
|           5 | CO2        | time_band 5 : Fundamental permise : rain : CO2 OFF  |        100 | time_band = 5 AND indoor_CO2 > 180 AND rain = 1             | CO2:OFF  |
|           5 | CO2        | time_band 5 : Fundamental permise : solar : CO2 ON  |         99 | time_band = 5 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | CO2:ON   |
|           5 | CO2        | time_band 5 : Fundamental permise : solar : CO2 OFF |         99 | time_band = 5 AND indoor_CO2 > 240 AND solar_radiation ≤ 50 | CO2:OFF  |
|           5 | CO2        |                                                     |         90 | time_band = 5 AND indoor_CO2 ≤ 200                          | CO2:ON   |
|           5 | CO2        |                                                     |         90 | time_band = 5 AND indoor_CO2 > 300                          | CO2:OFF  |
|           6 | CO2        | time_band 6 : Fundamental permise : rain : CO2 ON   |        100 | time_band = 6 AND indoor_CO2 ≤ 180 AND rain = 1             | CO2:ON   |
|           6 | CO2        | time_band 6 : Fundamental permise : rain : CO2 OFF  |        100 | time_band = 6 AND indoor_CO2 > 180 AND rain = 1             | CO2:OFF  |
|           6 | CO2        | time_band 6 : Fundamental permise : solar : CO2 ON  |         99 | time_band = 6 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | CO2:ON   |
|           6 | CO2        | time_band 6 : Fundamental permise : solar : CO2 OFF |         99 | time_band = 6 AND indoor_CO2 > 240 AND solar_radiation ≤ 50 | CO2:OFF  |
|           6 | CO2        |                                                     |         90 | time_band = 6 AND indoor_CO2 ≤ 200                          | CO2:ON   |
|           6 | CO2        |                                                     |         90 | time_band = 6 AND indoor_CO2 > 300                          | CO2:OFF  |
|           7 | CO2        | time_band 7 : Fundamental permise : rain : CO2 ON   |        100 | time_band = 7 AND indoor_CO2 ≤ 180 AND rain = 1             | CO2:ON   |
|           7 | CO2        | time_band 7 : Fundamental permise : rain : CO2 OFF  |        100 | time_band = 7 AND indoor_CO2 > 180 AND rain = 1             | CO2:OFF  |
|           7 | CO2        | time_band 7 : Fundamental permise : solar : CO2 ON  |         99 | time_band = 7 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | CO2:ON   |
|           7 | CO2        | time_band 7 : Fundamental permise : solar : CO2 OFF |         99 | time_band = 7 AND indoor_CO2 > 240 AND solar_radiation ≤ 50 | CO2:OFF  |
|           7 | CO2        |                                                     |         90 | time_band = 7 AND indoor_CO2 ≤ 200                          | CO2:ON   |
|           7 | CO2        |                                                     |         90 | time_band = 7 AND indoor_CO2 > 300                          | CO2:OFF  |
|           8 | CO2        | time_band 8 : Fundamental permise : rain : CO2 ON   |        100 | time_band = 8 AND indoor_CO2 ≤ 200 AND rain = 1             | CO2:ON   |
|           8 | CO2        | time_band 8 : Fundamental permise : rain : CO2 OFF  |        100 | time_band = 8 AND indoor_CO2 > 270 AND rain = 1             | CO2:OFF  |
|           8 | CO2        | time_band 8 : Fundamental permise : solar : CO2 ON  |         99 | time_band = 8 AND indoor_CO2 ≤ 200 AND solar_radiation ≤ 50 | CO2:ON   |
|           8 | CO2        | time_band 8 : Fundamental permise : solar : CO2 OFF |         99 | time_band = 8 AND indoor_CO2 > 360 AND solar_radiation ≤ 50 | CO2:OFF  |
|           8 | CO2        |                                                     |         90 | time_band = 8 AND indoor_CO2 ≤ 200                          | CO2:ON   |
|           8 | CO2        |                                                     |         90 | time_band = 8 AND indoor_CO2 > 450                          | CO2:OFF  |