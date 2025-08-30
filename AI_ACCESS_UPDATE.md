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
**업데이트**: 2025-08-30 Grok 접근 복원용
**상태**: 프로덕션 레디 (실전 서버 테스트 완료)