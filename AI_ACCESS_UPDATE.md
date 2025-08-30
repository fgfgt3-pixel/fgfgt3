# AI_ACCESS_UPDATE.md
<!-- AI 접근용 프로젝트 상태 복원 파일 - Grok 진입점 -->

## 🤖 Grok을 위한 프로젝트 완전 가이드 (2025-08-30)

### 📋 프로젝트 개요
**키움 OpenAPI+ 실시간 데이터 수집 시스템**
- 목적: 실시간 주식 틱 데이터 수집 및 44개 지표 계산
- 상태: **완전 정상 작동** (2025-08-29 마지막 테스트 완료)
- 환경: Python 3.8 32비트 + PyQt5 + Windows 필수

### 🏗️ 핵심 파일 구조 및 역할

#### 1. 메인 실행 파일
- **`main.py`** - 시스템 통합 관리자
  - `KiwoomDataCollector` 클래스: 전체 시스템 오케스트레이션
  - 모든 모듈 초기화 및 콜백 연결
  - 실행: `C:\python38_32bit\python.exe main.py`

#### 2. 키움 API 연결
- **`kiwoom_client.py`** - 키움 OpenAPI+ OCX 컨트롤 관리
  - `KiwoomClient`: 키움 API 래퍼 클래스
  - `SimpleTRManager`: TR 요청 60초 제한 관리 (QTimer 방식)
  - `ConnectionMonitor`: 연결 상태 모니터링 및 자동 재연결
  - 실시간 데이터 등록/수신 (`SetRealReg`, `OnReceiveRealData`)

#### 3. 데이터 처리 엔진
- **`data_processor.py`** - 44개 지표 실시간 계산
  - `IndicatorCalculator`: 36개 기본 지표 계산 (가격, 볼륨, 호가 등)
  - `DataProcessor`: 실시간 데이터 파싱 및 지표 통합
  - `InvestorNetManager`: 11개 수급 지표 관리 (OPT10059 TR)
  - sRealType별 분기 처리 ("주식체결", "주식호가잔량")

#### 4. CSV 저장 시스템
- **`csv_writer.py`** - 배치 저장 최적화
  - `BatchCSVWriter`: 설정 가능한 배치 저장 (기본 100틱)
  - 44개 컬럼 CSV 파일 생성
  - 파일명: `{stock_code}_44indicators_realtime_{YYYYMMDD}.csv`
  - 경로: `pure_websocket_data/` (자동 생성)

#### 5. 설정 관리
- **`config.py`** - 중앙 집중 설정 관리
  - `TARGET_STOCKS`: 대상 종목 리스트 (현재 161390 1개)
  - `KiwoomConfig`: 키움 API 설정 (화면번호, 계정 등)
  - `OptimizedFID`: 실시간 등록용 FID 매핑
  - `DataConfig`: CSV 및 지표 설정

#### 6. 보안 도구
- **`secure_helper.py`** - 암호화된 자동 로그인
  - `SecureLoginHelper`: 인증 정보 암호화 관리
  - 메모리 보안: 사용 후 즉시 삭제

#### 7. 개발 가이드
- **`CLAUDE.md`** - AI 개발 지침서 (핵심 문서)
  - 프로젝트 전체 규칙 및 제약사항
  - 36개 지표 정의 ('수급 지표'는 11개 컬럼 확장)
  - 기술 스펙 및 구현 원칙

### 📊 44개 지표 상세 구성
1. **기본 데이터 (4개)**: time, stock_code, current_price, volume
2. **가격 지표 (5개)**: ma5, rsi14, disparity, stoch_k, stoch_d
3. **볼륨 지표 (3개)**: vol_ratio, z_vol, obv_delta
4. **Bid/Ask 지표 (2개)**: spread, bid_ask_imbalance
5. **기타 지표 (2개)**: accel_delta, ret_1s
6. **호가 가격 (10개)**: ask1~ask5, bid1~bid5
7. **호가 잔량 (6개)**: ask1_qty~ask3_qty, bid1_qty~bid3_qty
8. **수급 지표 (11개)**: 개인, 외인, 기관, 연기금, 투신, 보험, 사모펀드, 은행, 국가, 기타법인, 프로그램
9. **수급 총합 (1개)**: total_investor_net

