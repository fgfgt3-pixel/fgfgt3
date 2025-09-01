# AI_ACCESS_UPDATE.md
<!-- AI 접근용 프로젝트 상태 복원 파일 - Grok 진입점 -->

## 🤖 Grok을 위한 프로젝트 완전 가이드 (2025-09-01)

### 📋 프로젝트 개요
**키움 OpenAPI+ 실시간 데이터 수집 시스템**
- 목적: 실시간 주식 틱 데이터 수집 및 44개 지표 계산
- 상태: **크래시 분석 시스템 추가** (2025-09-01 업데이트)
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

#### 7. 시스템 모니터링 (NEW - 2025-09-01)
- **`system_monitor.py`** - 크래시 분석 및 실시간 모니터링
  - `SystemCrashDetector`: 메모리/CPU 사용량, 하트비트 모니터링
  - `ConnectionStabilityMonitor`: 키움 연결 상태 실시간 체크
  - `ExceptionTracker`: 모든 예외 발생 추적 및 로깅
  - `FilePermissionMonitor`: CSV 파일 권한 및 디스크 공간 체크
  - 크래시 시 자동 스냅샷 저장: `logs/crash_snapshot_YYYYMMDD_HHMMSS.log`

#### 8. 개발 가이드
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
C:\python38_32bit\python.exe main.py

#### 설정 수정
config.py에서 TARGET_STOCKS 수정
TARGET_STOCKS = ["161390"]  # 현재 설정

### 📁 생성되는 데이터 파일

#### CSV 파일 위치
pure_websocket_data/
├── 161390_44indicators_realtime_20250829.csv
├── 005930_44indicators_realtime_20250828.csv
└── ...

#### 로그 파일
logs/
├── main_20250829_141818.log
├── kiwoom_client_20250829.log
└── ...

### 🔍 최근 테스트 결과 (2025-09-01)
- **종목**: 10개 종목 동시 수집 성공
- **데이터 수집**: 정상 (09:02~14:01, 약 5시간)
- **지표 계산**: 44개 모두 정상
- **CSV 저장**: Permission denied 오류로 중단 (09:22 이후)
- **크래시 원인**: 14:01:21 갑작스런 종료 - 원인 미상
- **해결책**: 시스템 모니터링 시스템 추가 (system_monitor.py)

### 🤖 GitHub 정보
- **URL**: https://github.com/fgfgt3-pixel/fgfgt3
- **브랜치**: main (단일 브랜치)
- **상태**: Public
- **최근 커밋**: 2025-08-31 코드 텍스트 형식 업데이트

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
- **크래시 분석**: SystemCrashDetector가 실시간 모니터링 (NEW)
- **예외 추적**: ExceptionTracker가 모든 예외 로깅 (NEW)
- **자동 스냅샷**: 크래시 시 logs/crash_snapshot_*.log 저장 (NEW)

---

## 📚 핵심 Python 코드 (텍스트 형식 - Grok 읽기용)

아래는 Python 코드를 순수 텍스트로 변환한 내용입니다. 코드 블록 대신 일반 텍스트로 제공하여 Grok이 읽을 수 있도록 했습니다.

### ========== main.py 핵심 코드 ==========

키움 OpenAPI+ 실시간 데이터 수집 시스템 메인 실행
CLAUDE.md 기반 - 틱 기반 데이터 취합, 33개 지표 계산, CSV 저장

import sys
import time
import signal
import logging
from datetime import datetime
from typing import Dict, Any
from PyQt5.QtCore import QTimer

from config import TARGET_STOCKS, KiwoomConfig, DataConfig, TRCode, validate_config
from kiwoom_client import KiwoomClient, SimpleTRManager, ConnectionMonitor
from data_processor import DataProcessor, InvestorNetManager
from csv_writer import BatchCSVWriter

