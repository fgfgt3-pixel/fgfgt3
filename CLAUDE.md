# CLAUDE.md - 키움 Open API 실시간 데이터 수집 시스템 개발 지침
이 문서는 Claude AI(특히 VS Code Claude Code)가 키움 Open API 기반 실시간 데이터 수집 프로젝트를 작업할 때 따를 지침서입니다. 모든 응답과 코드 생성은 이 문서를 기반으로 수행하세요. 위반 시 "CLAUDE.md 위반"을 알리고 작업을 중단하세요. 이 파일은 프로젝트의 핵심 규칙을 정의하며, 코드 작성 시 절대 기준입니다. 이 프로젝트는 zero base에서 시작하므로, 이전 작업 메모리 없이 이 가이드만 따르세요. 매 응답에서 프로젝트 목적(틱 기반 데이터 취합, 36개 지표 계산, CSV 저장)을 재확인하세요. 절대 지켜야 하는 규정에 대한 변경이 필요한 경우 변경 내용, 목적과 함께 사용자 승인을 받을 것. 

## 1. 프로젝트 배경 및 목적
- **목적**: 키움 Open API+(실전 서버)를 사용하여 사용자가 지정한 종목(초기 1개, 점진적 증가로 1~20개 테스트)의 실시간 데이터를 틱 발생 시 이벤트 단위로 취합. 36개 지표를 계산하여 CSV로 저장, 급등주 매매 프로그램 개발을 위한 데이터 분석 기반 마련. 인터넷 과거 데이터 확보 어려움 보완.- **사용 API**: Open API+만 사용할 것, 다른 Open API, REST 등은 일체 사용 불가. 에러 및 변경/추가 필요 시 변경 필요에 대한 내용과 함께 사용자 승인 받을 것.
- **주요 기능**: 틱 이벤트 기반 취합, 36개 지표(수급 지표는 11개 컬럼 확장 저장으로 총 44개 CSV컬럼) 계산, CSV 저장.
- **개발 환경**: Python 중심 (32비트 Python 3.8 권장, pykiwoom wrapper 사용), VS Code Claude Code로 작업. Windows 환경 필수 (키움 Open API+ 의존). 세부 설명 필요 – Claude가 내용을 모르는 상태이므로, 매 응답에서 프로젝트 목적(틱 기반 취합, 36개 지표(수급 지표는 11개 컬럼 확장 저장으로 총 44개 CSV컬럼), CSV 저장)을 재확인.

## 2. 기능 요구사항
### 2.1 실시간 데이터 수집
- 키움 Open API에 연결하여 실시간 주가/호가 데이터 수신.
- 틱 발생 시 이벤트(OnReceiveRealData)로 데이터 포인트 생성.
- 주가 체결 데이터와 호가 데이터 동시 등록 (SetRealReg 사용).
### 2.2 데이터 처리
- 수신 이벤트 데이터 파싱 (FID 기반 추출 지원).
- rolling window(deque)로 가격/거래량 히스토리 관리.
- 36개 지표 실시간 계산 – 종목별 독립 상태 유지.
### 2.3 CSV 저장
- 종목별 개별 CSV 파일 생성.
- 틱마다 36개 지표를 한 행으로 저장 (틱 기반 전환), (수급 지표는 11개 컬럼 확장 저장으로 총 44개 CSV컬럼).
- 파일명: {stock_code}_44indicators_realtime_{YYYYMMDD}.csv.
- 경로: pure_websocket_data/ (자동 생성, 상대 경로).

