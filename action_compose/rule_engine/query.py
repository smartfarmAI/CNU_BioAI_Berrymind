def get_query() -> str:
  return """WITH base AS (
    SELECT * FROM greenhouse2 ORDER BY time DESC LIMIT 1
  ),
  b AS (
    SELECT *,
          (COALESCE(indoor_temp,0)=0
            AND COALESCE(indoor_humidity,0)=0
            AND COALESCE(indoor_co2,0)=0) AS all_zero3
    FROM base
  )
  SELECT
    b.time,
    CASE WHEN b.all_zero3 THEN COALESCE((
      SELECT p.indoor_temp
      FROM greenhouse2 p
      WHERE p.time <= b.time AND p.time > b.time - interval '30 minutes'
        AND COALESCE(p.indoor_temp,0) <> 0
      ORDER BY p.time DESC LIMIT 1
    ), b.indoor_temp) ELSE b.indoor_temp END AS indoor_temp,
    CASE WHEN b.all_zero3 THEN COALESCE((
      SELECT p.indoor_humidity
      FROM greenhouse2 p
      WHERE p.time <= b.time AND p.time > b.time - interval '30 minutes'
        AND COALESCE(p.indoor_humidity,0) <> 0
      ORDER BY p.time DESC LIMIT 1
    ), b.indoor_humidity) ELSE b.indoor_humidity END AS indoor_humidity,
    b.rain, b.wind_speed, b.outdoor_temp, b.solar_radiation,
    CASE WHEN b.all_zero3 THEN COALESCE((
      SELECT p.indoor_co2
      FROM greenhouse2 p
      WHERE p.time <= b.time AND p.time > b.time - interval '30 minutes'
        AND COALESCE(p.indoor_co2,0) <> 0
      ORDER BY p.time DESC LIMIT 1
    ), b.indoor_co2) ELSE b.indoor_co2 END AS indoor_co2,
    b.soil_water_content, b.wind_direction , b.fcu_circulation_status
  FROM b;"""