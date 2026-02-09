"""
일출/일몰 시간 계산 및 실제 데이터와 비교 분석 도구
완주군 이서면 농생명로 100 (위도: 35.8, 경도: 127.1) 기준
"""

import ephem
from datetime import datetime, timedelta, time
from typing import Tuple

class SunriseCalculator:
    """일출/일몰 시간 계산 클래스"""
    
    def __init__(self, latitude: float, longitude: float):
        """
        Args:
            latitude: 위도 (도 단위)
            longitude: 경도 (도 단위)
        """
        self.latitude = latitude
        self.longitude = longitude
        self.observer = ephem.Observer()
        self.observer.lat = str(latitude)
        self.observer.lon = str(longitude)
        self.sun = ephem.Sun()
    
    def calculate_sunrise_sunset(self, date: str) -> Tuple[str, str]:
        """
        특정 날짜의 일출/일몰 시간 계산
        
        Args:
            date: 날짜 문자열 (YYYYMMDD 형식)
            
        Returns:
            (sunrise_time, sunset_time): HH:MM 형식의 시간 문자열 튜플
        """
        # 날짜 파싱
        dt = datetime.strptime(date, '%Y%m%d')
        self.observer.date = dt
        
        # 일출/일몰 시간 계산
        sunrise = self.observer.next_rising(self.sun)
        sunset = self.observer.next_setting(self.sun)
        
        # UTC를 KST로 변환 (UTC+9)
        sunrise_kst = ephem.localtime(sunrise)
        sunset_kst = ephem.localtime(sunset)
        
        return (
            sunrise_kst.strftime('%H:%M'),
            sunset_kst.strftime('%H:%M')
        )
    
    def get_timeband(self, datetime_str: str) -> int:
        """
        현재 시간의 타임밴드 계산
        타임밴드 정의:
          t1: SR ~ SR+3h
          t2: SR+3h ~ 정오(12:00)
          t3: 정오 ~ SS-3h
          t4: SS-3h ~ SS
          t5: SS ~ SS+3h
          t6: SS+3h ~ 자정(24:00)
          t7: 자정(00:00) ~ SR-3h
          t8: SR-3h ~ SR
        
        Args:
            datetime_str: 'YYYY-MM-DD HH:MM:SS'
        
        Returns:
            timeband(int)
        """
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        date_str = dt.strftime("%Y%m%d")

        # 해당 날짜의 일출/일몰 (KST 문자열 → datetime)
        sr_str, ss_str = self.calculate_sunrise_sunset(date_str)
        SR = datetime.strptime(f"{dt.date()} {sr_str}", "%Y-%m-%d %H:%M")
        SS = datetime.strptime(f"{dt.date()} {ss_str}", "%Y-%m-%d %H:%M")

        # 기준 시각들
        NOON = datetime.combine(dt.date(), time(12, 0))
        DAY_START = datetime.combine(dt.date(), time(0, 0))                 # 00:00
        NEXT_MIDNIGHT = datetime.combine(dt.date() + timedelta(days=1), time(0, 0))  # 다음날 00:00 (24:00)

        # 파생 시각들
        SR_m3 = SR - timedelta(hours=3)
        SR_p3 = SR + timedelta(hours=3)
        SS_m3 = SS - timedelta(hours=3)
        SS_p3 = SS + timedelta(hours=3)

        # 경계 보정 (clamp)
        # t6: [SS+3h, 24:00)
        t6_start = min(SS_p3, NEXT_MIDNIGHT)
        # t7: [00:00, SR-3h)
        t7_end = max(SR_m3, DAY_START)

        def in_(start, end):
            return start <= dt < end  # 반열림 [start, end)

        # 순서는 아무거나 가능하지만, 가독성 위해 하루의 시작부터 순서대로 체크
        if in_(DAY_START, t7_end):   return 7            # t7: 00:00 ~ SR-3h
        if in_(t7_end, SR):          return 8            # t8: SR-3h ~ SR
        if in_(SR, SR_p3):           return 1            # t1: SR ~ SR+3h
        if in_(SR_p3, NOON):         return 2            # t2: SR+3h ~ 정오
        if in_(NOON, SS_m3):         return 3            # t3: 정오 ~ SS-3h
        if in_(SS_m3, SS):           return 4            # t4: SS-3h ~ SS
        if in_(SS, SS_p3):           return 5            # t5: SS ~ SS+3h
        if in_(t6_start, NEXT_MIDNIGHT): return 6        # t6: SS+3h ~ 24:00

        # 예상 밖(경계값) 안전망
        if dt >= NEXT_MIDNIGHT:      return 6
        if dt < DAY_START:           return 7
        return 8