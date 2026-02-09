def get_X_sql():
    return  """WITH latest AS (
        SELECT MAX(time) AS last_time
        FROM greenhouse2
    )
    SELECT
        id,
        time,
        outdoor_temp,
        wind_direction,
        wind_speed,
        solar_radiation,
        indoor_temp,
        indoor_humidity,
        indoor_co2,
        sky_window_left_open_pct,
        sky_window_right_open_pct,
        heat_curtain_open_pct,
        shading_screen_open_pct,
        rain,
        fan_status,
        fcu_status,
        fcu_circulation_status,
        fog_status,
        co2_status
    FROM greenhouse2 g
    CROSS JOIN latest l
    WHERE g.time >= l.last_time - INTERVAL '10 minutes'
    AND g.time <= l.last_time
    AND NOT (
        indoor_temp = 0
        AND indoor_humidity = 0
        AND indoor_co2 = 0
    )
    ORDER BY time ASC;"""
