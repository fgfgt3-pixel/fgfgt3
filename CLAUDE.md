# CLAUDE.md - 키움 Open API 실시간 데이터 수집 시스템 개발 지침

이 문서는 Claude AI(특히 VS Code Claude Code)가 키움 Open API 기반 실시간 데이터 수집 프로젝트를 작업할 때 따를 지침서입니다. 모든 응답과 코드 생성은 이 문서를 기반으로 수행하세요. 위반 시 "CLAUDE.md 위반"을 알리고 작업을 중단하세요. 이 파일은 프로젝트의 핵심 규칙을 정의하며, 코드 작성 시 절대 기준입니다. 이 프로젝트는 zero base에서 시작하므로, 이전 작업 메모리 없이 이 가이드만 따르세요. 매 응답에서 프로젝트 목적(틱 기반 데이터 취합, 36개 지표 계산, '수급 지표'는 11개 컬럼 확장 저장으로 총 44개 CSV컬럼)을 재확인하세요. 절대 지켜야 하는 규정에 대한 변경이 필요한 경우 변경 내용, 목적과 함께 사용자 승인을 받을 것.

## 1. 프로젝트 배경 및 목적 (불변사항)
- **목적**: 키움 Open API+(실전 서버)를 사용하여 사용자가 지정한 종목(초기 1개, 점진적 증가로 1~20개 테스트)의 실시간 데이터를 틱 발생 시 이벤트 단위로 취합. 36개 지표를 계산하여 CSV로 저장, 급등주 매매 프로그램 개발을 위한 데이터 분석 기반 마련. 인터넷 과거 데이터 확보 어려움 보완.
- **사용 API**: Open API+만 사용할 것, 다른 Open API, REST 등은 일체 사용 불가. 에러 및 변경/추가 필요 시 변경 필요에 대한 내용과 함께 사용자 승인 받을 것.
- **주요 기능**: 틱 이벤트 기반 취합, 36개 지표(수급 지표는 11개 컬럼 확장 저장으로 총 44개 CSV컬럼) 계산, CSV 저장.
- **틱 정의**: 틱 = 체결 발생 시점 (가격/거래량 변동이 있을 때만). 호가 변경은 별도 이벤트로 처리하며 CSV 저장하지 않음.
- **개발 환경**: Python 중심 (32비트 Python 3.8 권장, pykiwoom wrapper 사용), VS Code Claude Code로 작업. Windows 환경 필수 (키움 Open API+ 의존).

## 2. 기능 요구사항

### 2.1 실시간 데이터 수집
- 키움 Open API에 연결하여 실시간 주가/호가 데이터 수신
- 틱 발생 시 이벤트(OnReceiveRealData)로 데이터 포인트 생성 
- 주가 체결 데이터와 호가 데이터 동시 등록 (SetRealReg 사용)
- sRealType별 처리 분기 필수 ("주식체결", "주식호가잔량", "주식시세")

### 2.2 데이터 처리 
- 수신 이벤트 데이터 파싱 (FID 기반 추출 지원)
- rolling window(deque)로 가격/거래량 히스토리 관리
- 36개 지표 실시간 계산 – 종목별 독립 상태 유지
- 데이터 무결성 체크 및 이상치 필터링

### 2.3 CSV 저장 
- 종목별 개별 CSV 파일 생성
- 체결 이벤트 시에만 CSV 저장 (호가 업데이트는 메모리만 갱신) (불변사항)
- 배치 저장 방식 (100틱마다) 적용으로 I/O 최적화
- 파일명: {stock_code}_36indicators_realtime_{YYYYMMDD}.csv
- 경로: pure_websocket_data/ (자동 생성, 상대 경로)

## 3. 기술 사양

### 3.1 config.py (설정 관리)
config.py는 클래스 기반 구조(KiwoomConfig, DataConfig, OptimizedFID 등)로 구현되어 있으며, TARGET_STOCKS, FID 매핑, CSV 설정 등을 중앙 관리합니다. 실제 구현은 해당 파일을 참조하세요.

### 3.2 Open API 연결 및 실시간 등록

#### 실시간 데이터 등록
KiwoomClient.register_realdata() 메서드가 구현되어 있으며, OptimizedFID 클래스의 FID 설정을 사용합니다.

#### 연결 상태 모니터링
ConnectionMonitor 클래스가 구현되어 있으며, 10초마다 연결 상태를 체크하고 자동 재연결/재등록을 처리합니다.

### 3.3 이벤트 핸들러

#### 실시간 데이터 처리
KiwoomClient.on_receive_real_data() 메서드가 실시간 데이터를 수신하고, DataProcessor에서 sRealType별 분기 처리 및 지표 계산을 수행합니다.

