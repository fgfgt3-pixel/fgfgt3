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
```python
# 종목 코드 중앙 관리
TARGET_STOCKS = ['005930']  # 초기 1개, 최대 20개까지 점진 증가

# Open API 설정
SCREEN_NO_BASE = 1000  # 실시간용 화면번호 시작
TR_SCREEN_NO_BASE = 5000  # TR용 화면번호 시작
ACCOUNT_NO = "계좌번호"

# 데이터 설정
MAX_TICK_BUFFER = 1000
CSV_DIR = "pure_websocket_data"
BATCH_SIZE = 100  # CSV 배치 저장 크기

# TR 제한 설정
TR_LIMIT_PER_SECOND = 4  # 안전하게 4회
TR_LIMIT_PER_MINUTE = 90  # 안전하게 90회
```

### 3.2 Open API 연결 및 실시간 등록

#### 실시간 데이터 등록 (SetRealReg)
```python
def register_real_data(self, stock_codes):
    # 완전한 FID 리스트 (체결, 호가, 잔량 모두 포함)
    fid_list = (
        # 체결 데이터
        "10;11;12;13;14;15;16;17;18;20;25;26;"
        # 매도호가 (41~50)
        "41;42;43;44;45;46;47;48;49;50;"
        # 매수호가 (51~60)
        "51;52;53;54;55;56;57;58;59;60;"
        # 매도잔량 (61~70)
        "61;62;63;64;65;66;67;68;69;70;"
        # 매수잔량 (71~80)
        "71;72;73;74;75;76;77;78;79;80;"
        # 추가 필요 FID
        "27;28;29;30;31;32;33;34;35"
    )
    
    for idx, code in enumerate(stock_codes):
        screen_no = f"{1000 + idx}"  # 종목별 화면번호 분리
        opt_type = "0"  # 신규 등록 (중요: "1"이 아닌 "0")
        
        self.SetRealReg(screen_no, code, fid_list, opt_type)
        time.sleep(0.05)  # 안정성
```

#### 연결 상태 모니터링
```python
class ConnectionMonitor:
    async def monitor_connection(self, kiwoom):
        while True:
            state = kiwoom.GetConnectState()
            
            if state == 0:  # 연결 끊김
                print("연결 끊김 감지! 재연결 시도...")
                kiwoom.CommTerminate()
                await asyncio.sleep(1)
                
                # 재로그인
                if kiwoom.CommConnect() == 0:
                    # 실시간 재등록
                    await self.re_register_all()
                    
            await asyncio.sleep(10)  # 10초마다 체크
```

### 3.3 이벤트 핸들러

#### OnReceiveRealData 구현
```python
def OnReceiveRealData(self, sCode, sRealType, sRealData):
    """실시간 데이터 수신 이벤트"""
    
    # 실시간 타입별 처리 분기 (필수)
    if sRealType == "주식체결":
        # 체결 데이터 처리 - 실제 틱
        current_price = self.parse_real_data(sCode, 10)
        volume = self.parse_real_data(sCode, 15)
        
        # 36개 지표 계산
        tick_data = self.calculate_indicators(sCode, current_price, volume)
        
        # CSV 저장 (체결 시에만)
        self.csv_writer.add_tick(tick_data)
        
    elif sRealType == "주식호가잔량":
        # 호가 데이터 처리 - 메모리만 업데이트
        self.update_orderbook(sCode)
        # CSV 저장하지 않음
        
    elif sRealType == "주식시세":
        # 종합 시세 처리
        pass

def parse_real_data(self, sCode, fid):
    """실시간 데이터 파싱 with 안전 처리"""
    raw_data = self.GetCommRealData(sCode, fid)
    
    # 공백/None 체크
    if not raw_data or raw_data.strip() == "":
        return 0
    
    # 부호 처리 및 타입 변환
    try:
        cleaned = raw_data.strip().replace(",", "")
        value = abs(int(cleaned)) if cleaned else 0
        
        # 이상치 체크
        if fid == 10 and value > 10000000:  # 현재가 천만원 초과시
            logging.warning(f"Abnormal price: {value}")
            
        return value
    except (ValueError, TypeError):
        logging.error(f"Parse error: {raw_data}")
        return 0
```