## 3. 기술 사양
### 3.1 config.py (설정 관리)
- 로그인 정보: ID, PW, CERT 등 환경 변수나 별도 파일로 관리 (깃 업로드 금지).
- 종목 코드 중앙 관리: config.py 최상단 TARGET_STOCKS 리스트 – 사용자 자유 수정 (초기 1개, 점진 증가 테스트, 최대 20개). 다른 모듈에서 이 리스트 참조.
- Open API 설정: SCREEN_NO = "0101" (기본 화면 번호), ACCOUNT_NO = "계좌번호".
- 데이터 설정: MAX_TICK_BUFFER = 1000 (틱 버퍼 크기), CSV_DIR = "pure_websocket_data".
### 3.2 Open API 연결 정보
- 로그인: CommConnect 사용, 자동 재로그인 로직 포함 (연결 끊김 시 최대 5회 재시도).
- 실시간 등록: SetRealReg, 화면당 최대 100종목 (여러 화면 번호 사용으로 확장).
- 재연결: 연결 끊김 시 CommTerminate 후 재로그인/재등록 (최대 5회), 등록 재시도 3회.
- TR 요청 제한 대응: 초당 1회/분당 60회, 큐잉 로직 필수 (queue 사용, 대기열 관리). 동일 TR은 1분 1회 까지만 가능(동일 조건 1분 1회). 1분 1회 넘어서는 TR 설계하지 않도록 필수 확인.
### 3.3 이벤트 데이터 형식
- 등록 요청: SetRealReg(화면번호, 종목코드 리스트, FID 리스트, "1" for 실시간).
- 실시간 데이터: OnReceiveRealData 이벤트, GetCommRealData(종목코드, FID)로 추출 (e.g., FID=10 현재가, FID=13 누적거래량).
### 3.4 36개 지표 정의 (time은 밀리초 단위로 정의)
-36개 지표 (수급 지표는 11개 컬럼 확장 저장으로 총 44개 CSV컬럼)
- 기본 데이터 (4개): time, stock_code, current_price, volume.
- 가격 지표 (5개): ma5, rsi14, disparity, stoch_k, stoch_d.
- 볼륨 지표 (3개): vol_ratio, z_vol, obv_delta.
- Bid/Ask 지표 (2개): spread, bid_ask_imbalance.
- 기타 지표 (2개): accel_delta, ret_1s.
- 호가 가격 (10개): ask1~ask5, bid1~bid5.
- 호가 잔량 (10개): ask1_qty~ask5_qty, bid1_qty~bid5_qty.
- 수급 통합 지표 (OPT10059 TR 코드): investor_net_vol dict (주체: 개인, 외인, 기관, 연기금, 투신, 보험, 사모펀드, 은행, 국가, 기타법인, 프로그램 등 net_vol = buy - sell; CSV에 json.dumps or 별도 열 저장, Sum으로 총 net 계산).
-수급 통합 지표(TR필요) 외 지표는 틱 기반 업데이트를 원칙으로 한다. (일부 틱 기반 업데이트가 필요 없는 지표는 예외)

## 4. 프로젝트 구조
```
kiwoom_openapi_collector/
├── config.py # 설정/종목 코드 중앙 관리
├── kiwoom_client.py # 로그인/연결/이벤트 핸들러
├── data_processor.py # FID 파싱/지표 계산
├── csv_writer.py # CSV 저장
├── main.py # 메인 실행
└── pure_websocket_data/ # CSV 폴더
```

## 5. 구현 상세
### 5.1 config.py
- TARGET_STOCKS 리스트로 종목 중앙 관리 – 다른 모듈에서 import.
- 로그인/계좌 정보 관리.
### 5.2 kiwoom_client.py
- 로그인/연결 수립/유지 (CommConnect, 자동 재로그인 로직: 연결 끊김 감지 시 재시도).
- 종목 등록 (SetRealReg), 이벤트 핸들러(OnReceiveRealData) 전달.
- 연결 끊김 시 자동 재연결/재로그인/재등록.
- TR 요청 큐잉: from queue import Queue; tr_queue = Queue(); 초당 1회 처리 로직 (e.g., async loop에서 queue.get() 후 CommRqData 호출, 초과 시 대기).
### 5.3 data_processor.py
- 이벤트 데이터 파싱 (GetCommRealData FID 기반).
- deque로 히스토리 관리.
- 지표 계산 함수 구현 – 종목별 상태 유지 (틱 기반 업데이트).
### 5.4 csv_writer.py
- 종목별 CSV 생성/관리.
- 헤더 작성, 틱마다 행 추가.
- I/O 에러 처리.
### 5.5 main.py
- 시스템 초기화/실행 (로그인/등록).
- 이벤트 루프로 데이터 수집.
- Ctrl+C 안전 종료 (CommTerminate 호출).
## 6. 지표 계산 로직 예시
- ma5: sum(price_history[-5:]) / 5.
- rsi14: 상승/하락 평균 계산 (14틱).
- spread: ask1 - bid1 (FID 27 - FID 32).
- bid_ask_imbalance: (sum(bid_qty) - sum(ask_qty)) / total (FID 51~55 등).
- investor_net_vol: OPT10059 TR GetCommData로 dict 추출 (e.g., 'inst': GetCommData("기관"), net_vol = buy - sell; delta = current - prev).

