#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
데이터 흐름 테스트 - Kiwoom API 없이 전체 파이프라인 테스트
"""

import os
import logging
import time
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

def test_data_flow():
    """전체 데이터 흐름 테스트"""
    print("=" * 60)
    print("데이터 흐름 테스트 시작")
    print("=" * 60)
    
    try:
        # 모듈 import
        from data_processor import DataProcessor
        from csv_writer import BatchCSVWriter
        
        # 테스트 종목
        test_stocks = ['005930']
        
        # 1. DataProcessor 초기화
        print("1. DataProcessor 초기화...")
        processor = DataProcessor(test_stocks)
        
        # 2. CSV Writer 초기화
        print("2. BatchCSVWriter 초기화...")
        csv_writer = BatchCSVWriter("pure_websocket_data", batch_size=3)
        
        # 3. 콜백 함수 정의
        def test_callback(stock_code, indicators):
            """테스트 콜백 함수"""
            print(f"[CALLBACK] {stock_code} - 지표개수: {len(indicators)} - 가격: {indicators.get('current_price')}")
            
            # CSV 저장
            success = csv_writer.write_indicators(stock_code, indicators)
            print(f"[CSV] {stock_code} - 저장: {'성공' if success else '실패'}")
        
        # 4. 콜백 연결
        print("3. 콜백 연결...")
        processor.set_indicator_callback(test_callback)
        
        # 5. 모의 실시간 데이터 생성 및 처리
        print("4. 모의 실시간 데이터 처리...")
        
        stock_code = '005930'
        base_price = 70000
        base_volume = 1000000
        
        for i in range(10):  # 10틱 데이터 생성
            # 모의 틱 데이터
            tick_data = {
                'time': int(time.time() * 1000) + i * 1000,
                'current_price': base_price + i * 100,
                'volume': base_volume + i * 1000,
                'ask1': base_price + i * 100 + 50,
                'bid1': base_price + i * 100 - 50,
                'ask1_qty': 100 + i * 10,
                'bid1_qty': 120 + i * 5,
            }
            
            print(f"\n--- 틱 #{i+1} ---")
            print(f"입력 데이터: 가격={tick_data['current_price']}, 거래량={tick_data['volume']}")
            
            # 실시간 데이터 처리
            result = processor.process_realdata(stock_code, '주식체결', tick_data)
            
            if result:
                print(f"처리 결과: {len(result)}개 지표")
            else:
                print("처리 결과: None")
            
            time.sleep(0.1)  # 잠시 대기
        
        # 6. 남은 배치 플러시
        print("\n5. 배치 플러시...")
        csv_writer.flush_all_buffers()
        
        # 7. 결과 확인
        print("\n6. 결과 확인...")
        csv_stats = csv_writer.get_statistics()
        print(f"CSV 통계: {csv_stats}")
        
        # CSV 파일 확인
        filepath = csv_writer.get_csv_filepath(stock_code)
        if os.path.exists(filepath):
            print(f"생성된 CSV 파일: {filepath}")
            print(f"파일 크기: {os.path.getsize(filepath)} bytes")
            
            # 파일 내용 일부 출력
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                print(f"총 라인 수: {len(lines)}")
                if len(lines) > 0:
                    print("헤더:")
                    print(lines[0][:100] + "...")
                if len(lines) > 1:
                    print("첫 번째 데이터:")
                    print(lines[1][:100] + "...")
        else:
            print("CSV 파일이 생성되지 않았습니다!")
        
        # 8. 정리
        print("\n7. 정리...")
        csv_writer.close_all()
        
        print("\n✓ 데이터 흐름 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_data_flow()
    print(f"\n테스트 결과: {'성공' if success else '실패'}")