### 3.4 36개 지표 정의 ('수급 지표'는 11개 컬럼 확장 저장으로 총 44개 CSV컬럼)
- 기본 데이터 (5개): time, stock_code, current_price, volume
- 가격 지표 (5개): ma5, rsi14, disparity, stoch_k, stoch_d
- 볼륨 지표 (3개): vol_ratio, z_vol, obv_delta
- Bid/Ask 지표 (2개): spread, bid_ask_imbalance
- 기타 지표 (2개): accel_delta, ret_1s
- 호가 가격 (10개): ask1~ask5, bid1~bid5
- 호가 잔량 (10개): ask1_qty~ask5_qty, bid1_qty~bid5_qty
- 수급 통합 지표: 개인, 외인, 기관, 연기금, 투신, 보험, 사모펀드, 은행, 국가, 기타법인, 프로그램 (11개 개별 컬럼)

## 4. 수급 통합 지표 (OPT10059) 관리

### 4.1 InvestorNetManager 클래스
```python
class InvestorNetManager:
    """수급 데이터 관리 - 단순하고 명확한 구조"""
    
    def __init__(self, stock_codes):
        self.stock_codes = stock_codes
        
        # 종목별 현재 수급 데이터 (TR에서 받은 최신 누적값)
        self.current_net_vol = defaultdict(lambda: self._get_empty_dict())
        
        # 종목별 이전 수급 데이터 (delta 계산용)
        self.previous_net_vol = defaultdict(lambda: self._get_empty_dict())
        
        # 종목별 마지막 업데이트 정보
        self.last_update_info = defaultdict(lambda: {
            'time': None,
            'round': 0
        })
        
        # TR 스케줄 관리
        self.tr_schedule = PriorityQueue()
        self._initialize_schedule()
        
    def _get_empty_dict(self):
        """빈 수급 딕셔너리 반환"""
        return {
            'individual': 0,      # 개인
            'foreign': 0,         # 외인
            'institution': 0,     # 기관
            'pension': 0,         # 연기금
            'investment': 0,      # 투신
            'insurance': 0,       # 보험
            'private_fund': 0,    # 사모펀드
            'bank': 0,           # 은행
            'state': 0,          # 국가
            'other_corp': 0,     # 기타법인
            'program': 0         # 프로그램
        }
    
    def update_from_tr(self, stock_code, tr_data):
        """TR 응답 처리 - 누적값을 그대로 저장 (대체)"""
        
        # 1. 이전값 백업 (delta 계산용)
        self.previous_net_vol[stock_code] = self.current_net_vol[stock_code].copy()
        
        # 2. 새로운 누적값으로 대체 (키움이 주는 값이 이미 누적값)
        self.current_net_vol[stock_code] = {
            'individual': int(tr_data.get('개인', 0)),
            'foreign': int(tr_data.get('외인', 0)),
            'institution': int(tr_data.get('기관', 0)),
            'pension': int(tr_data.get('연기금', 0)),
            'investment': int(tr_data.get('투신', 0)),
            'insurance': int(tr_data.get('보험', 0)),
            'private_fund': int(tr_data.get('사모펀드', 0)),
            'bank': int(tr_data.get('은행', 0)),
            'state': int(tr_data.get('국가', 0)),
            'other_corp': int(tr_data.get('기타법인', 0)),
            'program': int(tr_data.get('프로그램', 0))
        }
        
        # 3. 다음 TR 스케줄링 (1분 후)
        next_time = time.time() + 60
        next_round = self.last_update_info[stock_code]['round'] + 1
        self.tr_schedule.put((next_time, stock_code, next_round))
```