class KiwoomDataCollector:
    # 키움 OpenAPI+ 실시간 데이터 수집 시스템 메인 클래스
    
    def __init__(self, target_stocks: list = None):
        self.target_stocks = target_stocks or TARGET_STOCKS
        self.running = False
        
        # 로깅 설정
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 모듈 초기화
        self.kiwoom_client: KiwoomClient = None
        self.data_processor: DataProcessor = None
        self.csv_writer: BatchCSVWriter = None
        
        # QTimer 기반 관리자들
        self.tr_manager: SimpleTRManager = None
        self.connection_monitor: ConnectionMonitor = None
        self.investor_manager: InvestorNetManager = None
        
        # 통계
        self.start_time = None
        self.tick_counts = {}
        self.last_stats_time = time.time()
    
    def initialize_modules(self) -> bool:
        # 모든 모듈 초기화
        try:
            # 1. 키움 클라이언트 초기화
            self.kiwoom_client = KiwoomClient()
            
            # 2. QTimer 기반 관리자들 초기화
            self.tr_manager = SimpleTRManager(self.kiwoom_client)
            self.connection_monitor = ConnectionMonitor(self.kiwoom_client)
            self.investor_manager = InvestorNetManager(self.target_stocks)
            
            # 3. 데이터 프로세서 초기화
            self.data_processor = DataProcessor(self.target_stocks, self.kiwoom_client)
            
            # 4. CSV 저장소 초기화
            self.csv_writer = BatchCSVWriter(
                base_dir=DataConfig.CSV_DIR,
                batch_size=DataConfig.CSV_BATCH_SIZE
            )
            
            # 5. 콜백 함수 연결
            self.kiwoom_client.set_realdata_callback(self.on_realdata_received)
            self.kiwoom_client.set_tr_callback(self.on_tr_data_received)
            self.data_processor.set_indicator_callback(self.on_indicators_calculated)
            
            return True
        except Exception as e:
            self.logger.error(f"모듈 초기화 실패: {e}")
            return False
    
    def connect_and_register(self) -> bool:
        # 키움 연결 및 실시간 데이터 등록
        # 키움 서버 연결
        if not self.kiwoom_client.connect():
            return False
        
        # 실시간 데이터 등록
        if not self.kiwoom_client.register_realdata(self.target_stocks):
            return False
        
        # 수급 데이터 TR 스케줄링 시작
        for i, stock_code in enumerate(self.target_stocks):
            QTimer.singleShot(i * 200, lambda sc=stock_code: self.tr_manager.request_opt10059(sc))
        
        return True
    
    def on_realdata_received(self, stock_code: str, real_type: str, real_data: Dict):
        # 실시간 데이터 수신 콜백
        if real_type == "주식체결":
            self.data_processor.process_tick_data(stock_code, real_data)
            self.tick_counts[stock_code] = self.tick_counts.get(stock_code, 0) + 1
        elif real_type in ["주식호가잔량", "주식호가"]:
            self.data_processor.update_hoga_data(stock_code, real_data)
    
    def on_indicators_calculated(self, stock_code: str, indicators: Dict):
        # 지표 계산 완료 콜백 - CSV 저장
        self.csv_writer.write_indicators(stock_code, indicators)
    
    def run(self):
        # 메인 실행 루프
        try:
            if not self.initialize_modules():
                return
            
            if not self.connect_and_register():
                return
            
            # 연결 모니터링 시작
            self.connection_monitor.start()
            
            self.running = True
            self.start_time = time.time()
            
            # PyQt5 이벤트 루프 실행
            self.app.exec_()
            
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            self.logger.error(f"실행 중 오류: {e}")
            self.stop()

### ========== kiwoom_client.py 핵심 코드 ==========

키움 OpenAPI+ 클라이언트
CLAUDE.md 기반 - 로그인/연결/실시간 이벤트 처리, 틱 기반 데이터 취합

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QAxContainer import QAxWidget  
from PyQt5.QtCore import QEventLoop, QTimer

