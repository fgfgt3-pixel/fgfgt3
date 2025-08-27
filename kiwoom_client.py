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
    TARGET_STOCKS, KiwoomConfig, DataConfig, RealDataFID, TRCode
)

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
    
    def connect(self) -> bool:
        """키움 서버 연결"""
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
            
            success_count = 0
            for idx, group in enumerate(screen_groups):
                screen_no = f"{KiwoomConfig.SCREEN_NO_REALTIME}{idx:02d}"
                
                # 주식체결 등록
                stock_codes = ";".join(group)
                self.logger.info(f"실시간 등록 상세: 화면={screen_no}, 종목={stock_codes}, FID={RealDataFID.QUOTE_FID_LIST}")
                ret1 = self.ocx.dynamicCall(
                    "SetRealReg(QString, QString, QString, QString)",
                    screen_no, stock_codes, RealDataFID.QUOTE_FID_LIST, "1"
                )
                self.logger.info(f"주식체결 등록 결과: {ret1}")
                
                # 주식호가 등록  
                hoga_screen = f"{screen_no}_HOGA"
                self.logger.info(f"호가 등록 상세: 화면={hoga_screen}, 종목={stock_codes}, FID={RealDataFID.HOGA_FID_LIST}")
                ret2 = self.ocx.dynamicCall(
                    "SetRealReg(QString, QString, QString, QString)",
                    hoga_screen, stock_codes, RealDataFID.HOGA_FID_LIST, "1"
                )
                self.logger.info(f"주식호가 등록 결과: {ret2}")
                
                if ret1 == 0 and ret2 == 0:
                    self.screen_numbers[screen_no] = group
                    self.registered_stocks.update(group)
                    success_count += len(group)
                    self.logger.info(f"실시간 등록 성공: 화면 {screen_no}, 종목 {len(group)}개")
                else:
                    self.logger.error(f"실시간 등록 실패: 화면 {screen_no}, ret1={ret1}, ret2={ret2}")
            
            self.logger.info(f"전체 실시간 등록: {success_count}/{len(stocks)} 성공")
            return success_count == len(stocks)
            
        except Exception as e:
            self.logger.error(f"실시간 등록 중 예외: {e}")
            return False
    
    def on_receive_real_data(self, stock_code: str, real_type: str, real_data: str):
        """실시간 데이터 수신 처리"""
        try:
            # 실시간 데이터 수신 확인 로그 (중요!)
            self.logger.info(f"[실시간] {stock_code} {real_type} 데이터 수신")
            
            # 모든 실시간 타입을 일단 받아보기
            if real_type not in ["주식체결", "주식호가"]:
                self.logger.warning(f"[실시간] 예상외 타입 수신: {real_type}")
            
            # 현재 시간을 HHMMSS.mmm 형식으로 생성 (시:분:초.밀리초)
            from datetime import datetime
            now = datetime.now()
            current_time = now.strftime("%H%M%S.%f")[:-3]  # HHMMSS.mmm
            
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
                        
            elif real_type == "주식호가":
                # 호가 데이터 추출
                for field, fid in RealDataFID.STOCK_HOGA.items():
                    try:
                        value = self.ocx.dynamicCall("GetCommRealData(QString, int)", stock_code, fid)
                        data[field] = self.parse_real_value(value, field)
                    except Exception as ex:
                        self.logger.debug(f"호가 FID {fid} 추출 오류: {ex}")
                        data[field] = 0
                
                # 매수1호가 로그
                bid1 = data.get('bid1_price', 0)
                if bid1 > 0:
                    self.logger.info(f"[호가] {stock_code}: 매수1호가 {bid1:,}원")
            else:
                self.logger.warning(f"알 수 없는 실시간 타입: {real_type}")
            
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
            
            # 수급 데이터 처리
            if tr_code == TRCode.INVESTOR_NET_VOL:
                data = self.parse_investor_data(tr_code, rq_name)
                data['stock_code'] = self.screen_to_stock.get(screen_no, "")  # 매핑에서 종목코드 추출
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
            
            # 투자주체별 순매수 데이터 추출
            fields = {
                'indiv_net': '개인',
                'foreign_net': '외국인',
                'inst_net': '기관',
                'pension_net': '연기금',
                'trust_net': '투신',
                'insurance_net': '보험', 
                'private_fund_net': '사모펀드',
                'bank_net': '은행',
                'state_net': '국가',
                'other_net': '기타법인',
                'prog_net': '프로그램'
            }
            
            for key, field_name in fields.items():
                try:
                    value = self.ocx.dynamicCall(
                        "GetCommData(QString, QString, int, QString)",
                        tr_code, rq_name, 0, field_name
                    ).strip()
                    investor_data[key] = int(value) if value else 0
                except:
                    investor_data[key] = 0
            
            # 총 순매수량 계산
            investor_data['total_net'] = sum(investor_data.values())
            
            return investor_data
            
        except Exception as e:
            self.logger.error(f"수급 데이터 파싱 오류: {e}")
            return {}
    
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