### 3.4 36개 지표 정의 ('수급 지표'는 11개 컬럼 확장 저장으로 총 44개 CSV컬럼)
- 기본 데이터 (4개): time, stock_code, current_price, volume
- 가격 지표 (5개): ma5, rsi14, disparity, stoch_k, stoch_d
- 볼륨 지표 (3개): vol_ratio, z_vol, obv_delta
- Bid/Ask 지표 (2개): spread, bid_ask_imbalance
- 기타 지표 (2개): accel_delta, ret_1s
- 호가 가격 (10개): ask1~ask5, bid1~bid5
- 호가 잔량 (6개): ask1_qty~ask3_qty, bid1_qty~bid3_qty
- 수급 통합 지표: 개인, 외인, 기관, 연기금, 투신, 보험, 사모펀드, 은행, 국가, 기타법인, 프로그램 (11개 개별 컬럼)
- 수급 총합 (1개): total_investor_net

## 4. 수급 통합 지표 (OPT10059) 관리

### 4.1 InvestorNetManager 클래스
data_processor.py에 구현되어 있으며, 11개 수급 지표의 현재값/이전값 관리, TR 응답 데이터 파싱, Delta 계산을 담당합니다.

### 4.2 TR 요청 제한 관리
SimpleTRManager 클래스가 kiwoom_client.py에 구현되어 있으며, 60초 TR 제한, QTimer 기반 스케줄링, 에러 시 타이머 체인 유지 기능을 제공합니다.

## 5. 구현된 주요 클래스들

### 5.1 메인 애플리케이션
- **KiwoomDataCollector** (main.py): 전체 시스템 통합 관리, 모든 모듈 초기화 및 콜백 연결

### 5.2 키움 API 클라이언트
- **KiwoomClient** (kiwoom_client.py): 키움 OpenAPI+ OCX 컨트롤 관리, 실시간 데이터 등록/수신
- **SimpleTRManager** (kiwoom_client.py): TR 요청 60초 제한 관리, QTimer 방식
- **ConnectionMonitor** (kiwoom_client.py): 연결 상태 모니터링 및 자동 재연결

### 5.3 데이터 처리
- **IndicatorCalculator** (data_processor.py): 36개 지표 실시간 계산
- **DataProcessor** (data_processor.py): 실시간 데이터 파싱 및 지표 통합
- **InvestorNetManager** (data_processor.py): 11개 수급 지표 관리

### 5.4 CSV 저장
- **BatchCSVWriter** (csv_writer.py): 설정 가능한 배치 저장, 44개 컬럼 CSV 파일 생성

### 5.5 보안 및 유틸리티
- **SecureLoginHelper** (secure_helper.py): 암호화된 자동 로그인 관리

## 6. 주요 설정 및 제한사항

### 6.1 기술적 제한사항 (불변)
- **32비트 Python 3.8** 환경 필수 (키움 OpenAPI+ 의존)
- **Windows 환경** 필수
- **QTimer 사용** (PyQt5 이벤트 루프 호환, async 금지)
- **TR 제한**: 동일 TR 60초 1회 제한

### 6.2 데이터 처리 원칙 (불변)
- **틱 정의**: 체결 발생 시점만 (가격/거래량 변동시)
- **CSV 저장**: 체결 이벤트만 저장, 호가는 메모리만 업데이트
- **종목별 독립**: 각 종목별 독립적 상태 관리
- **배치 저장**: I/O 최적화를 위한 배치 저장 방식

### 6.3 보안 관리
- **자동 로그인**: 암호화된 인증 정보 관리
- **메모리 보안**: 사용 후 즉시 삭제
- **환경 변수**: 민감 정보는 환경 변수 활용

## 7. 개발 및 운영 가이드라인

### 7.1 코드 작성 원칙
- 기존 파일 우선 활용, 신규 파일 최소화
- 실제 구현된 클래스와 메서드 참조
- GitHub pykiwoom 예제 참고 가능 (직접 복사 금지)
- 출처 주석 명시, 재구현 원칙

### 7.2 테스트 방법
- 단일 종목부터 점진적 증가 (1개 → 20개)
- 실시간 환경에서 실제 데이터 검증
- 로그 파일을 통한 상세 모니터링

### 7.3 로그 관리
- logging 모듈 활용
- INFO(일반), WARNING(재시도), ERROR(실패) 레벨 구분
- logs/ 디렉토리에 날짜별 파일 저장

## 8. 최종 확정 구현 사항

1. **QTimer 기반**: PyQt5 이벤트 루프 호환성
2. **FID 최적화**: 체결/호가 선택적 사용
3. **람다 클로저**: 변수 캐처 시 기본값 지정 필수
4. **TR 관리**: 성공 후에만 시간 기록
5. **객체 관리**: Timer 객체는 클래스 멤버로 관리
6. **실시간 등록**: 첫 종목 "0", 나머지 "1"
7. **CSV 설정**: 배치 크기 1~100 설정 가능

---

**참고**: 모든 상세 구현은 실제 .py 파일들을 참조하세요. 이 문서는 프로젝트의 전략적 방향과 핵심 원칙을 제시하며, 구체적인 코드 구현은 각 파일에서 확인할 수 있습니다.