class KiwoomClient:
    # 키움 OpenAPI+ 클라이언트 - 로그인/연결 관리, 실시간 데이터 수신
    
    def __init__(self):
        # QApplication 설정
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
        
        # OCX용 숨겨진 윈도우 생성
        self.window = QWidget()
        self.window.setWindowTitle("Kiwoom OpenAPI Data Collector")
        self.window.resize(100, 100)
        self.window.hide()
        
        # OCX 컨트롤 생성
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1", self.window)
        
        # 연결 상태
        self.connected = False
        self.registered_stocks = set()
        
        # 콜백 함수들
        self.realdata_callback = None
        self.tr_callback = None
        
        # 이벤트 연결
        self.setup_events()
    
    def setup_events(self):
        # 이벤트 핸들러 연결
        self.ocx.OnEventConnect.connect(self._on_event_connect)
        self.ocx.OnReceiveRealData.connect(self._on_receive_real_data)
        self.ocx.OnReceiveTrData.connect(self._on_receive_tr_data)
    
    def connect(self) -> bool:
        # 키움 서버 연결
        err = self.ocx.dynamicCall("CommConnect()")
        if err != 0:
            return False
        
        # 로그인 대기
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()
        
        return self.connected
    
    def register_realdata(self, stocks: list) -> bool:
        # 실시간 데이터 등록
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
            
            self.registered_stocks.add(stock_code)
        
        return True
    
    def _on_receive_real_data(self, sCode, sRealType, sRealData):
        # 실시간 데이터 수신 이벤트
        if sRealType == "주식체결":
            data = self._parse_trade_data(sCode, sRealData)
        elif sRealType in ["주식호가잔량", "주식호가"]:
            data = self._parse_hoga_data(sCode, sRealData)
        else:
            return
        
        # 콜백 실행
        if self.realdata_callback:
            self.realdata_callback(sCode, sRealType, data)
    
    def _parse_trade_data(self, stock_code: str, real_data: str) -> Dict:
        # 체결 데이터 파싱
        data = {
            'time': self.get_comm_real_data(stock_code, 20),  # 체결시간
            'current_price': abs(int(self.get_comm_real_data(stock_code, 10))),  # 현재가
            'volume': int(self.get_comm_real_data(stock_code, 15)),  # 거래량
            'high_price': abs(int(self.get_comm_real_data(stock_code, 17))),  # 고가
            'low_price': abs(int(self.get_comm_real_data(stock_code, 18))),  # 저가
        }
        return data

class SimpleTRManager:
    # TR 요청 60초 제한 관리 (QTimer 방식)
    
    def __init__(self, kiwoom_client: KiwoomClient):
        self.kiwoom_client = kiwoom_client
        self.last_request_times = {}  # TR별 마지막 요청 시간
        self.pending_requests = {}  # 대기 중인 요청
        self.request_timers = {}  # TR별 타이머
    
    def request_opt10059(self, stock_code: str) -> bool:
        # OPT10059 (투자자별매매상황) TR 요청
        current_time = time.time()
        tr_code = "OPT10059"
        
        # 60초 제한 체크
        if tr_code in self.last_request_times:
            elapsed = current_time - self.last_request_times[tr_code]
            if elapsed < 60:
                # 대기 후 재시도
                delay = int((60 - elapsed) * 1000)
                QTimer.singleShot(delay, lambda: self.request_opt10059(stock_code))
                return False
        
        # TR 요청 실행
        self.kiwoom_client.ocx.dynamicCall(
            "SetInputValue(QString, QString)",
            "종목코드", stock_code
        )
        
        ret = self.kiwoom_client.ocx.dynamicCall(
            "CommRqData(QString, QString, int, QString)",
            f"투자자별매매상황_{stock_code}",
            tr_code,
            0,
            "7000"
        )
        
        if ret == 0:
            self.last_request_times[tr_code] = current_time
            # 60초 후 다시 요청
            QTimer.singleShot(60000, lambda: self.request_opt10059(stock_code))
        
        return ret == 0

