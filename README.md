# 키움 OpenAPI+ 실시간 데이터 수집 시스템

## 🤖 AI 접근 가이드
**AI가 이 프로젝트를 이해하려면 → [AI_ACCESS_UPDATE.md](./AI_ACCESS_UPDATE.md) 파일을 먼저 읽어주세요**

> **목적**: 키움 Open API+를 사용한 실시간 주식 데이터 수집 및 36개 지표 계산 시스템

## 📁 프로젝트 구조

### 핵심 파일들
- **`CLAUDE.md`** - 프로젝트 설계 및 개발 지침 (가장 중요!)
- **`main.py`** - 메인 실행 파일
- **`config.py`** - 설정 관리 (종목, API 설정)
- **`kiwoom_client.py`** - 키움 API 클라이언트
- **`data_processor.py`** - 36개 지표 계산 엔진
- **`csv_writer.py`** - CSV 파일 저장 모듈
- **`run.py`** - 통합 실행 스크립트

### 실행 방법
```bash
# 32비트 Python 3.8 필요
C:\python38_32bit\python.exe run.py
```

## 🎯 주요 기능
- **실시간 틱 데이터 수집**: 키움 OpenAPI+ 기반
- **36개 지표 계산**: 수급지표 11개 확장으로 총 44개 CSV 컬럼
- **CSV 자동 저장**: `pure_websocket_data/{종목}_44indicators_realtime_{날짜}.csv`
- **자동 재연결**: 연결 끊김시 자동 복구

## 📊 지표 목록
- 기본 데이터 (4개): time, stock_code, current_price, volume
- 가격 지표 (5개): ma5, rsi14, disparity, stoch_k, stoch_d  
- 볼륨 지표 (3개): vol_ratio, z_vol, obv_delta
- 호가 지표 (2개): spread, bid_ask_imbalance
- 호가 가격 (10개): ask1~5, bid1~5
- 호가 잔량 (10개): ask1_qty~5_qty, bid1_qty~5_qty
- 수급 지표 (11개): 개인, 외인, 기관, 연기금, 투신, 보험, 사모펀드, 은행, 국가, 기타법인, 프로그램

## 🔧 환경 설정
- **OS**: Windows (키움 API 의존)
- **Python**: 32비트 Python 3.8 권장
- **API**: 키움 Open API+ (실전 서버)

## 🔍 최근 업데이트 (2025-08-27)
### CSV 파일 생성 문제 진단 완료
- **결론**: CSV 생성 코드는 정상 작동 ✅
- **실제 원인**: Kiwoom API 연결 또는 실시간 데이터 수신 문제
- **추가된 도구**:
  - `test_csv_writer.py` - CSV Writer 독립 테스트
  - `test_data_flow.py` - 전체 파이프라인 테스트 
  - `test_connection.py` - Kiwoom API 연결 테스트
  - 디버깅 로그 강화 (main.py, data_processor.py, csv_writer.py)

### 진단 단계
1. `simple_csv_test.py` 실행 → CSV 기능 확인
2. `test_data_flow.py` 실행 → 전체 파이프라인 확인
3. `test_connection.py` 실행 → API 연결 상태 확인

## 📝 개발 지침
모든 코드 수정은 `CLAUDE.md` 파일의 지침을 따라야 합니다.

---
🤖 Generated with Claude Code