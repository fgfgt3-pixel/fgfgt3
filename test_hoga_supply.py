"""
호가/수급 데이터 수신 테스트
문제 진단: 왜 호가와 수급 데이터가 모두 0인가?
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop, QTimer
import time
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class HogaSupplyTester(QAxWidget):
    def __init__(self):
        super().__init__()
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
        
        # 이벤트 연결
        self.OnEventConnect.connect(self.on_event_connect)
        self.OnReceiveRealData.connect(self.on_receive_real_data)
        self.OnReceiveTrData.connect(self.on_receive_tr_data)
        
        self.connected = False
        self.login_loop = QEventLoop()
        
        # 테스트 결과
        self.hoga_received = False
        self.supply_received = False
        
        logger.info("키움 API 테스터 초기화 완료")
    
    def on_event_connect(self, err_code):
        if err_code == 0:
            logger.info("✅ 키움 로그인 성공")
            self.connected = True
        else:
            logger.error(f"❌ 키움 로그인 실패: {err_code}")
        
        self.login_loop.exit()
    
    def connect_and_test(self):
        """연결 및 테스트 실행"""
        try:
            # 1. 로그인
            logger.info("1. 키움 로그인 시도...")
            result = self.dynamicCall("CommConnect()")
            if result != 0:
                logger.error(f"CommConnect 실패: {result}")
                return False
                
            self.login_loop.exec_()
            
            if not self.connected:
                logger.error("로그인 실패")
                return False
            
            # 2. 호가 데이터 등록 테스트
            logger.info("\\n2. 호가 데이터 등록 테스트...")
            self.test_hoga_registration()
            
            # 3. 수급 데이터 TR 테스트
            logger.info("\\n3. 수급 데이터 TR 테스트...")
            self.test_supply_tr()
            
            # 4. 10초간 실시간 데이터 대기
            logger.info("\\n4. 10초간 실시간 데이터 수신 대기...")
            QTimer.singleShot(10000, self.finish_test)
            
            return True
            
        except Exception as e:
            logger.error(f"테스트 실행 오류: {e}")
            return False
    
    def test_hoga_registration(self):
        """호가 데이터 등록 테스트"""
        try:
            # 다양한 FID 조합 테스트
            fid_combinations = [
                ("기본체결", "10;11;12;13;14;15;20"),
                ("호가가격", "27;28"),
                ("호가가격확장", "41;42;43;44;45;51;52;53;54;55"),
                ("호가잔량", "61;62;63;64;65;71;72;73;74;75"),
                ("전체호가", "41;42;43;44;45;51;52;53;54;55;61;62;63;64;65;71;72;73;74;75")
            ]
            
            for i, (name, fid_list) in enumerate(fid_combinations):
                screen_no = f"100{i}"
                logger.info(f"  {name} FID 등록: {fid_list}")
                
                result = self.dynamicCall(
                    "SetRealReg(QString, QString, QString, QString)",
                    screen_no, "005930", fid_list, "0"
                )
                
                if result == 0:
                    logger.info(f"  ✅ {name} 등록 성공")
                else:
                    logger.error(f"  ❌ {name} 등록 실패: {result}")
                    
                time.sleep(0.1)  # API 제한 방지
                
        except Exception as e:
            logger.error(f"호가 등록 오류: {e}")
    
    def test_supply_tr(self):
        """수급 데이터 TR 테스트"""
        try:
            # OPT10059 요청
            self.dynamicCall("SetInputValue(QString, QString)", "종목코드", "005930")
            self.dynamicCall("SetInputValue(QString, QString)", "기준일자", datetime.now().strftime("%Y%m%d"))
            self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
            
            result = self.dynamicCall(
                "CommRqData(QString, QString, int, QString)",
                "수급테스트", "opt10059", 0, "5959"
            )
            
            if result == 0:
                logger.info("  ✅ OPT10059 요청 성공")
            else:
                logger.error(f"  ❌ OPT10059 요청 실패: {result}")
                
        except Exception as e:
            logger.error(f"수급 TR 오류: {e}")
    
    def on_receive_real_data(self, stock_code, real_type, real_data):
        """실시간 데이터 수신"""
        try:
            logger.info(f"📊 실시간 데이터: {stock_code} - {real_type}")
            
            # 체결 데이터 확인
            if real_type in ["주식체결"]:
                current_price = self.get_comm_real_data(stock_code, 10)
                logger.info(f"  현재가: {current_price}")
            
            # 호가 데이터 확인  
            elif real_type in ["주식호가", "주식호가잔량"]:
                self.hoga_received = True
                logger.info("  🎯 호가 데이터 수신됨!")
                
                # 주요 호가 FID 확인
                test_fids = [41, 51, 61, 71]  # ask1, bid1, ask1_qty, bid1_qty
                for fid in test_fids:
                    try:
                        value = self.get_comm_real_data(stock_code, fid)
                        logger.info(f"    FID {fid}: {value}")
                    except:
                        logger.info(f"    FID {fid}: 읽기 실패")
            
        except Exception as e:
            logger.error(f"실시간 데이터 처리 오류: {e}")
    
    def on_receive_tr_data(self, screen_no, rq_name, tr_code, record_name, inquiry):
        """TR 데이터 수신"""
        try:
            logger.info(f"📋 TR 응답: {tr_code} - {rq_name}")
            
            if tr_code == "opt10059":
                self.supply_received = True
                logger.info("  🎯 수급 데이터 응답됨!")
                
                # 다양한 필드명으로 테스트
                test_fields = ["개인", "외국인", "기관", "연기금", "투신", "보험", "사모펀드"]
                for field in test_fields:
                    try:
                        value = self.dynamicCall(
                            "GetCommData(QString, QString, int, QString)",
                            tr_code, rq_name, 0, field
                        ).strip()
                        logger.info(f"    {field}: '{value}'")
                    except:
                        logger.info(f"    {field}: 읽기 실패")
            
        except Exception as e:
            logger.error(f"TR 데이터 처리 오류: {e}")
    
    def get_comm_real_data(self, stock_code, fid):
        """실시간 데이터 추출"""
        return self.dynamicCall("GetCommRealData(QString, int)", stock_code, fid).strip()
    
    def finish_test(self):
        """테스트 종료"""
        logger.info("\\n" + "="*50)
        logger.info("📊 테스트 결과 요약")
        logger.info("="*50)
        logger.info(f"호가 데이터 수신: {'✅ 성공' if self.hoga_received else '❌ 실패'}")
        logger.info(f"수급 데이터 수신: {'✅ 성공' if self.supply_received else '❌ 실패'}")
        
        if not self.hoga_received:
            logger.warning("⚠️  호가 데이터 미수신: FID 등록 또는 실시간 타입 문제")
        
        if not self.supply_received:
            logger.warning("⚠️  수급 데이터 미수신: OPT10059 응답 또는 파싱 문제")
        
        logger.info("테스트 완료. 프로그램을 종료합니다.")
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    tester = HogaSupplyTester()
    
    try:
        if tester.connect_and_test():
            app.exec_()
        else:
            logger.error("테스트 실행 실패")
            
    except Exception as e:
        logger.error(f"메인 실행 오류: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())