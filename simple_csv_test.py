#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
간단한 CSV Writer 테스트
"""

import os
import sys
import logging
import time
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

def main():
    print("CSV Writer 테스트 시작")
    
    try:
        # 모듈 import
        from csv_writer import CSVWriter
        print("SUCCESS: 모듈 import 성공")
        
        # 디렉토리 확인
        test_dir = "pure_websocket_data"
        print(f"테스트 디렉토리: {os.path.abspath(test_dir)}")
        
        # 권한 확인
        parent_dir = os.getcwd()
        print(f"현재 디렉토리: {parent_dir}")
        print(f"쓰기 권한: {os.access(parent_dir, os.W_OK)}")
        
        # CSVWriter 초기화
        writer = CSVWriter(test_dir)
        print("SUCCESS: CSVWriter 초기화 성공")
        
        # CSV 파일 초기화
        stock_code = "005930"
        success = writer.initialize_stock_csv(stock_code)
        print(f"CSV 초기화: {'성공' if success else '실패'}")
        
        if success:
            # 파일 경로 확인
            filepath = writer.get_csv_filepath(stock_code)
            print(f"파일 경로: {filepath}")
            print(f"파일 존재: {os.path.exists(filepath)}")
            
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                print(f"파일 크기: {size} bytes")
                
                # 테스트 데이터 생성
                test_data = {
                    'time': int(time.time() * 1000),
                    'stock_code': stock_code,
                    'current_price': 70500.0,
                    'volume': 1000000,
                    'ma5': 70400.0,
                    'rsi14': 55.5
                }
                
                # 데이터 쓰기 테스트
                write_success = writer.write_indicators(stock_code, test_data)
                print(f"데이터 쓰기: {'성공' if write_success else '실패'}")
                
                # 파일 크기 재확인
                if write_success and os.path.exists(filepath):
                    new_size = os.path.getsize(filepath)
                    print(f"쓰기 후 파일 크기: {new_size} bytes")
                    
                    # 파일 내용 확인
                    with open(filepath, 'r', encoding='utf-8-sig') as f:
                        content = f.read()
                        print(f"파일 내용 길이: {len(content)} 글자")
                        print("파일 내용 (처음 200자):")
                        print(content[:200])
        
        # 통계
        stats = writer.get_statistics()
        print(f"통계: {stats}")
        
        # 정리
        writer.close_all()
        print("테스트 완료")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()