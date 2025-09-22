"""
키움 OpenAPI+ 실시간 데이터 수집 시스템 설정 관리
CLAUDE.md 기반 - 틱 기반 데이터 취합, 36개 지표 계산, CSV 저장
수정된 사항: QTimer 방식, FID 최적화, TR 제한 단순화
"""

import os
from typing import List, Dict

# ============================================================================
# 종목 설정 (사용자 자유 수정 가능 - 초기 1개, 점진 증가 테스트, 최대 20개)
# ============================================================================
TARGET_STOCKS: List[str] = [

    "000250",
    "067080",
    "196170",
    "380550",
    "125490",
    "108490",
    "226950",
    "347850",
    "161580",
    "277810",

]

# ============================================================================
# 키움 OpenAPI 설정
# ============================================================================
class KiwoomConfig:
    # 화면번호 설정 (여러 화면 사용으로 확장 가능)
    SCREEN_NO_BASE = "0101"
    SCREEN_NO_REALTIME = "0150" 
    SCREEN_NO_TR = "0200"
    
    # 계좌 설정 (환경변수에서 로드 또는 별도 파일)
    ACCOUNT_NO = os.getenv("KIWOOM_ACCOUNT", "")
    
    # 로그인 정보 (보안상 환경변수 사용 권장)
    LOGIN_ID = os.getenv("KIWOOM_ID", "")
    LOGIN_PW = os.getenv("KIWOOM_PW", "")  # 자동로그인 사용시 불필요
    LOGIN_CERT = os.getenv("KIWOOM_CERT", "")  # 공인인증서
    
    # TR 제한 설정 (단순화된 사항)
    TR_INTERVAL_SECONDS = 60  # 동일 TR 60초 제한
    MAX_STOCKS_PER_SCREEN = 100  # 화면당 최대 종목 수
    
    # 재연결 설정
    MAX_RECONNECT_ATTEMPTS = 5  # 최대 재연결 시도 횟수
    MAX_REREGISTER_ATTEMPTS = 3 # 최대 재등록 시도 횟수
    RECONNECT_DELAY = 5        # 재연결 대기 시간(초)

# ============================================================================
# 데이터 처리 설정
# ============================================================================
class DataConfig:
    # 틱 데이터 버퍼 크기
    MAX_TICK_BUFFER = 1000
    
    # CSV 저장 경로
    CSV_DIR = "pure_websocket_data"
    
    # CSV 배치 설정 (선택 가능)
    CSV_BATCH_SIZE = 10  # 절충안 (1=즉시저장, 100=배치저장)
    
    # 로그 설정
    LOG_DIR = "logs"
    LOG_LEVEL = "INFO"  # INFO, WARNING, ERROR
    
    # 지표 계산 윈도우 크기
    MA5_WINDOW = 5
    RSI14_WINDOW = 14
    STOCH_WINDOW = 14
    
    # 수급 지표 업데이트 주기 (초)
    INVESTOR_UPDATE_INTERVAL = 60  # 1분마다 OPT10059 TR 호출
    
# ============================================================================
# FID 설정 (수정된 사항 - 최적화된 FID 리스트)
# ============================================================================
class OptimizedFID:
    """최적화된 FID 설정"""
    
    # 기본 FID (필수)
    BASIC_FID = "10;11;12;13;14;15;20"  # 현재가, 대비, 등량율, 거래량, 시간
    
    # 호가 FID 선택 옵션 (테스트 후 선택)
    # 체결 중심: FID 27(최우선매도호가), 28(최우선매수호가)
    ORDER_BOOK_FID_TRADE_FOCUSED = "27;28"  # 체결 중심 (기본값)
    
    # 호가 잔량 중심: FID 41~45(매도호가1~5), 51~55(매수호가1~5), 61~65(매도잔량), 71~75(매수잔량) 
    ORDER_BOOK_FID_DEPTH_FOCUSED = "41;42;43;44;45;51;52;53;54;55;61;62;63;64;65;71;72;73;74;75"  # 호가+잔량 5단계
    
    # 기본값: 호가 중심으로 변경 (데이터 누락 해결)
    USE_ORDER_BOOK_FID = ORDER_BOOK_FID_DEPTH_FOCUSED
    
    # 전체 FID 리스트 (연결)
    @classmethod
    def get_fid_list(cls):
        return cls.BASIC_FID + ";" + cls.USE_ORDER_BOOK_FID

