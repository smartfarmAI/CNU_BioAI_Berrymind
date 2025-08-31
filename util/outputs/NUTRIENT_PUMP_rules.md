|   time_band | actuator   | rule_name   |   priority | conditions                                         | action      |
|------------:|:-----------|:------------|-----------:|:---------------------------------------------------|:------------|
|           1 |            |             |         90 | time_band = 1 AND water_content ≤ 12.5 AND DAT ≤ 3 | : (dur=50s) |
|           1 |            |             |         90 | time_band = 1 AND water_content ≤ 12.5 AND DAT > 3 | : (dur=50s) |
|           2 |            |             |         90 | time_band = 2 AND water_content ≤ 12.5 AND DAT ≤ 3 | : (dur=30s) |
|           2 |            |             |         90 | time_band = 2 AND water_content ≤ 12.5 AND DAT > 3 | : (dur=30s) |
|           3 |            |             |         90 | time_band = 3 AND water_content ≤ 12.5 AND DAT ≤ 3 | : (dur=20s) |
|           3 |            |             |         90 | time_band = 3 AND water_content ≤ 12.5 AND DAT > 3 | : (dur=20s) |
|           4 |            |             |         90 | time_band = 4 AND water_content ≤ 12.5 AND DAT ≤ 3 | : (dur=15s) |
|           4 |            |             |         90 | time_band = 4 AND water_content ≤ 12.5 AND DAT > 3 | : (dur=15s) |