### 🔧 기술적 핵심 사항

#### 실시간 데이터 처리 방식
- **틱 정의**: 체결 발생 시점만 (가격/거래량 변동시)
- **CSV 저장**: 체결 이벤트만 저장, 호가는 메모리만 업데이트
- **종목별 독립**: 각 종목별 독립적 상태 관리
- **배치 저장**: I/O 최적화를 위한 배치 저장 방식

#### TR 요청 제한 관리
- **동일 TR 60초 1회 제한**: SimpleTRManager로 관리
- **QTimer 기반**: PyQt5 이벤트 루프 호환
- **수급 데이터**: OPT10059 TR 주기적 요청

#### 환경 제약사항
- **32비트 Python 3.8** 필수 (키움 OpenAPI+ 의존)
- **Windows 환경** 필수
- **pykiwoom wrapper** 사용 권장
- **async 사용 금지**: QTimer만 사용

### 🚀 실행 방법

#### 기본 실행
```bash
C:\python38_32bit\python.exe main.py
```

#### 설정 수정
```python
# config.py에서 TARGET_STOCKS 수정
TARGET_STOCKS = ["161390"]  # 현재 설정
```

### 📁 생성되는 데이터 파일

#### CSV 파일 위치
```
pure_websocket_data/
├── 161390_44indicators_realtime_20250829.csv
├── 005930_44indicators_realtime_20250828.csv
└── ...
```

#### 로그 파일
```
logs/
├── main_20250829_141818.log
├── kiwoom_client_20250829.log
└── ...
```

### 🔍 최근 테스트 결과 (2025-08-29)
- **종목**: 161390 (한국타이어앤테크놀로지)
- **데이터 수집**: 정상 (틱 데이터 실시간 수집)
- **지표 계산**: 44개 모두 정상
- **CSV 저장**: 배치 저장 정상 작동
- **수급 데이터**: OPT10059 TR 정상 수신

### 🤖 GitHub 정보
- **URL**: https://github.com/fgfgt3-pixel/fgfgt3
- **브랜치**: main (단일 브랜치)
- **상태**: Public
- **최근 커밋**: 2025-08-29 업데이트

### 📝 중요 참고사항
1. **CLAUDE.md**: AI 개발 시 필수 참조 문서
2. **config.py**: 모든 설정의 중심지
3. **실시간 테스트**: 장 중에만 정상 작동 확인 가능
4. **점진적 확장**: 1개 종목 → 최대 20개 종목까지 테스트

### 🔧 문제 해결
- **연결 실패**: ConnectionMonitor가 자동 재연결
- **TR 제한**: SimpleTRManager가 자동 관리
- **데이터 누락**: rolling window(deque)로 히스토리 관리
- **파일 권한**: logs/, pure_websocket_data/ 자동 생성

---

## 📚 핵심 Python 코드 (Grok 읽기용)