## 7. 주의사항
- 로그인 정보 보안: 환경 변수 관리.
- 틱 기반 처리: 이벤트 핸들러에서 즉시 업데이트.
- 메모리 관리: deque maxlen 설정, TR 큐 크기 제한.
- 에러 처리: 네트워크/연결 오류 시 재로그인, TR 초과 큐잉.
- CSV 무결성: 쓰기 오류 시 데이터 손실 방지.
- Windows/32비트 환경: Python 3.8 32비트 필수.
- 자동 로그인: kiwoom_client.py에 연결 상태 모니터링, 끊김 시 CommConnect 재호출.

## 8. 테스트 방법
- 단일 종목: TARGET_STOCKS = ['005930'].
- 다중 종목: 1개 → 20개 점진 증가.
- 대량 종목: 20개 이상으로 안정성 테스트 (틱 부하 시뮬).

## 9. 개발 순서
1. config.py 작성 – 설정/종목 정의.
2. kiwoom_client.py – 로그인/연결/이벤트 구현.
3. data_processor.py – FID 파싱/계산 구현.
4. csv_writer.py – 저장 구현.
5. main.py – 통합 실행.

## 10. 코드 작성 참고
-키움 Open API+는 공식 제공 문서 및 예제 코드가 매우 제한적이므로, GitHub에 공개된 pykiwoom 및 키움 관련 예제 코드를 참고할 수 있다.
-단, 공개 소스는 참고만 가능하며, 본 프로젝트 코드에는 직접 복사하지 않고 재구현한다.
-참고 시, “참고한 오픈소스 출처”를 주석에 반드시 명시한다.
-참고 가능한 예:
pykiwoom GitHub
키움증권 OpenAPI 공식 샘플 (설치 경로 예제코드)

## 11. 로그 관리 (기술적으로 가능한 경우 아래와 같이 로그 관리 진행)
-개발된 Python 코드에서 logging 모듈로 로그 기록을 남겨야 한다
-레벨: INFO(일반 이벤트), WARNING(재로그인 시도), ERROR(연결 실패).
-로그는 logs/ 디렉토리에 날짜별 파일로 저장한다.

## 12. 수급 통합 지표 (OPT10059 TR) 코딩 시 참조 사항 (GitHub에 공개된 더 좋은 코드가 있다면 해당 코드 사용 가능)
OPT10059 TR 코드 주체(연기금, 투신, 보험, 사모펀드, 은행, 국가, 기타 등)를 포함 (tool: web_search [0] 키움 Open API 문서/ [1] devguide PDF – OPT10059 필드: 개인, 외인, 기관, 연기금, 투신, 보험, 은행, 사모펀드, 국가, 기타법인 등 buy/sell/net vol 제공).
* 하나의 TR(OPT10059)로 모든 주체 총합을 취득 가능 – net_vol = buy - sell 계산.
* dict를 확장해 "주요 + 기타" 주체 모두 포함 – CSV에 열 나눠 저장/Sum. ( e.g., investor_net_vol dict로 저장, CSV에 json.dumps or 별도 열: inst_net, pension_net, etc.)
* 30초 1회 호출로 오버 방지, delta (현재 - 이전)로 변화 파악 – 급등 초기 주체( e.g., 연기금 spike) 포착 강화.
업데이트된 코드 예시 (Python, Kiwoom class 가정)
python
# 키움 Open API에서 OPT10059 TR 호출
kiwoom.SetInputValue("종목코드", stock_code)
kiwoom.SetInputValue("기준일자", "20240818") # 당일
kiwoom.SetInputValue("수정주가구분", "1") # 수정주가 반영
kiwoom.CommRqData("OPT10059", "OPT10059", 0, "0101")
# OnReceiveTrData 이벤트 핸들러
def OnReceiveTrData(self, scr_no, rq_name, tr_code, record_name, inquiry):
if tr_code == "OPT10059":
        investor_net = {}
        investor_net['indiv'] = self.GetCommData(tr_code, rq_name, 0, "개인") # 개인 net vol
        investor_net['foreign'] = self.GetCommData(tr_code, rq_name, 0, "외인") # 외인 net vol
        investor_net['inst'] = self.GetCommData(tr_code, rq_name, 0, "기관") # 기관 net vol
        investor_net['pension'] = self.GetCommData(tr_code, rq_name, 0, "연기금") # 연기금 net vol
        investor_net['trust'] = self.GetCommData(tr_code, rq_name, 0, "투신") # 투신 net vol
        investor_net['insurance'] = self.GetCommData(tr_code, rq_name, 0, "보험") # 보험 net vol
        investor_net['private_fund'] = self.GetCommData(tr_code, rq_name, 0, "사모펀드") # 사모펀드 net vol
        investor_net['bank'] = self.GetCommData(tr_code, rq_name, 0, "은행") # 은행 net vol
        investor_net['state'] = self.GetCommData(tr_code, rq_name, 0, "국가") # 국가 net vol
        investor_net['other'] = self.GetCommData(tr_code, rq_name, 0, "기타법인") # 기타법인 net vol
        investor_net['prog'] = self.GetCommData(tr_code, rq_name, 0, "프로그램") # 프로그램 net vol (OPT10034 보완 가능)