### 4.2 TR 요청 제한 관리
```python
# TR 요청은 3가지 레벨의 제한을 모두 준수해야 함
# 1. 초당 제한: 모든 TR 합계 4회 (안전 마진, 실제 제한 5회)
# 2. 분당 제한: 모든 TR 합계 90회 (안전 마진, 실제 제한 100-200회)  
# 3. 동일 TR 제한: 같은 TR코드 + 같은 조건 = 60초 1회  (불변사항)

class SafeTRScheduler:
    """모든 TR 요청 제한 통합 관리"""
    
    def __init__(self, kiwoom_client):
        self.kiwoom = kiwoom_client
        
        # 전체 TR 트래픽 관리
        self.request_history = []
        
        # 동일 TR별 마지막 요청 시간
        # 키: (tr_code, 종목코드, 조건) 튜플
        self.last_request_per_tr = {}
    
    async def request_tr(self, tr_code, stock_code, input_dict, round_num=0):
        """범용 TR 요청 (모든 제한 체크)"""
        
        # 1. 동일 TR 60초 제한 체크
        tr_key = (tr_code, stock_code, str(input_dict))
        current_time = time.time()
        
        if tr_key in self.last_request_per_tr:
            elapsed = current_time - self.last_request_per_tr[tr_key]
            if elapsed < 60:
                wait_time = 60 - elapsed
                print(f"{tr_code} {stock_code}: {wait_time:.1f}초 후 재요청 가능")
                await asyncio.sleep(wait_time)
        
        # 2. 초당/분당 제한 체크
        await self._check_traffic_limits()
        
        # 3. TR 요청 실행
        for key, value in input_dict.items():
            self.kiwoom.SetInputValue(key, value)
        
        req_name = f"{tr_code}_{stock_code}_{round_num}"
        self.kiwoom.CommRqData(req_name, tr_code, 0, self._get_screen_no(tr_code))
        
        # 4. 요청 기록
        self.last_request_per_tr[tr_key] = current_time
        self.request_history.append(current_time)
        
    async def request_opt10059(self, stock_code, round_num):
        """OPT10059 특화 메서드 (하위호환성)"""
        input_dict = {
            "종목코드": stock_code,
            "기준일자": datetime.now().strftime("%Y%m%d"),
            "수정주가구분": "1"
        }
        await self.request_tr("OPT10059", stock_code, input_dict, round_num)
    
    async def _check_traffic_limits(self):
        """초당/분당 트래픽 제한 체크"""
        current_time = time.time()
        
        # 오래된 기록 정리
        self.request_history = [t for t in self.request_history 
                               if current_time - t < 60]
        
        # 초당 제한 (5회 -> 안전하게 4회)
        recent_1s = [t for t in self.request_history 
                     if current_time - t < 1]
        if len(recent_1s) >= 4:
            wait_time = 1 - (current_time - recent_1s[0])
            await asyncio.sleep(wait_time)
            
        # 분당 제한 (100회 -> 안전하게 90회)
        if len(self.request_history) >= 90:
            wait_time = 60 - (current_time - self.request_history[0])
            print(f"분당 제한 근접. {wait_time:.1f}초 대기")
            await asyncio.sleep(wait_time)
    
    def _get_screen_no(self, tr_code):
        """TR별 화면번호 반환"""
        if tr_code == "OPT10059":
            return "5959"
        return "5000"  # 기본 TR 화면번호


## 5. 데이터 처리 및 저장

### 5.1 틱 데이터 처리
```python
class TickProcessor:
    """틱 데이터 처리 및 CSV 저장"""
    
    def __init__(self, investor_manager):
        self.investor_manager = investor_manager
        self.buffer = deque(maxlen=10000)  # 백프레셔 처리
        
    def process_tick(self, stock_code, real_time_data):
        """틱 발생 시 데이터 처리"""
        
        # 1. 기본 틱 데이터
        tick_data = {
            'timestamp': datetime.now().isoformat(),
            'stock_code': stock_code,
            'current_price': real_time_data.get('current_price', 0),
            'volume': real_time_data.get('volume', 0),
            # ... 기타 실시간 지표
        }
        
        # 2. 수급 데이터 추가
        investor_data = self.investor_manager.get_data_for_tick(stock_code)
        
        # 개별 컬럼으로 저장
        for key, value in investor_data['net_vol'].items():
            tick_data[f'net_{key}'] = value
            
        # Delta 추가
        if investor_data['delta']:
            for key, value in investor_data['delta'].items():
                tick_data[f'delta_{key}'] = value
        else:
            for key in investor_data['net_vol'].keys():
                tick_data[f'delta_{key}'] = 0
                
        return tick_data
```

### 5.2 CSV 배치 저장
```python
class CSVWriter:
    """CSV 배치 저장으로 I/O 최적화"""
    
    def __init__(self):
        self.batch = []
        self.batch_size = 100
        self.write_lock = Lock()
        
    def add_tick(self, tick_data):
        """틱 데이터 추가"""
        self.batch.append(tick_data)
        if len(self.batch) >= self.batch_size:
            self.flush()
    
    def flush(self):
        """배치 쓰기"""
        with self.write_lock:
            if not self.batch:
                return
                
            filename = f"{tick_data['stock_code']}_36indicators_realtime_{datetime.now().strftime('%Y%m%d')}.csv"
            filepath = os.path.join("pure_websocket_data", filename)
            
            # 디렉토리 생성
            os.makedirs("pure_websocket_data", exist_ok=True)
            
            # CSV 쓰기
            file_exists = os.path.exists(filepath)
            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.get_columns())
                if not file_exists:
                    writer.writeheader()
                writer.writerows(self.batch)
            
            self.batch.clear()