### 1. main.py - 메인 실행 파일
```python
"""
키움 OpenAPI+ 실시간 데이터 수집 시스템 메인 실행
"""
import sys
import time
import signal
import logging
from datetime import datetime
from typing import Dict, Any
from PyQt5.QtCore import QTimer

from config import TARGET_STOCKS, KiwoomConfig, DataConfig, TRCode
from kiwoom_client import KiwoomClient, SimpleTRManager, ConnectionMonitor
from data_processor import DataProcessor, InvestorNetManager
from csv_writer import BatchCSVWriter

class KiwoomDataCollector:
    """키움 OpenAPI+ 실시간 데이터 수집 시스템 메인 클래스"""
    
    def __init__(self, target_stocks: list = None):
        self.target_stocks = target_stocks or TARGET_STOCKS
        self.running = False
        
        # 모듈 초기화
        self.kiwoom_client = None
        self.data_processor = None
        self.csv_writer = None
        self.tr_manager = None
        self.connection_monitor = None
        self.investor_manager = None
    
    def initialize_modules(self) -> bool:
        """모든 모듈 초기화"""
        # 1. 키움 클라이언트
        self.kiwoom_client = KiwoomClient()
        
        # 2. QTimer 기반 관리자들
        self.tr_manager = SimpleTRManager(self.kiwoom_client)
        self.connection_monitor = ConnectionMonitor(self.kiwoom_client)
        self.investor_manager = InvestorNetManager(self.target_stocks)
        
        # 3. 데이터 프로세서
        self.data_processor = DataProcessor(self.target_stocks, self.kiwoom_client)
        
        # 4. CSV 저장소
        self.csv_writer = BatchCSVWriter(self.target_stocks)
        
        return True
    
    def connect_callbacks(self):
        """콜백 연결"""
        # 실시간 데이터 콜백
        self.kiwoom_client.register_callback(
            'on_receive_real_data', 
            self.on_realtime_data
        )
        
        # TR 데이터 콜백
        self.kiwoom_client.register_callback(
            'on_receive_tr_data',
            self.on_tr_data
        )
    
    def start(self):
        """시스템 시작"""
        if not self.kiwoom_client.connect():
            return False
            
        # 실시간 데이터 등록
        self.kiwoom_client.register_realdata(self.target_stocks)
        
        # 연결 모니터링 시작
        self.connection_monitor.start()
        
        # 수급 데이터 업데이트 시작
        self.setup_investor_update()
        
        self.running = True
        return True
```

### 2. kiwoom_client.py - 키움 API 클라이언트
```python
"""
키움 OpenAPI+ 클라이언트
"""
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
import time
import logging

class KiwoomClient(QObject):
    """키움 OpenAPI+ OCX 컨트롤 관리"""
    
    def __init__(self):
        super().__init__()
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.connected = False
        self.callbacks = {}
        
        # 이벤트 연결
        self.ocx.OnEventConnect.connect(self._on_event_connect)
        self.ocx.OnReceiveRealData.connect(self._on_receive_real_data)
        self.ocx.OnReceiveTrData.connect(self._on_receive_tr_data)
    
    def connect(self) -> bool:
        """키움 서버 연결"""
        err = self.ocx.dynamicCall("CommConnect()")
        if err != 0:
            return False
        
        # 로그인 대기
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()
        
        return self.connected
    
    def register_realdata(self, stocks: list) -> bool:
        """실시간 데이터 등록"""
        SCREEN_BASE_TRADE = "5000"  # 체결용
        SCREEN_BASE_HOGA = "6000"   # 호가용
        
        for idx, stock_code in enumerate(stocks):
            # 기존 등록 제거
            self.ocx.dynamicCall("SetRealRemove(QString, QString)", "ALL", stock_code)
            time.sleep(0.05)
            
            # 체결 데이터 등록
            screen_trade = f"{SCREEN_BASE_TRADE}{idx:02d}"
            ret = self.ocx.dynamicCall(
                "SetRealReg(QString, QString, QString, QString)",
                screen_trade,
                stock_code,
                "10;11;12;13;14;15;16;17;18;20",  # 체결 FID
                "0" if idx == 0 else "1"
            )
            
            # 호가 데이터 등록
            screen_hoga = f"{SCREEN_BASE_HOGA}{idx:02d}"
            ret = self.ocx.dynamicCall(
                "SetRealReg(QString, QString, QString, QString)",
                screen_hoga,
                stock_code,
                "41;42;43;44;45;51;52;53;54;55",  # 호가 FID
                "1"
            )
        
        return True
    
    def _on_receive_real_data(self, sCode, sRealType, sRealData):
        """실시간 데이터 수신"""
        if sRealType == "주식체결":
            data = self._parse_trade_data(sCode, sRealData)
        elif sRealType in ["주식호가잔량", "주식호가"]:
            data = self._parse_hoga_data(sCode, sRealData)
        else:
            return
        
        # 콜백 실행
        if 'on_receive_real_data' in self.callbacks:
            self.callbacks['on_receive_real_data'](sCode, sRealType, data)
```

