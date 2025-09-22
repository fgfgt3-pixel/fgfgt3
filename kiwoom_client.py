"""
키움 OpenAPI+ 클라이언트
CLAUDE.md 기반 - 로그인/연결/실시간 이벤트 처리, 틱 기반 데이터 취합
"""

import sys
import time
import logging
import asyncio
from datetime import datetime
from queue import Queue, Empty
from typing import Dict, List, Callable, Optional
from collections import defaultdict

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QAxContainer import QAxWidget  
from PyQt5.QtCore import QEventLoop, QTimer

from config import (
    TARGET_STOCKS, KiwoomConfig, DataConfig, RealDataFID, TRCode, OptimizedFID
)

# 자동 로그인 비활성화
SECURE_LOGIN_AVAILABLE = False

class KiwoomClient:
    """
    키움 OpenAPI+ 클라이언트
    - 로그인/연결 관리
    - 실시간 데이터 수신 (OnReceiveRealData)
    - TR 요청 큐잉 및 제한 관리
    - 자동 재연결/재등록
    """
    
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
        
        # OCX 컨트롤 생성 (숨겨진 윈도우를 부모로)
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1", self.window)
        
        # 연결 상태
        self.connected = False
        self.login_attempted = False
        
        # 자동 로그인 비활성화
        self.secure_login_helper = None
        self.auto_login_enabled = False
        self.secure_credentials_file = None
        
        # 이벤트 루프
        self.login_event_loop = None
        self.tr_event_loops = {}  # TR별 이벤트 루프
        
        # 계좌 정보
        self.account_list = []
        self.user_info = {}
        
        # TR 요청 큐 및 제한 관리
        self.tr_queue = Queue()
        self.tr_request_times = []  # 요청 시간 추적
        self.tr_results = {}        # TR 결과 저장
        self.screen_to_stock = {}   # screen_no -> stock_code 매핑
        
        # 실시간 등록 상태
        self.registered_stocks = set()
        self.screen_numbers = {}    # 화면번호 관리
        
        # 전일고가 데이터 저장
        self.prev_day_high = {}
        
        # 호가 데이터 이전값 저장 (0 fallback 방지)
        self.prev_hoga = {}
        
        # 실시간 호가 데이터
        self.ask1 = {}
        self.bid1 = {}
        
        # 콜백 함수들
        self.realdata_callback: Optional[Callable] = None
        self.tr_callback: Optional[Callable] = None
        
        # 재연결 관리
        self.reconnect_count = 0
        self.reregister_count = defaultdict(int)
        
        # 로깅 설정
        self.setup_logging()
        
        # 이벤트 연결
        self.setup_events()
        
        # TR 요청 관리 타이머
        self.tr_timer = QTimer()
        self.tr_timer.timeout.connect(self.process_tr_queue)
        self.tr_timer.start(1000)  # 1초마다 큐 처리
        
    def setup_logging(self):
        """로깅 설정"""
        log_filename = f"{DataConfig.LOG_DIR}/kiwoom_client_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=getattr(logging, DataConfig.LOG_LEVEL),
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_events(self):
        """이벤트 핸들러 연결"""
        self.ocx.OnEventConnect.connect(self.on_event_connect)
        self.ocx.OnReceiveTrData.connect(self.on_receive_tr_data)
        self.ocx.OnReceiveRealData.connect(self.on_receive_real_data)
        self.ocx.OnReceiveMsg.connect(self.on_receive_msg)
        
    # ========================================================================
    # 로그인 및 연결 관리
    # ========================================================================
    
    def enable_auto_login(self, credentials_file: str = None) -> bool:
        """자동 로그인 비활성화"""
        self.logger.info("자동 로그인이 비활성화되었습니다. 수동으로 로그인해주세요.")
        return False
    
    def auto_login(self) -> bool:
        """자동 로그인 비활성화 - 수동 로그인만 사용"""
        self.logger.info("자동 로그인이 비활성화되었습니다. 수동으로 로그인해주세요.")
        return False
    
    def connect(self, use_auto_login: bool = False) -> bool:
        """키움 서버 연결
        Args:
            use_auto_login: True면 GUI 자동화로 로그인 시도
        """
        if self.login_attempted:
            self.logger.warning("이미 로그인 시도 중입니다.")
            return self.connected
            
        # 윈도우 표시 (핸들값 문제 해결)
        self.window.show()
        self.app.processEvents()
        
        # 연결 상태 확인
        try:
            state = self.ocx.dynamicCall("GetConnectState()")
            if state == 1:
                self.logger.info("이미 연결되어 있습니다.")
                self.connected = True
                self.get_account_info()
                return True
        except Exception as e:
            self.logger.error(f"연결 상태 확인 실패: {e}")
            
        # 로그인 시도
        self.logger.info("키움 서버 연결 시도 중...")
        self.login_attempted = True
        
        try:
            self.login_event_loop = QEventLoop()
            
            # CommConnect 호출
            ret = self.ocx.dynamicCall("CommConnect()")
            if ret == 0:
                # 자동 로그인 옵션 확인
                if use_auto_login:
                    try:
                        from auto_login_gui import KiwoomAutoLogin
                        auto_login = KiwoomAutoLogin()
                        self.logger.info("GUI 자동 로그인 시도...")
                        
                        # 로그인 창이 뜰 때까지 대기
                        time.sleep(2)
                        
                        # 자동 로그인 실행 (별도 스레드로)
                        from PyQt5.QtCore import QThread
                        class AutoLoginThread(QThread):
                            def run(self):
                                auto_login.safe_auto_login()
                        
                        login_thread = AutoLoginThread()
                        login_thread.start()
                        
                    except ImportError:
                        self.logger.warning("auto_login_gui 모듈이 없습니다. 수동 로그인으로 진행합니다.")
                        self.logger.info("로그인 창이 열렸습니다. 수동으로 로그인해주세요.")
                else:
                    self.logger.info("로그인 창이 열렸습니다. 수동으로 로그인해주세요.")
                
                # 타임아웃 설정 (30초)
                QTimer.singleShot(30000, self.login_timeout)
                self.login_event_loop.exec_()
            else:
                self.logger.error(f"CommConnect 실패 (코드: {ret})")
                self.login_attempted = False
                
        except Exception as e:
            self.logger.error(f"연결 중 예외 발생: {e}")
            self.login_attempted = False
            
        return self.connected
    
    def login_timeout(self):
        """로그인 타임아웃 처리"""
        if not self.connected and self.login_event_loop:
            self.logger.warning("로그인 타임아웃")
            if self.login_event_loop.isRunning():
                self.login_event_loop.exit()
            self.login_attempted = False
    
    def on_event_connect(self, err_code: int):
        """로그인 이벤트 처리"""
        if err_code == 0:
            self.logger.info("키움 서버 연결 성공")
            self.connected = True
            self.reconnect_count = 0  # 재연결 카운트 리셋
            self.get_account_info()
        else:
            error_msgs = {
                -100: "사용자 정보 교환 실패",
                -101: "서버 접속 실패",
                -102: "버전 처리 실패",
                -106: "보안 모듈 오류"
            }
            msg = error_msgs.get(err_code, f"알 수 없는 오류 ({err_code})")
            self.logger.error(f"로그인 실패: {msg}")
            self.connected = False
            
        self.login_attempted = False
        if self.login_event_loop and self.login_event_loop.isRunning():
            self.login_event_loop.exit()
    
    def get_account_info(self):
        """계좌 정보 조회"""
        try:
            self.user_info = {
                'user_id': self.ocx.dynamicCall("GetLoginInfo(QString)", "USER_ID"),
                'user_name': self.ocx.dynamicCall("GetLoginInfo(QString)", "USER_NAME"),
                'keyboard_security': self.ocx.dynamicCall("GetLoginInfo(QString)", "KEY_BSECGB"),
                'firewall': self.ocx.dynamicCall("GetLoginInfo(QString)", "FIREW_SECGB")
            }
            
            accounts = self.ocx.dynamicCall("GetLoginInfo(QString)", "ACCNO").strip()
            self.account_list = [acc for acc in accounts.split(';') if acc]
            
            self.logger.info(f"사용자: {self.user_info['user_name']} ({self.user_info['user_id']})")
            if self.account_list:
                self.logger.info(f"계좌: {self.account_list[0]}")
                
        except Exception as e:
            self.logger.error(f"계좌 정보 조회 실패: {e}")
    
    def disconnect(self):
        """연결 종료"""
        try:
            if self.connected:
                self.ocx.dynamicCall("CommTerminate()")
                self.logger.info("키움 서버 연결 종료")
            self.connected = False
        except Exception as e:
            self.logger.error(f"연결 종료 실패: {e}")
    
    # ========================================================================
    # 실시간 데이터 등록 및 수신
    # ========================================================================
    
    def register_realdata(self, stocks: List[str] = None) -> bool:
        """실시간 데이터 등록"""
        if not self.connected:
            self.logger.error("연결되지 않음")
            return False
            
        if stocks is None:
            stocks = TARGET_STOCKS
            
        try:
            # 종목을 화면별로 분할 (화면당 최대 100종목)
            screen_groups = []
            for i in range(0, len(stocks), KiwoomConfig.MAX_STOCKS_PER_SCREEN):
                group = stocks[i:i + KiwoomConfig.MAX_STOCKS_PER_SCREEN]
                screen_groups.append(group)
            
            # modify.md 방안 2: 완전 별도 화면번호 체계
            success_count = 0
            SCREEN_BASE_TRADE = "5000"  # 체결용
            SCREEN_BASE_HOGA = "6000"   # 호가용
            
            for idx, group in enumerate(screen_groups):
                stock_codes = ";".join(group)
                
                # 종목별 개별 등록 (modify.md 권장)
                for stock_idx, stock_code in enumerate(group):
                    # 1. 기존 등록 제거 (중요!)
                    self.ocx.dynamicCall("SetRealRemove(QString, QString)", "ALL", stock_code)
                    time.sleep(0.05)
                    
                    # 첫 번째 종목인지 확인 (전체 종목 중 첫 번째)
                    is_first = (idx == 0 and stock_idx == 0)
                    reg_type = "0" if is_first else "1"
                    
                    # 2. 체결 데이터 등록 (완전 별도 화면)
                    screen_trade = f"{SCREEN_BASE_TRADE}{idx:02d}{stock_idx:01d}"
                    basic_fid = OptimizedFID.BASIC_FID
                    self.logger.info(f"📊 [체결등록] 화면={screen_trade}, 종목={stock_code}, FID={basic_fid}, 타입={reg_type}")
                    ret1 = self.ocx.dynamicCall(
                        "SetRealReg(QString, QString, QString, QString)",
                        screen_trade, stock_code, basic_fid, reg_type
                    )
                    
                    time.sleep(0.1)  # API 제한 방지
                    
                    # 3. 호가 데이터 별도 화면 등록 (중요!)
                    screen_hoga = f"{SCREEN_BASE_HOGA}{idx:02d}{stock_idx:01d}"
                    hoga_fid = OptimizedFID.USE_ORDER_BOOK_FID
                    self.logger.info(f"📈 [호가등록] 화면={screen_hoga}, 종목={stock_code}, FID={hoga_fid}, 타입={reg_type}")
                    ret2 = self.ocx.dynamicCall(
                        "SetRealReg(QString, QString, QString, QString)",
                        screen_hoga, stock_code, hoga_fid, reg_type
                    )
                    
                    time.sleep(0.1)  # 안정성 대기
                    
                    # 등록 결과 확인
                    if ret1 == 0 and ret2 == 0:
                        self.screen_numbers[screen_trade] = [stock_code]  # 체결 화면
                        self.screen_numbers[screen_hoga] = [stock_code]   # 호가 화면
                        self.registered_stocks.add(stock_code)
                        success_count += 1
                        self.logger.info(f"✅ [등록성공] {stock_code}: 체결({screen_trade}) + 호가({screen_hoga})")
                    else:
                        self.logger.error(f"❌ [등록실패] {stock_code}: 체결={ret1}, 호가={ret2}")
                        
                    # 과도한 요청 방지
                    time.sleep(0.2)
            
            self.logger.info(f"전체 실시간 등록: {success_count}/{len(stocks)} 성공")
            return success_count == len(stocks)
            
        except Exception as e:
            self.logger.error(f"실시간 등록 중 예외: {e}")
            return False
    
    def on_receive_real_data(self, stock_code: str, real_type: str, real_data: str):
        """실시간 데이터 수신 처리"""
        try:
            # 전문가 진단: 모든 real_type 상세 로깅
            self.logger.info(f"📡 [실시간수신] {stock_code}: real_type='{real_type}' (raw_data_len={len(real_data)})")
            
            # 실시간 데이터 수신 카운터 추가
            if not hasattr(self, 'realdata_count'):
                self.realdata_count = 0
            self.realdata_count += 1
            
            # 100번마다 수신 상태 로그
            if self.realdata_count % 100 == 0:
                self.logger.info(f"✅ 실시간 데이터 {self.realdata_count}개 수신 완료")
            
            # 알려진 타입이 아닌 경우 경고
            known_types = ["주식체결", "주식호가", "주식호가잔량", "주식시세"]
            if real_type not in known_types:
                self.logger.warning(f"⚠️  [미지타입] {stock_code}: '{real_type}' - 새로운 이벤트 타입!")
            
            # 현재 시간을 Unix timestamp (밀리초 단위)로 생성
            from datetime import datetime
            now = datetime.now()
            current_time = int(now.timestamp() * 1000)  # Unix timestamp in milliseconds
            
            # 데이터 추출
            data = {'time': current_time, 'stock_code': stock_code}
            
            if real_type == "주식체결":
                # 주가 데이터 추출
                for field, fid in RealDataFID.STOCK_QUOTE.items():
                    try:
                        value = self.ocx.dynamicCall("GetCommRealData(QString, int)", stock_code, fid)
                        data[field] = self.parse_real_value(value, field)
                    except Exception as ex:
                        self.logger.debug(f"FID {fid} 추출 오류: {ex}")
                        data[field] = 0
                
                # 현재가 로그
                current_price = data.get('current_price', 0)
                if current_price > 0:
                    self.logger.info(f"[체결] {stock_code}: {current_price:,}원")
                        
            elif real_type in ["주식호가", "주식호가잔량"]:
                # modify.md 방안 3: 디버깅 강화 - raw 데이터 전체 덤프
                self.logger.info(f"🎯 [호가이벤트수신] {stock_code}: real_type='{real_type}'")
                self.logger.debug(f"📊 RAW 호가 데이터 전체: {str(real_data)[:200]}...")
                
                for field, fid in RealDataFID.STOCK_HOGA.items():
                    try:
                        raw_value = self.ocx.dynamicCall("GetCommRealData(QString, int)", stock_code, fid)
                        
                        # modify.md 방안 3: 다양한 방식으로 FID 테스트
                        raw_value_int = self.ocx.dynamicCall("GetCommRealData(QString, int)", stock_code, fid)
                        raw_value_str = self.ocx.dynamicCall("GetCommRealData(QString, QString)", stock_code, str(fid))
                        
                        self.logger.info(f"🔍 [FID검증] FID {fid} ({field}): int='{raw_value_int}', str='{raw_value_str}'")
                        
                        # 더 안전한 값 선택 (비어있지 않은 값 우선)
                        raw_value = raw_value_int if raw_value_int.strip() else raw_value_str
                        
                        # 호가 데이터 파싱 개선: 0 fallback 방지
                        cleaned_value = raw_value.strip().replace('+', '').replace('-', '') if raw_value else ''
                        
                        if not cleaned_value and stock_code in self.prev_hoga and field in self.prev_hoga[stock_code]:
                            # 빈 값일 때 이전 값 유지
                            parsed_value = self.prev_hoga[stock_code][field]
                        else:
                            parsed_value = int(cleaned_value or 0) if cleaned_value else 0
                            # 이전 값 저장
                            if stock_code not in self.prev_hoga:
                                self.prev_hoga[stock_code] = {}
                            self.prev_hoga[stock_code][field] = parsed_value
                        
                        data[field] = parsed_value
                        
                        # 파싱 결과 로깅
                        self.logger.info(f"    → cleaned='{cleaned_value}' → parsed={parsed_value}")
                        
                        # 실제 데이터 발견시 강조
                        if parsed_value != 0:
                            self.logger.info(f"💡 [데이터발견] FID {fid} ({field}): {parsed_value}")
                            
                    except Exception as ex:
                        self.logger.error(f"호가 FID {fid}({field}) 추출/파싱 오류: {ex}")
                        data[field] = 0
                
                # 키 매핑 수정: ask1_price → ask1
                ask1_price = data.get('ask1', 0)
                bid1_price = data.get('bid1', 0)
                
                if ask1_price > 0:
                    self.ask1[stock_code] = ask1_price
                if bid1_price > 0:
                    self.bid1[stock_code] = bid1_price
                
                # 호가 데이터 수신 로그 (항상 출력)
                self.logger.info(f"[호가결과] {stock_code}: 매도1호가 {ask1_price:,}원, 매수1호가 {bid1_price:,}원")
                
                # 호가 데이터가 모두 0인 경우 경고
                if ask1_price == 0 and bid1_price == 0:
                    self.logger.warning(f"[호가경고] {stock_code}: 호가 데이터가 모두 0입니다.")
            else:
                self.logger.warning(f"[미처리실시간타입] {real_type} - 데이터 무시됨")
            
            # 콜백 함수 호출
            if self.realdata_callback:
                self.realdata_callback(stock_code, real_type, data)
            else:
                self.logger.warning("realdata_callback이 설정되지 않음")
                
        except Exception as e:
            self.logger.error(f"실시간 데이터 처리 오류: {e}")
    
    def parse_real_value(self, value: str, field: str) -> float:
        """실시간 데이터 값 파싱"""
        try:
            if not value or value.strip() == "":
                return 0.0
            
            # 쉼표 제거
            clean_value = str(value).replace(',', '').strip()
            if not clean_value:
                return 0.0
                
            # 숫자 변환
            if 'price' in field or field in ['current_price', 'open_price', 'high_price', 'low_price']:
                return abs(float(clean_value))  # 가격은 절댓값
            elif 'qty' in field or field in ['volume', 'trade_volume']:
                return int(clean_value)
            elif 'time' in field:
                return clean_value
            else:
                return float(clean_value)
                
        except (ValueError, TypeError):
            return 0.0
    
    # ========================================================================
    # TR 요청 관리 (큐잉 및 제한)
    # ========================================================================
    
    def request_tr(self, tr_code: str, inputs: Dict[str, str], screen_no: str = None) -> bool:
        """TR 요청 (큐에 추가)"""
        if screen_no is None:
            screen_no = f"{KiwoomConfig.SCREEN_NO_TR}{self.tr_queue.qsize():03d}"
            
        request = {
            'tr_code': tr_code,
            'inputs': inputs,
            'screen_no': screen_no,
            'timestamp': time.time(),
            'stock_code': inputs.get('종목코드', '')  # 종목코드 추가로 TR 결과 연결
        }
        
        self.tr_queue.put(request)
        self.logger.debug(f"TR 요청 큐 추가: {tr_code} (큐 크기: {self.tr_queue.qsize()})")
        return True
    
    def process_tr_queue(self):
        """TR 큐 처리 (초당 1회 제한)"""
        if not self.connected or self.tr_queue.empty():
            return
            
        # 요청 제한 체크
        current_time = time.time()
        
        # 1분 이내 요청 수 체크
        self.tr_request_times = [t for t in self.tr_request_times if current_time - t < 60]
        if len(self.tr_request_times) >= KiwoomConfig.TR_PER_MINUTE:
            self.logger.warning("분당 TR 요청 제한 도달")
            return
            
        # 1초 이내 요청 체크
        recent_requests = [t for t in self.tr_request_times if current_time - t < 1]
        if len(recent_requests) >= KiwoomConfig.TR_PER_SECOND:
            return  # 1초 대기
            
        try:
            request = self.tr_queue.get_nowait()
            self.send_tr_request(request)
            self.tr_request_times.append(current_time)
            
        except Empty:
            pass
        except Exception as e:
            self.logger.error(f"TR 큐 처리 오류: {e}")
    
    def send_tr_request(self, request: Dict):
        """실제 TR 요청 전송"""
        tr_code = request['tr_code']
        inputs = request['inputs']
        screen_no = request['screen_no']
        
        try:
            # 입력값 설정
            for key, value in inputs.items():
                self.ocx.dynamicCall("SetInputValue(QString, QString)", key, str(value))
            
            # screen_no -> stock_code 매핑 저장
            stock_code = request.get('stock_code', '')
            if stock_code:
                self.screen_to_stock[screen_no] = stock_code
            
            # 이벤트 루프 생성
            self.tr_event_loops[screen_no] = QEventLoop()
            
            # TR 요청
            ret = self.ocx.dynamicCall(
                "CommRqData(QString, QString, int, QString)",
                f"{tr_code}_REQ", tr_code, 0, screen_no
            )
            
            if ret == 0:
                self.logger.debug(f"TR 요청 성공: {tr_code}")
                # 타임아웃 설정 (10초)
                QTimer.singleShot(10000, lambda: self.tr_timeout(screen_no))
                self.tr_event_loops[screen_no].exec_()
            else:
                self.logger.error(f"TR 요청 실패: {tr_code} (코드: {ret})")
                
        except Exception as e:
            self.logger.error(f"TR 요청 전송 오류: {e}")
    
    def tr_timeout(self, screen_no: str):
        """TR 타임아웃 처리"""
        if screen_no in self.tr_event_loops and self.tr_event_loops[screen_no].isRunning():
            self.logger.warning(f"TR 타임아웃: {screen_no}")
            self.tr_event_loops[screen_no].exit()
    
    def on_receive_tr_data(self, screen_no: str, rq_name: str, tr_code: str, record_name: str, inquiry: str):
        """TR 데이터 수신 처리"""
        try:
            self.logger.debug(f"TR 데이터 수신: {tr_code}")
            
            # 종목코드 추출
            stock_code = self.screen_to_stock.get(screen_no, "")
            
            # 수급 데이터 처리
            if tr_code == TRCode.INVESTOR_NET_VOL:
                data = self.parse_investor_data(tr_code, rq_name)
                data['stock_code'] = stock_code
                self.tr_results[screen_no] = data
                
            # 전일고가 데이터 처리
            elif tr_code == TRCode.DAILY_STOCK:
                data = self.parse_prev_day_high_data(tr_code, rq_name, stock_code)
                data['stock_code'] = stock_code
                self.tr_results[screen_no] = data
                
            # 콜백 함수 호출
            if self.tr_callback:
                self.tr_callback(tr_code, self.tr_results.get(screen_no, {}))
            
            # 이벤트 루프 종료
            if screen_no in self.tr_event_loops and self.tr_event_loops[screen_no].isRunning():
                self.tr_event_loops[screen_no].exit()
                
        except Exception as e:
            self.logger.error(f"TR 데이터 처리 오류: {e}")
    
    def parse_investor_data(self, tr_code: str, rq_name: str) -> Dict:
        """수급 데이터 파싱 (OPT10059)"""
        try:
            investor_data = {}
            
            # rq_name에서 stock_code 추출 (형식: OPT10059_{stock_code}_{timestamp})
            stock_code = rq_name.split('_')[1] if '_' in rq_name else ''
            investor_data['stock_code'] = stock_code
            
            # 멀티 데이터 행 수 확인
            repeat_cnt = self.ocx.dynamicCall("GetRepeatCnt(QString, QString)", tr_code, rq_name)
            self.logger.info(f"📊 [수급파싱시작] TR코드={tr_code}, 종목={stock_code}, 데이터행수={repeat_cnt}")
            
            if repeat_cnt <= 0:
                self.logger.warning(f"⚠️ [수급데이터없음] {stock_code} - 데이터행수=0")
                # 빈 데이터 반환
                for key in ['indiv_net', 'foreign_net', 'inst_net', 'pension_net', 'trust_net', 
                           'insurance_net', 'private_fund_net', 'bank_net', 'state_net', 'other_net', 'prog_net']:
                    investor_data[key] = 0
                return investor_data
            
            # OPT10059 실제 필드명 (키움 공식 문서 기준)
            fields = {
                'indiv_net': '개인투자자',
                'foreign_net': '외국인투자자', 
                'inst_net': '기관계',
                'pension_net': '연기금등',
                'trust_net': '투신',
                'insurance_net': '보험',
                'private_fund_net': '사모펀드',
                'bank_net': '은행',
                'state_net': '국가',
                'other_net': '기타법인',
                'prog_net': '내외국인'  # 참고: 프로그램 매매는 OPT10030에서 조회
            }
            
            # 가장 최신 데이터(index 0) 파싱
            for key, field_name in fields.items():
                try:
                    raw_value = self.ocx.dynamicCall(
                        "GetCommData(QString, QString, int, QString)",
                        tr_code, rq_name, 0, field_name
                    )
                    
                    # 원시값 로깅
                    self.logger.debug(f"🔍 [수급raw] {field_name}: '{raw_value}'")
                    
                    # 데이터 정제 (공백, 콤마, 부호 처리)
                    if raw_value:
                        cleaned_value = raw_value.strip().replace(',', '')
                        # 부호 처리 (+/- 모두 허용)
                        if cleaned_value.startswith('+'):
                            cleaned_value = cleaned_value[1:]
                        try:
                            parsed_value = int(cleaned_value)
                        except ValueError:
                            parsed_value = 0
                            self.logger.warning(f"⚠️ 파싱 실패: {field_name}='{cleaned_value}'")
                    else:
                        parsed_value = 0
                    
                    investor_data[key] = parsed_value
                    
                    # 0이 아닌 값 발견시 강조 로깅
                    if parsed_value != 0:
                        self.logger.info(f"💡 [수급데이터발견] {stock_code} - {key}: {parsed_value:,}")
                        
                except Exception as e:
                    investor_data[key] = 0
                    self.logger.error(f"❌ [수급파싱오류] {key}({field_name}): {e}")
            
            # 총 순매수량 계산
            investor_data['total_net'] = sum([v for k, v in investor_data.items() 
                                              if k not in ['stock_code', 'total_net']])
            
            self.logger.info(f"✅ [수급파싱완료] {stock_code} - 총순매수: {investor_data['total_net']:,}")
            return investor_data
            
        except Exception as e:
            self.logger.error(f"❌ [수급파싱전체오류]: {e}", exc_info=True)
            return {'stock_code': ''}
    
    def get_prev_day_high(self, stock_code: str):
        """전일고가 데이터 요청 (OPT10081 TR 사용)"""
        try:
            inputs = {
                "종목코드": stock_code,
                "기준일자": datetime.now().strftime('%Y%m%d'),
                "수정주가구분": "1"
            }
            
            self.logger.info(f"전일고가 요청: {stock_code}")
            return self.request_tr(TRCode.DAILY_STOCK, inputs)
            
        except Exception as e:
            self.logger.error(f"전일고가 요청 실패 ({stock_code}): {e}")
            return False
    
    def parse_prev_day_high_data(self, tr_code: str, rq_name: str, stock_code: str) -> Dict:
        """전일고가 데이터 파싱 (opt10081)"""
        try:
            # 전일고가 추출
            high_value = self.ocx.dynamicCall(
                "GetCommData(QString, QString, int, QString)",
                tr_code, rq_name, 0, "전일고가"
            ).strip()
            
            if high_value:
                # 쉼표 제거 후 숫자 변환
                prev_high = int(high_value.replace(',', ''))
                self.prev_day_high[stock_code] = prev_high
                self.logger.info(f"전일고가 저장: {stock_code} = {prev_high:,}원")
                return {'prev_day_high': prev_high}
            else:
                self.logger.warning(f"전일고가 데이터 없음: {stock_code}")
                return {'prev_day_high': 0}
                
        except Exception as e:
            self.logger.error(f"전일고가 데이터 파싱 오류: {e}")
            return {'prev_day_high': 0}
    
    def on_receive_msg(self, screen_no: str, rq_name: str, tr_code: str, msg: str):
        """서버 메시지 수신"""
        self.logger.info(f"서버 메시지: {msg}")
    
    # ========================================================================
    # 재연결 및 복구 관리
    # ========================================================================
    
    def check_connection(self):
        """연결 상태 체크 및 자동 재연결"""
        try:
            state = self.ocx.dynamicCall("GetConnectState()")
            if state == 0 and self.connected:
                self.logger.warning("연결이 끊어졌습니다. 재연결 시도...")
                self.connected = False
                self.auto_reconnect()
                
        except Exception as e:
            self.logger.error(f"연결 상태 체크 오류: {e}")
    
    def auto_reconnect(self):
        """자동 재연결"""
        if self.reconnect_count >= KiwoomConfig.MAX_RECONNECT_ATTEMPTS:
            self.logger.error("최대 재연결 시도 횟수 초과")
            return False
            
        self.reconnect_count += 1
        self.logger.info(f"재연결 시도 {self.reconnect_count}/{KiwoomConfig.MAX_RECONNECT_ATTEMPTS}")
        
        # 잠시 대기
        time.sleep(KiwoomConfig.RECONNECT_DELAY)
        
        # 재연결 시도
        if self.connect():
            # 실시간 데이터 재등록
            self.logger.info("재연결 성공. 실시간 데이터 재등록 중...")
            self.register_realdata()
            return True
        else:
            self.logger.error("재연결 실패")
            return False
    
    # ========================================================================
    # 콜백 함수 등록
    # ========================================================================
    
    def set_realdata_callback(self, callback: Callable):
        """실시간 데이터 콜백 함수 설정"""
        self.realdata_callback = callback
        
    def set_tr_callback(self, callback: Callable):
        """TR 데이터 콜백 함수 설정"""
        self.tr_callback = callback
    
    # ========================================================================
    # 상태 조회
    # ========================================================================
    
    def get_status(self) -> Dict:
        """클라이언트 상태 조회"""
        return {
            'connected': self.connected,
            'registered_stocks_count': len(self.registered_stocks),
            'tr_queue_size': self.tr_queue.qsize(),
            'reconnect_count': self.reconnect_count,
            'user_info': self.user_info,
            'account_list': self.account_list
        }