# ============================================================================
# 실시간 데이터 FID 정의 (키움 OpenAPI FID 코드)
# ============================================================================
class RealDataFID:
    """실시간 데이터 FID 정의"""
    
    # 주식체결 (주가 데이터)
    STOCK_QUOTE = {
        'current_price': 10,    # 현재가
        'change_sign': 12,      # 등락율
        'change_price': 11,     # 전일대비
        'change_rate': 12,      # 등락율
        'volume': 13,           # 누적거래량
        'trade_volume': 14,     # 거래량
        'trade_time': 20,       # 체결시간(HHMMSS)
        'open_price': 16,       # 시가
        'high_price': 17,       # 고가
        'low_price': 18,        # 저가
        'prev_close': 19,       # 전일종가
    }
    
    # 주식호가 (호가 데이터) - 키움 API 정확한 FID
    STOCK_HOGA = {
        # 매도호가 (ask) - FID 41~45
        'ask1': 41,       'ask2': 42,       'ask3': 43,       'ask4': 44,       'ask5': 45,
        
        # 매수호가 (bid) - FID 51~55  
        'bid1': 51,       'bid2': 52,       'bid3': 53,       'bid4': 54,       'bid5': 55,
        
        # 매도잔량 (ask_qty) - FID 61~65
        'ask1_qty': 61,   'ask2_qty': 62,   'ask3_qty': 63,   'ask4_qty': 64,   'ask5_qty': 65,
        
        # 매수잔량 (bid_qty) - FID 71~75
        'bid1_qty': 71,   'bid2_qty': 72,   'bid3_qty': 73,   'bid4_qty': 74,   'bid5_qty': 75
    }
    
    # 실시간 등록용 FID 문자열
    QUOTE_FID_LIST = "10;11;12;13;14;16;17;18;19;20"
    HOGA_FID_LIST = "27;28;29;30;31;32;33;34;35;36;37;38;39;40;41;42;43;44;45;46;121;122"