class ConnectionMonitor:
    # 연결 상태 모니터링 및 자동 재연결
    
    def __init__(self, kiwoom_client: KiwoomClient):
        self.kiwoom_client = kiwoom_client
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.check_connection)
        self.last_check_time = time.time()
    
    def start(self):
        # 10초마다 연결 상태 체크
        self.monitor_timer.start(10000)
    
    def check_connection(self):
        # 연결 상태 확인
        if not self.kiwoom_client.connected:
            # 재연결 시도
            self.kiwoom_client.connect()
            
            # 실시간 데이터 재등록
            if self.kiwoom_client.connected:
                stocks = list(self.kiwoom_client.registered_stocks)
                self.kiwoom_client.register_realdata(stocks)

### ========== data_processor.py 핵심 코드 ==========

데이터 처리 및 33개 지표 계산 엔진
CLAUDE.md 기반 - 틱 기반 업데이트, 종목별 독립 상태 유지

import numpy as np
from collections import deque, defaultdict
from typing import Dict, List, Optional

class IndicatorCalculator:
    # 33개 지표 계산 클래스 - 틱 기반 실시간 업데이트
    
    def __init__(self, stock_code: str, kiwoom_client=None):
        self.stock_code = stock_code
        self.kiwoom_client = kiwoom_client
        
        # 틱 데이터 버퍼 (deque with maxlen)
        self.price_buffer = deque(maxlen=200)
        self.volume_buffer = deque(maxlen=200)
        self.time_buffer = deque(maxlen=200)
        
        # 고가/저가 버퍼 (Stochastic 계산용)
        self.high_buffer = deque(maxlen=200)
        self.low_buffer = deque(maxlen=200)
        
        # 호가 데이터 버퍼
        self.bid_ask_buffer = deque(maxlen=100)
        
        # 지표 계산용 상태 변수
        self.prev_price = 0
        self.prev_volume = 0
        self.prev_obv = 0
        self.rsi_gains = deque(maxlen=14)
        self.rsi_losses = deque(maxlen=14)
        
        # 수급 데이터 (TR 기반)
        self.investor_net_data = {}
        self.prev_investor_net = {}
        
        # 기타 상태
        self.prev_day_high = 0
        self.session_start_price = 0
        self.last_update_time = 0
    
    def update_tick_data(self, tick_data: Dict) -> Dict:
        # 틱 데이터 업데이트 및 33개 지표 계산
        
        current_time = int(tick_data.get('time', int(time.time() * 1000)))
        current_price = float(tick_data.get('current_price', 0))
        current_volume = int(tick_data.get('volume', 0))
        
        if current_price <= 0:
            return {}
        
        # 고가/저가 추출
        current_high = float(tick_data.get('high_price', current_price))
        current_low = float(tick_data.get('low_price', current_price))
        
        # 버퍼 업데이트
        self.price_buffer.append(current_price)
        self.volume_buffer.append(current_volume)
        self.time_buffer.append(current_time)
        self.high_buffer.append(current_high)
        self.low_buffer.append(current_low)
        
        # 33개 지표 계산
        indicators = self._calculate_all_indicators(tick_data)
        
        return indicators
    
    def _calculate_all_indicators(self, tick_data: Dict) -> Dict:
        # 33개 지표 전체 계산
        result = {
            # 기본 데이터 (4개)
            'time': tick_data.get('time'),
            'stock_code': self.stock_code,
            'current_price': tick_data.get('current_price'),
            'volume': tick_data.get('volume'),
            
            # 가격 지표 (5개)
            'ma5': self._calculate_ma(5),
            'rsi14': self._calculate_rsi(14),
            'disparity': self._calculate_disparity(),
            'stoch_k': self._calculate_stochastic_k(14),
            'stoch_d': self._calculate_stochastic_d(14, 3),
            
            # 볼륨 지표 (3개)
            'vol_ratio': self._calculate_volume_ratio(),
            'z_vol': self._calculate_z_score_volume(),
            'obv_delta': self._calculate_obv_delta(),
            
            # 호가 지표 (2개)
            'spread': self._calculate_spread(tick_data),
            'bid_ask_imbalance': self._calculate_bid_ask_imbalance(tick_data),
            
            # 기타 지표 (2개)
            'accel_delta': self._calculate_acceleration_delta(),
            'ret_1s': self._calculate_return_1s(),
        }
        
        # 호가 데이터 추가 (16개)
        for i in range(1, 6):
            result[f'ask{i}'] = tick_data.get(f'ask{i}', 0)
            result[f'bid{i}'] = tick_data.get(f'bid{i}', 0)
            if i <= 3:
                result[f'ask{i}_qty'] = tick_data.get(f'ask{i}_qty', 0)
                result[f'bid{i}_qty'] = tick_data.get(f'bid{i}_qty', 0)
        
        # 수급 지표 추가 (11개)
        if self.investor_net_data:
            result.update(self.investor_net_data)
        
        return result
    
    def _calculate_ma(self, period: int) -> float:
        # 이동평균 계산
        if len(self.price_buffer) < period:
            if len(self.price_buffer) > 0:
                return sum(self.price_buffer) / len(self.price_buffer)
            return 0
        return sum(list(self.price_buffer)[-period:]) / period
    
    def _calculate_rsi(self, period: int = 14) -> float:
        # RSI 계산 (Relative Strength Index)
        if len(self.price_buffer) < 2:
            return 50.0
        
        # 가격 변화 계산
        if self.prev_price > 0:
            change = self.price_buffer[-1] - self.prev_price
            if change > 0:
                self.rsi_gains.append(change)
                self.rsi_losses.append(0)
            else:
                self.rsi_gains.append(0)
                self.rsi_losses.append(abs(change))
        
        self.prev_price = self.price_buffer[-1]
        
        if len(self.rsi_gains) < period:
            return 50.0
        
        avg_gain = sum(self.rsi_gains) / len(self.rsi_gains)
        avg_loss = sum(self.rsi_losses) / len(self.rsi_losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

class DataProcessor:
    # 실시간 데이터 처리 메인 클래스
    
    def __init__(self, target_stocks: list, kiwoom_client):
        self.target_stocks = target_stocks
        self.kiwoom_client = kiwoom_client
        
        # 종목별 계산기
        self.calculators = {}
        for stock_code in target_stocks:
            self.calculators[stock_code] = IndicatorCalculator(stock_code, kiwoom_client)
        
        # 콜백
        self.indicator_callback = None
    
    def process_tick_data(self, stock_code: str, tick_data: Dict):
        # 틱 데이터 처리 - 체결 이벤트
        if stock_code not in self.calculators:
            return
        
        # 지표 계산
        indicators = self.calculators[stock_code].update_tick_data(tick_data)
        
        # 콜백 실행
        if indicators and self.indicator_callback:
            self.indicator_callback(stock_code, indicators)
    
    def update_hoga_data(self, stock_code: str, hoga_data: Dict):
        # 호가 데이터 업데이트 - 메모리만 갱신
        if stock_code not in self.calculators:
            return
        
        # 호가 버퍼 업데이트 (CSV 저장하지 않음)
        self.calculators[stock_code].bid_ask_buffer.append(hoga_data)

class InvestorNetManager:
    # 11개 수급 지표 관리 (OPT10059 TR 기반)
    
    def __init__(self, target_stocks: list):
        self.target_stocks = target_stocks
        
        # 종목별 수급 데이터
        self.investor_data = defaultdict(dict)
        self.prev_investor_data = defaultdict(dict)
        
        # 투자자 구분
        self.investor_types = [
            '개인', '외인', '기관', '연기금', '투신',
            '보험', '사모펀드', '은행', '국가', '기타법인', '프로그램'
        ]
    
    def update_investor_data(self, stock_code: str, tr_data: Dict):
        # TR 데이터로부터 수급 지표 업데이트
        
        # 이전 데이터 저장
        if stock_code in self.investor_data:
            self.prev_investor_data[stock_code] = self.investor_data[stock_code].copy()
        
        # 새 데이터 파싱
        new_data = {}
        total_net = 0
        
        for investor_type in self.investor_types:
            value = tr_data.get(investor_type, 0)
            new_data[investor_type] = value
            total_net += value
        
        new_data['total_investor_net'] = total_net
        
        # 데이터 업데이트
        self.investor_data[stock_code] = new_data
        
        return new_data

### ========== csv_writer.py 핵심 코드 ==========

CSV 파일 저장 관리
CLAUDE.md 기반 - 배치 저장, 44개 컬럼

import csv
import os
from datetime import datetime
from collections import defaultdict

class BatchCSVWriter:
    # 배치 방식 CSV 저장 클래스
    
    def __init__(self, base_dir: str = "pure_websocket_data", batch_size: int = 100):
        self.base_dir = base_dir
        self.batch_size = batch_size
        
        # 종목별 버퍼
        self.buffers = defaultdict(list)
        
        # 파일 경로 관리
        self.file_paths = {}
        self.csv_writers = {}
        
        # 디렉토리 생성
        os.makedirs(base_dir, exist_ok=True)
        
        # 44개 컬럼 정의
        self.columns = [
            # 기본 데이터 (4개)
            'time', 'stock_code', 'current_price', 'volume',
            
            # 가격 지표 (5개)
            'ma5', 'rsi14', 'disparity', 'stoch_k', 'stoch_d',
            
            # 볼륨 지표 (3개)
            'vol_ratio', 'z_vol', 'obv_delta',
            
            # Bid/Ask 지표 (2개)
            'spread', 'bid_ask_imbalance',
            
            # 기타 지표 (2개)
            'accel_delta', 'ret_1s',
            
            # 호가 가격 (10개)
            'ask1', 'ask2', 'ask3', 'ask4', 'ask5',
            'bid1', 'bid2', 'bid3', 'bid4', 'bid5',
            
            # 호가 잔량 (6개)
            'ask1_qty', 'ask2_qty', 'ask3_qty',
            'bid1_qty', 'bid2_qty', 'bid3_qty',
            
            # 수급 지표 (11개)
            '개인', '외인', '기관', '연기금', '투신',
            '보험', '사모펀드', '은행', '국가', '기타법인', '프로그램',
            
            # 수급 총합 (1개)
            'total_investor_net'
        ]
    
    def write_indicators(self, stock_code: str, indicators: Dict):
        # 지표 데이터를 버퍼에 추가
        self.buffers[stock_code].append(indicators)
        
        # 배치 크기 도달 시 파일 저장
        if len(self.buffers[stock_code]) >= self.batch_size:
            self._flush_buffer(stock_code)
    
    def _flush_buffer(self, stock_code: str):
        # 버퍼 데이터를 CSV 파일로 저장
        if not self.buffers[stock_code]:
            return
        
        # 파일 경로 생성
        if stock_code not in self.file_paths:
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"{stock_code}_44indicators_realtime_{date_str}.csv"
            self.file_paths[stock_code] = os.path.join(self.base_dir, filename)
            
            # 헤더 작성
            file_exists = os.path.exists(self.file_paths[stock_code])
            if not file_exists:
                with open(self.file_paths[stock_code], 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.columns)
                    writer.writeheader()
        
        # 데이터 추가
        with open(self.file_paths[stock_code], 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            for row in self.buffers[stock_code]:
                writer.writerow(row)
        
        # 버퍼 초기화
        self.buffers[stock_code].clear()
    
    def flush_all(self):
        # 모든 버퍼 저장
        for stock_code in list(self.buffers.keys()):
            self._flush_buffer(stock_code)

---

**업데이트**: 2025-08-31 Python 코드를 순수 텍스트 형식으로 변환
**목적**: Grok AI가 코드 블록을 파싱하지 못하는 문제 해결
**상태**: 텍스트 형식 코드 제공 완료