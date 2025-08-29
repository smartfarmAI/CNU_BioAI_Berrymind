#!/usr/bin/env python3
"""
predictions.csv에 바운더리 클리핑을 적용하는 스크립트
"""

import pandas as pd
from data_check_utils import apply_boundary_clipping

def main():
    print("🔄 predictions.csv 로딩 중...")
    
    # predictions.csv 로드
    predictions_df = pd.read_csv('/Users/jay/workspace/berrymind/predictions.csv')
    
    print(f"📊 원본 데이터 크기: {predictions_df.shape}")
    print(f"📋 컬럼 목록:")
    for i, col in enumerate(predictions_df.columns, 1):
        print(f"  {i:2d}. {col}")
    
    # 클리핑할 컬럼들과 바운더리 룰 정의
    clipping_rules = {
        # 온도 관련 컬럼들 (-10 ~ 50도)
        'temp_columns': {
            'boundary_rule': {'min': -10, 'max': 50},
            'columns': [
                'after_30min_indoor_temp_1_pred',
                'after_30min_indoor_temp_1_actual', 
                'after_30min_indoor_temp_2_pred',
                'after_30min_indoor_temp_2_actual'
            ]
        },
        # 습도 관련 컬럼들 (0 ~ 100%)
        'humidity_columns': {
            'boundary_rule': {'min': 0, 'max': 100},
            'columns': [
                'after_30min_indoor_humidity_1_pred',
                'after_30min_indoor_humidity_1_actual',
                'after_30min_indoor_humidity_2_pred', 
                'after_30min_indoor_humidity_2_actual'
            ]
        },
        # CO2 농도 관련 컬럼들 (0 ~ 5000ppm)
        'co2_columns': {
            'boundary_rule': {'min': 0, 'max': 5000},
            'columns': [
                'after_30min_co2_concentration_1_pred',
                'after_30min_co2_concentration_1_actual'
            ]
        }
    }
    
    # 클리핑 적용
    print("\n🔧 바운더리 클리핑 적용 중...")
    clipped_df = predictions_df.copy()
    
    for rule_name, rule_config in clipping_rules.items():
        print(f"  📌 {rule_name} 적용: {rule_config['boundary_rule']}")
        
        # 존재하는 컬럼만 필터링
        existing_columns = [col for col in rule_config['columns'] 
                           if col in clipped_df.columns]
        
        if existing_columns:
            print(f"     적용 대상: {existing_columns}")
            clipped_df = apply_boundary_clipping(
                df=clipped_df,
                boundary_rule=rule_config['boundary_rule'],
                columns=existing_columns
            )
        else:
            print(f"     ⚠️  해당 컬럼들이 존재하지 않음")
    
    # 클리핑 전후 비교
    print("\n📈 클리핑 효과 분석:")
    for rule_name, rule_config in clipping_rules.items():
        existing_columns = [col for col in rule_config['columns'] 
                           if col in predictions_df.columns]
        
        if existing_columns:
            min_val = rule_config['boundary_rule']['min']
            max_val = rule_config['boundary_rule']['max']
            
            for col in existing_columns:
                original = predictions_df[col]
                clipped = clipped_df[col]
                
                clipped_count = ((original < min_val) | (original > max_val)).sum()
                if clipped_count > 0:
                    print(f"  🔄 {col}: {clipped_count}개 값 클리핑됨")
                    print(f"     범위 전: [{original.min():.3f}, {original.max():.3f}]")
                    print(f"     범위 후: [{clipped.min():.3f}, {clipped.max():.3f}]")
    
    # 클리핑된 결과 저장
    output_file = '/Users/jay/workspace/berrymind/predictions_clipped.csv'
    print(f"\n💾 클리핑된 데이터 저장: {output_file}")
    clipped_df.to_csv(output_file, index=False)
    
    print("✅ 완료!")
    print(f"📁 원본: predictions.csv ({predictions_df.shape})")
    print(f"📁 클리핑: predictions_clipped.csv ({clipped_df.shape})")

if __name__ == "__main__":
    main()