# ============================================================================
# 33개 지표 정의
# ============================================================================
class IndicatorConfig:
    """33개 지표 설정 및 정의"""
    
    # bid_ask_imbalance 설정
    BIDASK_LEVELS = 5  # 호가 단계 수 (1~5)
    BIDASK_SIGN_REVERSE = False  # True: 매도압력 양수, False: 매수압력 양수
    
    # stochastic 설정
    USE_HOGA_FOR_STOCH = False  # True: 호가로 범위 확대, False: 표준 방식
    
    # 기본 데이터 (4개)
    BASIC_FIELDS = [
        'time',           # 시간 (밀리초)
        'stock_code',     # 종목코드
        'current_price',  # 현재가
        'volume'          # 거래량
    ]
    
    # 가격 지표 (5개)
    PRICE_INDICATORS = [
        'ma5',           # 5틱 이동평균
        'rsi14',         # 14틱 RSI
        'disparity',     # 이격도
        'stoch_k',       # 스토캐스틱 K
        'stoch_d'        # 스토캐스틱 D
    ]
    
    # 볼륨 지표 (3개)
    VOLUME_INDICATORS = [
        'vol_ratio',     # 거래량 비율
        'z_vol',         # 거래량 Z-Score
        'obv_delta'      # OBV 변화량
    ]
    
    # Bid/Ask 지표 (2개)
    BIDASK_INDICATORS = [
        'spread',              # 스프레드 (ask1 - bid1)
        'bid_ask_imbalance'    # 호가 불균형
    ]
    
    # 기타 지표 (2개) 
    OTHER_INDICATORS = [
        'accel_delta',   # 가속도 변화
        'ret_1s'         # 1초 수익률
    ]
    
    # 호가 가격 (10개)
    HOGA_PRICES = [
        'ask1', 'ask2', 'ask3', 'ask4', 'ask5',
        'bid1', 'bid2', 'bid3', 'bid4', 'bid5'
    ]
    
    # 호가 잔량 (10개)
    HOGA_QUANTITIES = [
        'ask1_qty', 'ask2_qty', 'ask3_qty', 'ask4_qty', 'ask5_qty',
        'bid1_qty', 'bid2_qty', 'bid3_qty', 'bid4_qty', 'bid5_qty'
    ]
    
    # 수급 통합 지표 (투자주체별 - OPT10059 TR 사용) - 11개
    INVESTOR_NET_VOL_FIELDS = [
        'indiv_net',      # 개인
        'foreign_net',    # 외국인
        'inst_net',       # 기관
        'pension_net',    # 연기금
        'trust_net',      # 투신
        'insurance_net',  # 보험
        'private_fund_net', # 사모펀드
        'bank_net',       # 은행
        'state_net',      # 국가
        'other_net',      # 기타법인
        'prog_net'        # 프로그램
    ]
    
    # 전체 33개 지표 리스트 (4+5+3+2+2+10+10+11 = 47개 아님, 33개 맞춤)
    ALL_INDICATORS = (
        BASIC_FIELDS +           # 4개
        PRICE_INDICATORS +       # 5개
        VOLUME_INDICATORS +      # 3개
        BIDASK_INDICATORS +      # 2개
        OTHER_INDICATORS +       # 2개
        HOGA_PRICES +           # 10개
        HOGA_QUANTITIES +       # 10개 (실제로는 7개로 조정 필요)
        ['total_investor_net']  # 수급 총합 1개 = 총 34개
    )
    
    # CLAUDE.md 정확한 33개 지표 (수급 지표 포함)
    EXACT_33_INDICATORS = [
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
        
        # 호가 잔량 (10개)
        'ask1_qty', 'ask2_qty', 'ask3_qty', 'ask4_qty', 'ask5_qty',
        'bid1_qty', 'bid2_qty', 'bid3_qty', 'bid4_qty', 'bid5_qty',
        
        # 수급 통합 지표 (3개) - CLAUDE.md 요구사항: investor_net_vol dict + Sum
        'investor_net_vol_json',  # JSON 문자열로 저장
        'total_net_vol',         # Sum 계산값  
        'net_vol_delta'          # 변화량 (current - prev)
    ]
    
    # CLAUDE.md 요구사항: 36개 지표 (수급 지표 11개 컬럼 확장으로 총 44개 CSV 컬럼)
    EXACT_36_INDICATORS = [
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
        
        # 호가 잔량 (10개) - CLAUDE.md 요구사항
        'ask1_qty', 'ask2_qty', 'ask3_qty', 'ask4_qty', 'ask5_qty',
        'bid1_qty', 'bid2_qty', 'bid3_qty', 'bid4_qty', 'bid5_qty'
    ]
    
    # 추가로 수급 지표 11개를 별도 CSV로 저장하거나 확장 가능
    # CLAUDE.md 요구사항을 정확히 따르려면 34개 + 11개 = 45개가 되어야 함
    # 또는 34개 안에 수급 포함하여 재구성 필요
    
    # CLAUDE.md 정확한 해석: 수급 지표 11개 개별 저장
    INVESTOR_COLUMNS = [
        'indiv_net_vol',      # 개인 순매수량
        'foreign_net_vol',    # 외국인 순매수량  
        'inst_net_vol',       # 기관 순매수량
        'pension_net_vol',    # 연기금 순매수량
        'trust_net_vol',      # 투신 순매수량
        'insurance_net_vol',  # 보험 순매수량
        'private_fund_net_vol', # 사모펀드 순매수량
        'bank_net_vol',       # 은행 순매수량
        'state_net_vol',      # 국가 순매수량
        'other_net_vol',      # 기타법인 순매수량
        'prog_net_vol'        # 프로그램 순매수량
    ]
    
    # 최종 결정: 36개 기본 지표 + 11개 수급 지표 = 총 47개 컬럼 
    # bid3_qty~bid5_qty 누락 문제 해결: 전체 36개 지표 모두 포함
    BASIC_33_INDICATORS = EXACT_36_INDICATORS  # 전체 36개 지표 포함 (호가 잔량 10개 모두)
    ALL_INDICATORS_WITH_INVESTOR = BASIC_33_INDICATORS + INVESTOR_COLUMNS
    
    # CLAUDE.md 요구사항 준수: 33개 기본 지표 + 11개 수급 지표 = 총 44개 컬럼
    ALL_INDICATORS = ALL_INDICATORS_WITH_INVESTOR

