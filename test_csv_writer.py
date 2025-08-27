#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CSV Writer 독립 테스트 스크립트
modify.md 분석에 따른 문제 진단
"""

import os
import logging
import time
from datetime import datetime
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('csv_test.log', encoding='utf-8')
    ]
)

def test_csv_writer():
    """CSVWriter 독립 테스트"""
    print("=" * 50)
    print("CSV Writer 독립 테스트 시작")
    print("=" * 50)
    
    try:
        # CSV Writer import 테스트
        print("\n1. 모듈 import 테스트...")
        from csv_writer import CSVWriter
        from config import IndicatorConfig
        print("[SUCCESS] 모듈 import 성공")
        
        # 디렉토리 확인
        print("\n2. 디렉토리 확인...")
        test_dir = "pure_websocket_data"
        print(f"테스트 디렉토리: {os.path.abspath(test_dir)}")
        
        # CSVWriter 초기화 테스트
        print("\n3. CSVWriter 초기화...")
        writer = CSVWriter(test_dir)
        print("✓ CSVWriter 초기화 성공")
        
        # 테스트 종목
        stock_code = "005930"
        print(f"\n4. 테스트 종목: {stock_code}")
        
        # CSV 초기화 테스트
        print("\n5. CSV 파일 초기화 테스트...")
        success = writer.initialize_stock_csv(stock_code)
        if success:
            print("[SUCCESS] CSV 초기화 성공")
            
            # 파일 경로 확인
            filepath = writer.get_csv_filepath(stock_code)
            print(f"생성된 파일 경로: {filepath}")
            print(f"파일 존재 여부: {os.path.exists(filepath)}")
            
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"파일 크기: {file_size} bytes")
        else:
            print("✗ CSV 초기화 실패")
            return False
        
        # 테스트 데이터 생성
        print("\n6. 테스트 데이터 생성...")
        test_indicators = {
            'time': int(time.time() * 1000),
            'stock_code': stock_code,
            'current_price': 70500.0,
            'volume': 1000000,
            'ma5': 70400.0,
            'rsi14': 55.5,
            'disparity': 1.02,
            'stoch_k': 60.5,
            'stoch_d': 58.3,
            'vol_ratio': 1.5,
            'z_vol': 0.8,
            'obv_delta': 1000,
            'spread': 100.0,
            'bid_ask_imbalance': 0.1,
            'ask1': 70600.0, 'ask2': 70700.0, 'ask3': 70800.0, 'ask4': 70900.0, 'ask5': 71000.0,
            'bid1': 70500.0, 'bid2': 70400.0, 'bid3': 70300.0, 'bid4': 70200.0, 'bid5': 70100.0,
            'ask1_qty': 100, 'ask2_qty': 150, 'ask3_qty': 200, 'ask4_qty': 120, 'ask5_qty': 180,
            'bid1_qty': 120, 'bid2_qty': 180, 'bid3_qty': 90, 'bid4_qty': 200, 'bid5_qty': 150,
        }
        
        # 수급 지표 추가 (11개)
        investor_indicators = {
            'indiv_net_vol': 1000, 'foreign_net_vol': -500, 'inst_net_vol': 2000,
            'pension_net_vol': 300, 'trust_net_vol': -100, 'insurance_net_vol': 200,
            'private_fund_net_vol': 150, 'bank_net_vol': 50, 'state_net_vol': 0,
            'other_net_vol': 100, 'prog_net_vol': -200
        }
        test_indicators.update(investor_indicators)
        
        print(f"테스트 데이터 키 개수: {len(test_indicators)}")
        print(f"예상 CSV 헤더 개수: {len(IndicatorConfig.ALL_INDICATORS)}")
        
        # 데이터 쓰기 테스트
        print("\n7. 데이터 쓰기 테스트...")
        for i in range(5):
            # 데이터 변경
            test_indicators['current_price'] += i * 100
            test_indicators['time'] += i * 1000
            
            success = writer.write_indicators(stock_code, test_indicators)
            print(f"쓰기 {i+1}: {'성공' if success else '실패'}")
            
            if success:
                # 파일 크기 확인
                filepath = writer.get_csv_filepath(stock_code)
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    print(f"  파일 크기: {file_size} bytes")
        
        # 통계 확인
        print("\n8. 통계 확인...")
        stats = writer.get_statistics()
        print(f"통계: {stats}")
        
        # 파일 내용 확인
        print("\n9. 파일 내용 확인...")
        filepath = writer.get_csv_filepath(stock_code)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                print(f"파일 라인 수: {len(lines)}")
                if lines:
                    print(f"헤더: {lines[0][:100]}...")
                    if len(lines) > 1:
                        print(f"첫 데이터: {lines[1][:100]}...")
        
        # 정리
        print("\n10. 정리...")
        writer.close_all()
        print("✓ 테스트 완료")
        
        return True
        
    except Exception as e:
        print(f"✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_directory_permissions():
    """디렉토리 권한 테스트"""
    print("\n" + "=" * 50)
    print("디렉토리 권한 테스트")
    print("=" * 50)
    
    test_dir = "pure_websocket_data"
    
    try:
        # 현재 작업 디렉토리
        current_dir = os.getcwd()
        print(f"현재 작업 디렉토리: {current_dir}")
        
        # 테스트 디렉토리 절대 경로
        abs_test_dir = os.path.abspath(test_dir)
        print(f"테스트 디렉토리 절대 경로: {abs_test_dir}")
        
        # 상위 디렉토리 권한 확인
        parent_dir = os.path.dirname(abs_test_dir)
        print(f"상위 디렉토리: {parent_dir}")
        print(f"상위 디렉토리 존재: {os.path.exists(parent_dir)}")
        print(f"상위 디렉토리 쓰기 권한: {os.access(parent_dir, os.W_OK)}")
        
        # 디렉토리 생성 테스트
        if not os.path.exists(abs_test_dir):
            os.makedirs(abs_test_dir, exist_ok=True)
            print(f"✓ 디렉토리 생성 성공: {abs_test_dir}")
        else:
            print(f"✓ 디렉토리 이미 존재: {abs_test_dir}")
        
        # 디렉토리 권한 확인
        print(f"디렉토리 읽기 권한: {os.access(abs_test_dir, os.R_OK)}")
        print(f"디렉토리 쓰기 권한: {os.access(abs_test_dir, os.W_OK)}")
        print(f"디렉토리 실행 권한: {os.access(abs_test_dir, os.X_OK)}")
        
        # 테스트 파일 생성
        test_file = os.path.join(abs_test_dir, "test.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("test")
        print(f"✓ 테스트 파일 생성 성공: {test_file}")
        
        # 테스트 파일 삭제
        os.remove(test_file)
        print("✓ 테스트 파일 삭제 성공")
        
        return True
        
    except Exception as e:
        print(f"✗ 디렉토리 권한 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 디렉토리 권한 테스트
    dir_test_result = test_directory_permissions()
    
    # CSV Writer 테스트
    if dir_test_result:
        csv_test_result = test_csv_writer()
        
        print("\n" + "=" * 50)
        print("테스트 결과 요약")
        print("=" * 50)
        print(f"디렉토리 권한 테스트: {'성공' if dir_test_result else '실패'}")
        print(f"CSV Writer 테스트: {'성공' if csv_test_result else '실패'}")
        
        if csv_test_result:
            print("\n✓ CSV 파일 생성 기능 정상 작동")
            print("문제가 상위 모듈에 있을 가능성이 높습니다.")
        else:
            print("\n✗ CSV Writer 자체에 문제가 있습니다.")
            print("csv_writer.py 코드를 점검해야 합니다.")
    else:
        print("\n✗ 디렉토리 권한 문제로 인해 CSV 테스트를 건너뜁니다.")