```

### 5.3 종목별 상태 관리
```python
from dataclasses import dataclass

@dataclass
class StockState:
    """종목별 상태 관리"""
    code: str
    screen_no: str
    price_buffer: deque
    volume_buffer: deque
    last_tick_time: datetime
    investor_net_vol: dict
    orderbook: dict  # 호가 정보
    indicators: dict  # 계산된 지표
    
class StockManager:
    def __init__(self):
        self.stocks: Dict[str, StockState] = {}
        
    def initialize_stock(self, stock_code):
        """종목 초기화"""
        self.stocks[stock_code] = StockState(
            code=stock_code,
            screen_no=f"{1000 + len(self.stocks)}",
            price_buffer=deque(maxlen=1000),
            volume_buffer=deque(maxlen=1000),
            last_tick_time=datetime.now(),
            investor_net_vol={},
            orderbook={},
            indicators={}
        )
```

## 6. 초기 데이터 로드
```python
async def initialize_stock_data(self, stock_code):
    """종목별 초기 데이터 로드 (전일 고가 등)"""
    # OPT10001로 기본 정보 로드
    self.SetInputValue("종목코드", stock_code)
    self.CommRqData(f"주식기본정보_{stock_code}", "OPT10001", 0, "2000")
    
    # 응답 대기 후 prev_day_high 등 저장
    await self.wait_for_tr_data()
```

## 7. 에러 처리 및 복구

### 7.1 에러 복구 메커니즘
```python
class ErrorRecovery:
    def __init__(self):
        self.error_count = defaultdict(int)
        self.last_error = defaultdict(lambda: None)
        
    async def handle_error(self, stock_code, error):
        self.error_count[stock_code] += 1
        
        if self.error_count[stock_code] > 5:
            # 재등록 시도
            await self.re_register_stock(stock_code)
            self.error_count[stock_code] = 0
```

### 7.2 디버깅 도구
```python
class DebugChecker:
    """문제 진단용 체커"""
    
    def check_fid_registration(self):
        """FID 등록 확인"""
        print("✓ FID 리스트 완전성 체크")
        print("✓ SetRealReg opt_type='0' 확인")
        
    def check_data_flow(self):
        """데이터 흐름 확인"""
        print("✓ OnReceiveRealData 호출 빈도")
        print("✓ sRealType별 분기 처리")
        print("✓ GetCommRealData 반환값 파싱")
        
    def check_tr_timing(self):
        """TR 타이밍 확인"""
        print("✓ OPT10059 1분 간격 준수")
        print("✓ 종목별 독립 타이머")
```

## 8. 메인 실행 로직
```python
class RealtimeCollector:
    """실시간 수집 메인 클래스"""
    
    def __init__(self, config):
        self.stock_codes = config.TARGET_STOCKS
        self.investor_manager = InvestorNetManager(self.stock_codes)
        self.tr_scheduler = SafeTRScheduler(kiwoom_client)
        self.tick_processor = TickProcessor(self.investor_manager)
        self.csv_writer = CSVWriter()
        self.error_recovery = ErrorRecovery()
        
    async def run(self):
        """메인 실행"""
        # 초기 데이터 로드
        for stock_code in self.stock_codes:
            await self.initialize_stock_data(stock_code)
        
        # 실시간 등록
        self.register_real_data(self.stock_codes)
        
        # 비동기 태스크 실행
        tasks = [
            self.tr_loop(),      # TR 요청 처리
            self.tick_loop(),    # 틱 데이터 처리
            self.monitor_loop(), # 연결 상태 모니터링
        ]
        await asyncio.gather(*tasks)
        
    async def tr_loop(self):
        """TR 요청 루프"""
        while True:
            if not self.investor_manager.tr_schedule.empty():
                schedule_time, stock_code, round_num = \
                    self.investor_manager.tr_schedule.get()
                
                # 예정 시간까지 대기
                wait_time = schedule_time - time.time()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                # TR 요청
                try:
                    await self.tr_scheduler.request_opt10059(stock_code, round_num)
                except Exception as e:
                    await self.error_recovery.handle_error(stock_code, e)
                
            await asyncio.sleep(0.1)
