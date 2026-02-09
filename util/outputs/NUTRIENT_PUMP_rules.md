|   time_band | actuator   |   priority | conditions                                         | action                                         |
|------------:|:-----------|-----------:|:---------------------------------------------------|:-----------------------------------------------|
|           1 |            |         90 | time_band = 1 AND water_content ≤ 12.5 AND DAT ≤ 3 | {'water_type': 'WATER', 'duration_sec': 50}    |
|           1 |            |         90 | time_band = 1 AND water_content ≤ 12.5 AND DAT > 3 | {'water_type': 'NUTRIENT', 'duration_sec': 50} |
|           2 |            |         90 | time_band = 2 AND water_content ≤ 12.5 AND DAT ≤ 3 | {'water_type': 'WATER', 'duration_sec': 30}    |
|           2 |            |         90 | time_band = 2 AND water_content ≤ 12.5 AND DAT > 3 | {'water_type': 'NUTRIENT', 'duration_sec': 30} |
|           3 |            |         90 | time_band = 3 AND water_content ≤ 12.5 AND DAT ≤ 3 | {'water_type': 'WATER', 'duration_sec': 20}    |
|           3 |            |         90 | time_band = 3 AND water_content ≤ 12.5 AND DAT > 3 | {'water_type': 'NUTRIENT', 'duration_sec': 20} |
|           4 |            |         90 | time_band = 4 AND water_content ≤ 12.5 AND DAT ≤ 3 | {'water_type': 'WATER', 'duration_sec': 15}    |
|           4 |            |         90 | time_band = 4 AND water_content ≤ 12.5 AND DAT > 3 | {'water_type': 'NUTRIENT', 'duration_sec': 15} |