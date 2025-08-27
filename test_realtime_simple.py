#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
간단한 Kiwoom 연결 테스트 - 핸들값 에러 진단용
"""

import sys
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget

def test_kiwoom_simple():
    """가장 기본적인 Kiwoom 연결 테스트"""
    print("=" * 50)
    print("Kiwoom 간단 연결 테스트")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    
    try:
        print("1. QAxWidget 생성 시도...")
        
        # 키움 OpenAPI+ ActiveX 컨트롤 생성
        kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        print("   ✓ QAxWidget 생성 성공")
        
        print("2. CommConnect 호출...")
        
        # 연결 시도
        result = kiwoom.dynamicCall("CommConnect()")
        print(f"   CommConnect 결과: {result}")
        
        if result == 0:
            print("   ✓ 연결 요청 성공 - 로그인 창이 나타나야 합니다")
            
            # 5초 대기 (사용자가 로그인할 시간)
            print("3. 5초 대기 중... (로그인 창에서 로그인 해주세요)")
            for i in range(5):
                print(f"   {5-i}초...")
                time.sleep(1)
                app.processEvents()
            
            # 연결 상태 확인
            connected = kiwoom.dynamicCall("GetConnectState()")
            print(f"4. 연결 상태 확인: {connected}")
            if connected == 1:
                print("   ✓ 로그인 성공!")
                
                # 계좌 정보 가져오기
                accounts = kiwoom.dynamicCall("GetLoginInfo(QString)", "ACCNO")
                print(f"   계좌 목록: {accounts}")
                
            else:
                print("   ✗ 로그인 실패 또는 미완료")
        else:
            print(f"   ✗ 연결 요청 실패: {result}")
            print("   가능한 원인:")
            print("   - 키움 Hero4 OpenAPI+ 미설치")
            print("   - 32비트 Python 환경 문제")
            print("   - ActiveX 컨트롤 등록 문제")
            
        # 연결 해제
        kiwoom.dynamicCall("CommTerminate()")
        
    except Exception as e:
        print(f"✗ 오류 발생: {e}")
        print("가능한 해결책:")
        print("1. 키움증권 OpenAPI+ 설치 확인")
        print("2. 32비트 Python 사용 확인")
        print("3. 관리자 권한으로 실행")
        
    print("=" * 50)
    print("테스트 완료")

if __name__ == "__main__":
    test_kiwoom_simple()