```

## 9. 프로젝트 구조
## 기존 구조에 통합하는 방법:

### 1. **필수 추가만 하면 되는 것들:**

```python
# data_processor.py에 추가
class InvestorNetManager:
    # 수급 데이터 관리 클래스 추가
    
# kiwoom_client.py에 추가  
class SafeTRScheduler:
    # TR 제한 관리 클래스 추가
    
class ConnectionMonitor:
    # 연결 상태 모니터링 클래스 추가
```

### 2. **이미 있는 파일들 활용:**
- `csv_writer.py` - 배치 저장 기능만 추가
- `config.py` - 설정값 업데이트
- `main.py` - 클래스 임포트 수정

### 3. **새 파일 불필요한 것들:**
- `investor_manager.py` → `data_processor.py`에 통합
- `tr_scheduler.py` → `kiwoom_client.py`에 통합  
- `error_recovery.py` → `kiwoom_client.py`에 간단히 추가
- `debug_checker.py` → 별도 테스트 파일로 유지

```python
# data_processor.py
class DataProcessor:
    # 기존 코드...
    
    def __init__(self):
        self.investor_manager = InvestorNetManager()  # 추가
        # 기존 코드...
```

## 10. 개발 순서

1. **config.py 업데이트**
   - FID 리스트 상수 추가
   - TR 제한 설정값 수정 (초당 4회, 분당 90회)
   - 화면번호 베이스 설정

2. **kiwoom_client.py 개선**
   - register_real_data() 수정 (FID 완전 등록, opt_type="0")
   - OnReceiveRealData에 sRealType 분기 추가
   - SafeTRScheduler 클래스 추가 (TR 제한 관리)
   - ConnectionMonitor 클래스 추가 (연결 상태 체크)

3. **data_processor.py 확장**
   - parse_real_data() 안전 처리 강화
   - InvestorNetManager 클래스 추가 (수급 데이터 관리)
   - 틱 정의 명확화 (체결만 처리)

4. **csv_writer.py 최적화**
   - 배치 저장 기능 추가 (100틱마다)
   - flush() 메서드 구현
   - 스레드 안전성 확보

5. **main.py 통합**
   - 새 클래스들 임포트/초기화
   - 비동기 루프 구조 적용
   - 초기 데이터 로드 추가

6. **테스트 파일 실행**
   - test_connection.py로 연결 확인
   - test_realtime_simple.py로 데이터 흐름 검증
   - test_csv_writer.py로 저장 확인


## 11. 테스트 방법
- 단일 종목: TARGET_STOCKS = ['005930']
- 다중 종목: 1개 → 20개 점진 증가
- 대량 종목: 20개 이상으로 안정성 테스트

## 12. 주의사항
- **로그인 정보 보안**: 환경 변수 관리
- **틱 정의 준수**: 체결 이벤트만 틱으로 처리, CSV 저장
- **FID 완전 등록**: 41~80 범위 포함 필수
- **sRealType 체크**: 이벤트 타입별 분기 처리
- **데이터 파싱**: abs(int()) 처리 및 이상치 체크
- **화면번호 분리**: 종목별 독립 화면번호
- **SetRealReg opt_type**: "0" 사용 (신규 등록)
- **TR 제한 준수**: 초당 4회, 분당 90회, 종목별 1분 제한
- **메모리 관리**: deque maxlen 설정, 백프레셔 처리
- **CSV 배치 저장**: 100틱마다 저장으로 I/O 최적화
- **Windows/32비트 환경**: Python 3.8 32비트 필수

## 13. 로그 관리
- logging 모듈 사용
- 레벨: INFO(일반), WARNING(재시도), ERROR(실패)
- logs/ 디렉토리에 날짜별 파일 저장
- 실시간 이벤트 빈도 및 에러 추적

## 14. 코드 작성 참고
- GitHub pykiwoom 예제 참고 가능
- 키움증권 OpenAPI 공식 샘플 참고
- 참고 시 출처 주석 명시
- 직접 복사 금지, 재구현 원칙