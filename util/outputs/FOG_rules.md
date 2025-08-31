|   time_band | actuator   | rule_name                 |   priority | conditions                         | action                        |
|------------:|:-----------|:--------------------------|-----------:|:-----------------------------------|:------------------------------|
|           1 | FOG        |                           |         90 | time_band = 1 AND indoor_temp ≥ 28 | FOG:ON (dur=60s, pause=1800s) |
|           1 | FOG        |                           |         90 | time_band = 1 AND indoor_temp < 28 | FOG:OFF                       |
|           2 | FOG        |                           |         90 | time_band = 2 AND indoor_temp ≥ 26 | FOG:ON (dur=60s, pause=600s)  |
|           2 | FOG        |                           |         90 | time_band = 2 AND indoor_temp < 26 | FOG:OFF                       |
|           3 | FOG        |                           |         90 | time_band = 3 AND indoor_temp ≥ 26 | FOG:ON (dur=120s, pause=600s) |
|           3 | FOG        |                           |         90 | time_band = 3 AND indoor_temp < 26 | FOG:OFF                       |
|           4 | FOG        |                           |         90 | time_band = 4 AND indoor_temp ≥ 28 | FOG:ON (dur=60s, pause=1800s) |
|           4 | FOG        |                           |         90 | time_band = 4 AND indoor_temp < 28 | FOG:OFF                       |
|         nan | FOG        | Fundamental permise : FOG |        100 | indoor_humidity ≥ 85               | FOG:OFF                       |