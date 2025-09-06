-- 1) 확장
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 2) 테이블
CREATE TABLE IF NOT EXISTS greenhouse2 (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  time TIMESTAMPTZ NOT NULL,

  -- device 2 values
  out_temp REAL,
  out_humi REAL,
  rain REAL,
  out_solar REAL,
  out_wind_speed REAL,
  out_wind_direction REAL,

  -- device 2 status
  out_temp_status SMALLINT,
  out_humi_status SMALLINT,
  rain_status SMALLINT,
  out_solar_status SMALLINT,
  out_wind_speed_status SMALLINT,
  out_wind_direction_status SMALLINT,

  -- device 3 values
  in_temp REAL,
  in_humi REAL,
  in_wind_speed REAL,
  in_co2 REAL,
  in_ec REAL,
  in_soil_w REAL,
  in_soil_t REAL,

  -- device 3 status
  in_temp_status SMALLINT,
  in_humi_status SMALLINT,
  in_wind_speed_status SMALLINT,
  in_co2_status SMALLINT,
  in_ec_status SMALLINT,
  in_soil_w_status SMALLINT,
  in_soil_t_status SMALLINT,

  -- device 4 values
  fcu_opid SMALLINT,
  fcu_status SMALLINT,
  fcu_remaining_time INTEGER,
  fcu_circulation_opid SMALLINT,
  fcu_circulation_status SMALLINT,
  fcu_circulation_remaining_time INTEGER,
  co2_opid SMALLINT,
  co2_status SMALLINT,
  co2_remaining_time INTEGER,
  fan_opid SMALLINT,
  fan_status SMALLINT,
  fan_remaining_time INTEGER,
  fog_opid SMALLINT,
  fog_status SMALLINT,
  fog_remain INTEGER,
  sky_left_opid_status SMALLINT,
  sky_left_status SMALLINT,
  sky_left_remaining_time INTEGER,
  sky_left_open_pct SMALLINT,
  sky_right_opid_status SMALLINT,
  sky_right_status SMALLINT,
  sky_right_remaining_time INTEGER,
  sky_right_open_pct SMALLINT,
  shade_opid_status SMALLINT,
  shade_status SMALLINT,
  shade_remaining_time INTEGER,
  shade_open_pct SMALLINT,
  heat_opid_status SMALLINT,
  heat_status SMALLINT,
  heat_remaining_time INTEGER,
  heat_open_pct SMALLINT,

  -- device 5 values
  ec1_value REAL,
  ph1_value REAL,
  total_flow_value REAL,
  flow1_value REAL,
  fert_status SMALLINT,
  fert_area SMALLINT,
  fert_alarm SMALLINT,
  fert_opid_status SMALLINT,
  fert_remain_time INTEGER,

  -- device 5 status
  ec1_value_status SMALLINT,
  ph1_value_status SMALLINT,
  total_flow_value_status SMALLINT,
  flow1_value_status SMALLINT
);

-- 3) 하이퍼테이블 + 인덱스
SELECT create_hypertable('greenhouse2','time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_greenhouse2_time ON greenhouse2 (time DESC);