if __name__ == "__main__":
    # 클라이언트 테스트
    import logging
    logging.basicConfig(level=logging.INFO)
    
    client = KiwoomClient()
    
    def test_realdata_callback(stock_code, real_type, data):
        print(f"[실시간] {stock_code} {real_type}: {data.get('current_price', 0)}")
    
    def test_tr_callback(tr_code, data):
        print(f"[TR] {tr_code}: {data}")
    
    client.set_realdata_callback(test_realdata_callback)
    client.set_tr_callback(test_tr_callback)
    
    if client.connect():
        print("[OK] 연결 성공")
        client.register_realdata()
        
        try:
            client.app.exec_()
        except KeyboardInterrupt:
            print("\n종료")
            client.disconnect()
    else:
        print("[FAIL] 연결 실패")

# ============================================================================
# CLAUDE.md 수정사항 - 새로운 클래스들 추가
# ============================================================================

class SimpleTRManager:
    """단순화된 TR 요청 관리 (QTimer 방식)"""
    
    def __init__(self, kiwoom_client):
        self.kiwoom = kiwoom_client
        self.last_opt10059 = {}  # 종목별 마지막 요청 시간만
        self.timers = {}  # 종목별 QTimer 관리
        self.logger = logging.getLogger(__name__)
        
    def can_request(self, stock_code):
        """60초 제한 체크"""
        if stock_code in self.last_opt10059:
            if time.time() - self.last_opt10059[stock_code] < 60:
                return False
        return True
    
    def request_opt10059(self, stock_code):
        """OPT10059 요청 (투자자별 일별 매매동향)"""
        if not self.can_request(stock_code):
            return False
            
        try:
            # OPT10059 입력값 설정 (키움 공식 문서 기준)
            self.kiwoom.ocx.dynamicCall("SetInputValue(QString, QString)", "일자", "")  # 빈값=최근일자
            self.kiwoom.ocx.dynamicCall("SetInputValue(QString, QString)", "종목코드", stock_code)
            self.kiwoom.ocx.dynamicCall("SetInputValue(QString, QString)", "금액수량구분", "2")  # 1=금액, 2=수량
            self.kiwoom.ocx.dynamicCall("SetInputValue(QString, QString)", "매매구분", "0")  # 0=순매수
            self.kiwoom.ocx.dynamicCall("SetInputValue(QString, QString)", "단위구분", "1")  # 1=단위(천주)
            
            self.logger.info(f"📊 [OPT10059 요청] 종목={stock_code}, 수량/순매수/천주단위")
            
            # 요청 실행
            screen_no = f"5959"  # 고정 화면번호 사용
            req_name = f"OPT10059_{stock_code}_{int(time.time())}"
            
            result = self.kiwoom.ocx.dynamicCall(
                "CommRqData(QString, QString, int, QString)",
                req_name, "OPT10059", 0, screen_no
            )
            
            if result == 0:
                self.last_opt10059[stock_code] = time.time()
                self.logger.info(f"✅ OPT10059 요청 성공: {stock_code}")
                return True
            else:
                error_msg = {
                    -200: "시세과부하",
                    -201: "조회전문작성실패",
                    -202: "전문작성초기화실패"
                }.get(result, f"알수없는오류({result})")
                self.logger.error(f"❌ OPT10059 요청 실패: {stock_code} - {error_msg}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ [OPT10059 요청오류] {stock_code}: {e}", exc_info=True)
            return False
    
    def request_with_retry(self, stock_code):
        """에러 시에도 Timer 체인 유지"""
        try:
            if self.can_request(stock_code):
                self.request_opt10059(stock_code)
        except Exception as e:
            self.logger.error(f"TR 실패 {stock_code}: {e}")
        finally:
            # 에러 여부 관계없이 다음 타이머 예약
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(60000, 
                lambda sc=stock_code: self.request_with_retry(sc))
    
    def schedule_next_request(self, stock_code):
        """종목별 60초 타이머 시작"""
        from PyQt5.QtCore import QTimer
        
        if stock_code in self.timers:
            self.timers[stock_code].stop()
            
        timer = QTimer()
        timer.timeout.connect(
            lambda sc=stock_code: self.request_with_retry(sc))
        timer.setSingleShot(True)
        timer.start(60000)  # 60초
        self.timers[stock_code] = timer
    
    def initialize_requests(self, stock_codes):
        """프로그램 시작 시 즉시 TR 요청"""
        from PyQt5.QtCore import QTimer
        
        for i, stock_code in enumerate(stock_codes):
            # 동시 요청 방지를 위한 지연
            QTimer.singleShot(i * 200, 
                lambda sc=stock_code: self.request_opt10059(sc))
            
    def cleanup(self):
        """종료 시 타이머 정리"""
        for timer in self.timers.values():
            timer.stop()


