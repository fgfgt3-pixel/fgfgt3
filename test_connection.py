#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kiwoom API 연결 및 실시간 데이터 수신 테스트
"""

import sys
import logging
import time
from PyQt5.QtWidgets import QApplication

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_kiwoom_connection():
    """Kiwoom API 연결 테스트"""
    print("=" * 60)
    print("Kiwoom API 연결 테스트")
    print("=" * 60)
    
    try:
        # QApplication 생성 (필수)
        app = QApplication(sys.argv)
        
        # KiwoomClient import 및 초기화
        from kiwoom_client import KiwoomClient
        from config import TARGET_STOCKS
        
        print(f"1. 대상 종목: {TARGET_STOCKS}")
        
        # 클라이언트 생성
        print("2. KiwoomClient 초기화...")
        client = KiwoomClient()
        
        # 데이터 수신 콜백 설정
        def test_realdata_callback(stock_code, real_type, data):
            print(f"[실시간데이터] {stock_code} - {real_type} - 가격: {data.get('current_price', 'N/A')}")
        
        client.set_realdata_callback(test_realdata_callback)
        
        # 연결 시도
        print("3. Kiwoom 서버 연결 시도...")
        if client.connect():
            print("✓ 연결 성공!")
            
            # 계좌 정보 확인
            print("4. 계좌 정보 확인...")
            accounts = client.get_login_info("ACCNO")
            print(f"계좌: {accounts}")
            
            # 실시간 데이터 등록
            print("5. 실시간 데이터 등록...")
            if client.register_realdata(TARGET_STOCKS[:1]):  # 첫 번째 종목만 테스트
                print("✓ 실시간 등록 성공!")
                
                print("6. 실시간 데이터 대기 중... (30초)")
                print("   데이터가 수신되면 위에 출력됩니다.")
                print("   시장이 열려있지 않으면 데이터가 오지 않을 수 있습니다.")
                
                # 30초 대기
                start_time = time.time()
                while time.time() - start_time < 30:
                    app.processEvents()
                    time.sleep(0.1)
                
                print("7. 테스트 종료")
                
            else:
                print("✗ 실시간 등록 실패")
        else:
            print("✗ 연결 실패")
            print("   - Kiwoom Hero4 OpenAPI+ 설치 확인")
            print("   - 32비트 Python 사용 확인")
            print("   - 로그인 정보 확인 (config.py)")
        
        # 연결 해제
        client.disconnect()
        print("연결 해제 완료")
        
    except ImportError as e:
        print(f"✗ 모듈 import 오류: {e}")
        print("필요한 모듈이 설치되지 않았을 수 있습니다.")
    except Exception as e:
        print(f"✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_kiwoom_connection()