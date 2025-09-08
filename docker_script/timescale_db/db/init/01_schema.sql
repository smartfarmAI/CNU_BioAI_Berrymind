-- 1) 확장
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 2) 테이블
CREATE TABLE IF NOT EXISTS greenhouse2 (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  time TIMESTAMPTZ NOT NULL,
  time_band SMALLINT,
  DAT SMALLINT,

  -- device 2 values
  outdoor_temp REAL,
  outdoor_humidity REAL,
  rain REAL,
  solar_radiation REAL,
  wind_speed REAL,
  wind_direction REAL,

  -- device 2 status
  outdoor_temp_status SMALLINT,
  outdoor_humidity_status SMALLINT,
  rain_status SMALLINT,
  solar_radiation_status SMALLINT,
  wind_speed_status SMALLINT,
  wind_direction_status SMALLINT,

  -- device 3 values
  indoor_temp REAL,
  indoor_humidity REAL,
  indoor_wind_speed REAL,
  indoor_co2 REAL,
  indoor_ec REAL,
  soil_water_content REAL,
  soil_temp REAL,

  -- device 3 status
  indoor_temp_status SMALLINT,
  indoor_humidity_status SMALLINT,
  indoor_wind_speed_status SMALLINT,
  indoor_co2_status SMALLINT,
  indoor_ec_status SMALLINT,
  soil_water_content_status SMALLINT,
  soil_temp_status SMALLINT,

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
  sky_window_left_opid_status SMALLINT,
  sky_window_left_status SMALLINT,
  sky_window_left_remaining_time INTEGER,
  sky_window_left_open_pct SMALLINT,
  sky_window_right_opid_status SMALLINT,
  sky_window_right_status SMALLINT,
  sky_window_right_remaining_time INTEGER,
  sky_window_right_open_pct SMALLINT,
  shading_screen_opid_status SMALLINT,
  shading_screen_status SMALLINT,
  shading_screen_remaining_time INTEGER,
  shading_screen_open_pct SMALLINT,
  heat_curtain_opid_status SMALLINT,
  heat_curtain_status SMALLINT,
  heat_curtain_remaining_time INTEGER,
  heat_curtain_open_pct SMALLINT,

  -- device 5 values
  nut_ec_value REAL,
  nut_ph_value REAL,
  total_flow_value REAL,
  flow_value REAL,
  fert_status SMALLINT,
  fert_area SMALLINT,
  fert_alarm SMALLINT,
  fert_opid_status SMALLINT,
  fert_remain_time INTEGER,

  -- device 5 status
  nut_ec_value_status SMALLINT,
  nut_ph_value_status SMALLINT,
  total_flow_value_status SMALLINT,
  flow_value_status SMALLINT
);

-- 3) 하이퍼테이블 + 인덱스
SELECT create_hypertable('greenhouse2','time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_greenhouse2_time ON greenhouse2 (time DESC);
