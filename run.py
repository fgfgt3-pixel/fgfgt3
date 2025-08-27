#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
키움 OpenAPI+ 실시간 데이터 수집 실행 스크립트
32비트 Python 환경에서 실행 필요
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
import struct

# 32비트 Python 경로 설정
PYTHON_32BIT = r"C:\python38_32bit\python.exe"

# 64비트에서 실행된 경우 32비트로 재실행
if struct.calcsize("P") * 8 == 64 and os.path.exists(PYTHON_32BIT):
    print("64비트 Python 감지됨. 32비트 Python으로 재실행합니다...")
    args = [PYTHON_32BIT] + sys.argv
    sys.exit(subprocess.call(args))

# 현재 디렉토리를 시스템 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def check_python_bit():
    """Python 비트 확인"""
    import struct
    bit = struct.calcsize("P") * 8
    print(f"Python {sys.version}")
    print(f"Python {bit}비트 환경")
    
    if bit != 32:
        print("\n[경고] 키움 OpenAPI+는 32비트 Python 환경에서만 작동합니다!")
        print("32비트 Python을 설치하고 다시 실행해주세요.")
        return False
    return True

def check_requirements():
    """필수 모듈 확인"""
    required_modules = {
        'PyQt5': 'PyQt5',
        'pykiwoom': 'pykiwoom',
        'pandas': 'pandas',
        'numpy': 'numpy'
    }
    
    missing_modules = []
    for module, package in required_modules.items():
        try:
            __import__(module)
            print(f"✓ {module} 설치됨")
        except ImportError:
            print(f"✗ {module} 미설치")
            missing_modules.append(package)
    
    if missing_modules:
        print(f"\n필수 모듈이 설치되지 않았습니다.")
        print(f"다음 명령어로 설치하세요:")
        print(f"pip install {' '.join(missing_modules)}")
        return False
    
    return True

def run_main():
    """메인 데이터 수집 프로그램 실행"""
    try:
        from main import main
        print("\n키움 OpenAPI+ 데이터 수집 시작...")
        print("종료하려면 Ctrl+C를 누르세요.\n")
        main()
    except ImportError as e:
        print(f"main.py 파일을 찾을 수 없습니다: {e}")
        return False
    except KeyboardInterrupt:
        print("\n\n프로그램이 사용자에 의해 종료되었습니다.")
        return True
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

def run_test_connection():
    """API 연결 테스트"""
    try:
        from test_connection import test_connection
        print("\n키움 OpenAPI+ 연결 테스트...")
        test_connection()
    except ImportError:
        print("test_connection.py 파일이 없습니다.")
        print("메인 프로그램에서 연결을 테스트합니다.")
        return False
    except Exception as e:
        print(f"연결 테스트 오류: {e}")
        return False

def run_config_check():
    """설정 파일 확인"""
    try:
        from config import TARGET_STOCKS, KiwoomConfig, DataConfig
        print("\n=== 설정 확인 ===")
        print(f"대상 종목: {TARGET_STOCKS}")
        print(f"화면 번호: {KiwoomConfig.SCREEN_NO_BASE}")
        print(f"CSV 저장 경로: {DataConfig.CSV_DIR}")
        return True
    except ImportError as e:
        print(f"config.py 파일을 찾을 수 없습니다: {e}")
        return False
    except Exception as e:
        print(f"설정 확인 오류: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='키움 OpenAPI+ 데이터 수집 프로그램')
    parser.add_argument('--test', action='store_true', help='API 연결 테스트만 실행')
    parser.add_argument('--config', action='store_true', help='설정 확인만 실행')
    parser.add_argument('--skip-check', action='store_true', help='환경 체크 건너뛰기')
    
    args = parser.parse_args()
    
    print("="*50)
    print("키움 OpenAPI+ 실시간 데이터 수집 프로그램")
    print("="*50)
    
    # 환경 체크
    if not args.skip_check:
        if not check_python_bit():
            sys.exit(1)
        
        print("\n=== 필수 모듈 확인 ===")
        if not check_requirements():
            sys.exit(1)
    
    # 설정 확인
    if args.config:
        run_config_check()
        return
    
    # 연결 테스트
    if args.test:
        run_test_connection()
        return
    
    # 설정 확인 후 메인 실행
    if run_config_check():
        run_main()
    else:
        print("\n설정 파일이 없어 프로그램을 실행할 수 없습니다.")
        print("config.py 파일을 먼저 생성해주세요.")

if __name__ == "__main__":
    main()