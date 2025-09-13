import pandas as pd
import ast

def make_summary(row, prefix):
    state = row.get(f'{prefix}_state', '')
    duration = row.get(f'{prefix}_duration', '')
    pause = row.get(f'{prefix}_pause', '')
    if pd.isna(state): state = ''
    if pd.isna(duration): duration = ''
    if pd.isna(pause): pause = ''
    return f"{state} (duration: {duration}s, pause: {pause}s)" if state else ''

def parse_log_to_csv(log_path, csv_path):
    sensor_list = []
    decision_list = []
    with open(log_path, 'r', encoding='utf-16') as f:
        for line in f:
            line = line.strip()
            if line.startswith('[SENSOR]'):
                sensor_dict = ast.literal_eval(line.split('[SENSOR]')[1].strip())
                sensor_list.append(sensor_dict)
            elif line.startswith('[DECISION]'):
                decision_dict = ast.literal_eval(line.split('[DECISION]')[1].strip())
                flat_decision = {}
                for actuator, v in decision_dict.items():
                    action_param = v.get('action_param', {})
                    flat_decision[f'{actuator}_state'] = action_param.get('state')
                    flat_decision[f'{actuator}_duration'] = action_param.get('duration_sec')
                    flat_decision[f'{actuator}_pause'] = action_param.get('pause_sec')
                decision_list.append(flat_decision)

    min_len = min(len(sensor_list), len(decision_list))
    rows = []
    for i in range(min_len):
        row = sensor_list[i].copy()
        row.update(decision_list[i])
        rows.append(row)

    df = pd.DataFrame(rows)

    sensor_cols = ['time_band', 'indoor_temp', 'indoor_humidity', 'rain', 'wind_speed','wind_direction', 'temp_diff',
                   'outdoor_temp', 'solar_radiation', 'DAT', 'indoor_co2', 'soil_water_content']

    actuators = [col[:-6] for col in df.columns if col.endswith('_state')]  # 자동 추출

    for act in actuators:
        df[f'{act}_summary'] = df.apply(lambda row: make_summary(row, act), axis=1)

    summary_cols = sensor_cols + [f'{act}_summary' for act in actuators]
    df_summary = df[summary_cols]

    df_summary.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"완성! '{csv_path}' 파일이 생성되었습니다.")

# 사용 예시
parse_log_to_csv('test_result.txt', 'greenhouse_log_summary.csv')