### 3. data_processor.py - 데이터 처리 엔진
```python
"""
실시간 데이터 처리 및 36개 지표 계산
"""
from collections import deque
import numpy as np
import time
from typing import Dict, Optional

class IndicatorCalculator:
    """36개 지표 실시간 계산"""
    
    def __init__(self, stock_code: str, buffer_size: int = 200):
        self.stock_code = stock_code
        self.buffer_size = buffer_size
        
        # 데이터 버퍼
        self.price_buffer = deque(maxlen=buffer_size)
        self.volume_buffer = deque(maxlen=buffer_size)
        self.time_buffer = deque(maxlen=buffer_size)
        self.high_buffer = deque(maxlen=buffer_size)
        self.low_buffer = deque(maxlen=buffer_size)
        
    def update_tick_data(self, tick_data: Dict) -> Dict:
        """틱 데이터 업데이트 및 지표 계산"""
        # 시간과 가격 추출
        current_time = int(tick_data.get('time', int(time.time() * 1000)))
        current_price = float(tick_data.get('current_price', 0))
        current_volume = int(tick_data.get('volume', 0))
        
        if current_price <= 0:
            return {}
        
        # 버퍼 업데이트
        self.price_buffer.append(current_price)
        self.volume_buffer.append(current_volume)
        self.time_buffer.append(current_time)
        
        # 36개 지표 계산
        indicators = self._calculate_all_indicators(tick_data)
        
        return indicators
    
    def _calculate_all_indicators(self, tick_data: Dict) -> Dict:
        """36개 지표 전체 계산"""
        result = {
            # 기본 데이터
            'time': tick_data.get('time'),
            'stock_code': self.stock_code,
            'current_price': tick_data.get('current_price'),
            'volume': tick_data.get('volume'),
            
            # 가격 지표
            'ma5': self._calculate_ma(5),
            'rsi14': self._calculate_rsi(14),
            'disparity': self._calculate_disparity(),
            'stoch_k': self._calculate_stochastic_k(14),
            'stoch_d': self._calculate_stochastic_d(14, 3),
            
            # 볼륨 지표
            'vol_ratio': self._calculate_volume_ratio(),
            'z_vol': self._calculate_z_score_volume(),
            'obv_delta': self._calculate_obv_delta(),
            
            # 호가 지표
            'spread': self._calculate_spread(tick_data),
            'bid_ask_imbalance': self._calculate_bid_ask_imbalance(tick_data),
        }
        
        # 호가 데이터 추가
        for i in range(1, 6):
            result[f'ask{i}'] = tick_data.get(f'ask{i}', 0)
            result[f'bid{i}'] = tick_data.get(f'bid{i}', 0)
            if i <= 3:
                result[f'ask{i}_qty'] = tick_data.get(f'ask{i}_qty', 0)
                result[f'bid{i}_qty'] = tick_data.get(f'bid{i}_qty', 0)
        
        return result
    
    def _calculate_ma(self, period: int) -> float:
        """이동평균 계산"""
        if len(self.price_buffer) < period:
            if len(self.price_buffer) > 0:
                return sum(self.price_buffer) / len(self.price_buffer)
            return 0
        return sum(list(self.price_buffer)[-period:]) / period
```

---
**업데이트**: 2025-08-30 Grok 접근 복원용 - Python 코드 포함
**상태**: 프로덕션 레디 (실전 서버 테스트 완료)