# CSV 저장 예: dict to columns or json
# e.g., df['investor_net_vol'] = json.dumps(investor_net)
# or separate cols: df['inst_net_vol'] = investor_net['inst']
* CSV 저장 팁: dict 전체 json.dumps로 한 열 저장 – or 11개 열 나눠 (inst_net_vol, foreign_net_vol, ... other_net_vol). Sum으로 총 net 계산 ( e.g., total_net = sum(investor_net.values())) – 패턴 분석 용이.
* delta 계산 (변화 파악): prev_net 저장 후 delta = current_net - prev_net – 30초 변화율로 spike 감지.
TR 요청 관리 전략 (다중 종목 시 요청 관리 전략_아래는 20개 기준이며 종목 개수 적용에 따라 개수 관련 내용은 상이)
* 초기 로드: 20종목 x OPT10059 = 20TR, 초당 5회 제한 → 4초 분산 요청 (asyncio.sleep(0.2)로 안전).
  * 코드 예시:
    python
    import asyncio
    from collections import defaultdict
    class Kiwoom:
    async def request_tr(self, stock_code, tr_code):
            self.SetInputValue("종목코드", stock_code)
            self.SetInputValue("기준일자", "20250826")
            self.SetInputValue("수정주가구분", "1")
            self.CommRqData("OPT10059", tr_code, 0, f"0101_{stock_code}")
    await asyncio.sleep(0.2) # 초당 5회 제한
    # ... GetCommData for investor_net_vol dict
    return {'inst': 1000, 'foreign': 500, ...}
    async def init_load(kiwoom, stocks):
        sem = asyncio.Semaphore(5) # 초당 5TR
    async def load_stock(code):
    async with sem:
    return await kiwoom.request_tr(code, 'OPT10059')
        results = await asyncio.gather(*[load_stock(code) for code in stocks])
    return dict(zip(stocks, results)) # {code: dict}
* 업데이트: 60초마다 20TR (20종목) – 분당 제한 OK. 각 종목 60초 1회로 동일 조건 충족.
* 대안 (최적화): 급등주 포착 우선순위 큐 – 모멘텀 높은 종목( e.g., volume spike) 먼저 TR (PriorityQueue로 관리).
내용 정리
* 1분 1회 제한: OPT10059는 동일 종목/조건으로 60초 1회만 가능 – 20/30초 업데이트 불가, 60초로 조정.
* 20종목 = 20TR: 각 종목별 OPT10059 호출 필요 – 1TR로 20종목 불가.
* 관리 가능: 초기 20TR(4초), 60초마다 20TR – 초당/분당 제한 OK (asyncio로 관리).
위 'TR 요청 관리 전략 '을 20개로 지정하였는데, 최종 설계 가이드시에는 1개~20개 까지 다중으로 넣을 수 있도록 유연하게 작성 진행 필요


 