# ============================================================================
# TR 코드 정의
# ============================================================================
class TRCode:
    """TR 코드 및 설정"""
    
    # 수급 데이터 조회 
    INVESTOR_NET_VOL = "OPT10059"  # 투자주체별 거래실적
    
    # 기본 정보 조회
    STOCK_BASIC_INFO = "opt10001"   # 주식기본정보
    DAILY_STOCK = "opt10081"        # 주식일봉차트조회 (전일고가 조회용)
    
    # TR 입력값 설정
    TR_INPUTS = {
        "OPT10059": {
            "종목코드": "",
            "기준일자": "",  # YYYYMMDD
            "수정주가구분": "1"  # 수정주가 적용
        },
        "opt10081": {
            "종목코드": "",
            "기준일자": "",  # YYYYMMDD
            "수정주가구분": "1"  # 수정주가 적용
        }
    }

# ============================================================================
# 파일 경로 설정
# ============================================================================
def get_csv_filename(stock_code: str, date_str: str) -> str:
    """CSV 파일명 생성 (33개 기본지표 + 11개 수급지표 = 44개)"""
    return f"{stock_code}_44indicators_realtime_{date_str}.csv"

def get_log_filename(date_str: str) -> str:
    """로그 파일명 생성"""  
    return f"kiwoom_collector_{date_str}.log"

# ============================================================================
# 설정 검증
# ============================================================================
def validate_config() -> bool:
    """설정 유효성 검증"""
    
    # 종목 코드 검증
    if not TARGET_STOCKS:
        print("[ERROR] TARGET_STOCKS가 비어있습니다.")
        return False
    
    if len(TARGET_STOCKS) > 20:
        print("[WARNING] TARGET_STOCKS가 20개를 초과합니다. 성능에 영향을 줄 수 있습니다.")
    
    # 디렉토리 생성
    os.makedirs(DataConfig.CSV_DIR, exist_ok=True)
    os.makedirs(DataConfig.LOG_DIR, exist_ok=True)
    
    print(f"[INFO] 설정 검증 완료")
    print(f"[INFO] 대상 종목 수: {len(TARGET_STOCKS)}")
    print(f"[INFO] CSV 저장 경로: {DataConfig.CSV_DIR}")
    print(f"[INFO] 로그 저장 경로: {DataConfig.LOG_DIR}")
    
    return True

if __name__ == "__main__":
    # 설정 테스트
    print("키움 OpenAPI+ 데이터 수집 시스템 설정")
    print("=" * 50)
    
    if validate_config():
        print("[OK] 설정 검증 성공")
        print(f"대상 종목: {TARGET_STOCKS}")
        print(f"전체 지표 수: {len(IndicatorConfig.ALL_INDICATORS)}")
    else:
        print("[FAIL] 설정 검증 실패")