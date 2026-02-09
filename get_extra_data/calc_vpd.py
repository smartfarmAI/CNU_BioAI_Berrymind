import numpy as np

def vpd_kpa(temp_c, rh_percent):
    """
    VPD 계산 (kPa)
    temp_c: 섭씨온도(ºC) - 스칼라 또는 numpy 배열/판다스 시리즈
    rh_percent: 상대습도(%) - 스칼라 또는 numpy 배열/판다스 시리즈
    """
    temp_c = np.asarray(temp_c, dtype=float)
    rh = np.asarray(rh_percent, dtype=float)

    es = 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3))  # kPa
    ea = es * (rh / 100.0)                                     # kPa
    vpd = es - ea                                              # kPa
    return vpd