class ConnectionMonitor:
    """QTimer 기반 연결 상태 모니터링"""
    
    def __init__(self, kiwoom_client):
        self.kiwoom = kiwoom_client
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.check_connection)
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self):
        """모니터링 시작"""
        self.monitor_timer.start(10000)  # 10초마다 체크
        self.logger.info("연결 상태 모니터링 시작")
        
    def check_connection(self):
        """연결 상태 체크"""
        try:
            state = self.kiwoom.ocx.dynamicCall("GetConnectState()")
            
            if state == 0:  # 연결 끊김
                self.logger.warning("연결 끊김 감지! 재연결 시도...")
                self.kiwoom.ocx.dynamicCall("CommTerminate()")
                
                # 재로그인
                result = self.kiwoom.ocx.dynamicCall("CommConnect()")
                if result == 0:
                    self.logger.info("재연결 성공")
                    # 실시간 재등록
                    self.re_register_all()
                else:
                    self.logger.error(f"재연결 실패: {result}")
                    
        except Exception as e:
            self.logger.error(f"연결 상태 체크 오류: {e}")
                
    def re_register_all(self):
        """실시간 데이터 재등록"""
        try:
            if hasattr(self.kiwoom, 'register_realdata'):
                self.kiwoom.register_realdata()
                self.logger.info("실시간 데이터 재등록 완료")
        except Exception as e:
            self.logger.error(f"실시간 데이터 재등록 실패: {e}")
                
    def stop_monitoring(self):
        """모니터링 중지"""
        if self.monitor_timer:
            self.monitor_timer.stop()
            self.logger.info("연결 상태 모니터링 중지")