"""
키움 OpenAPI+ 실시간 데이터 수집 시스템 메인 실행
CLAUDE.md 기반 - 틱 기반 데이터 취합, 33개 지표 계산, CSV 저장
"""

import sys
import time
import signal
import logging
from datetime import datetime
from typing import Dict, Any
from PyQt5.QtCore import QTimer

from config import (
    TARGET_STOCKS, KiwoomConfig, DataConfig, TRCode, 
    validate_config
)
from kiwoom_client import KiwoomClient, SimpleTRManager, ConnectionMonitor
from data_processor import DataProcessor, InvestorNetManager
from csv_writer import BatchCSVWriter
from system_monitor import ComprehensiveMonitor
from market_scheduler import MarketScheduler

class KiwoomDataCollector:
    """
    키움 OpenAPI+ 실시간 데이터 수집 시스템 메인 클래스
    
    기능:
    - 키움 API 연결 및 관리
    - 실시간 틱 데이터 수집
    - 33개 지표 실시간 계산
    - CSV 파일 저장
    - 수급 데이터 주기적 업데이트
    """
    
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
        
        # 시스템 모니터링
        self.system_monitor: ComprehensiveMonitor = None
        
        # 장 시작 스케줄러
        self.market_scheduler: MarketScheduler = None
        
        # 통계
        self.start_time = None
        self.tick_counts = {}
        self.last_stats_time = time.time()
        
        self.logger.info("=" * 60)
        self.logger.info("키움 OpenAPI+ 실시간 데이터 수집 시스템")
        self.logger.info("=" * 60)
        self.logger.info(f"대상 종목: {len(self.target_stocks)}개")
        self.logger.info(f"목적: 틱 기반 데이터 취합, 33개 지표 계산, CSV 저장")
    
    def setup_logging(self):
        """로깅 설정"""
        log_filename = f"{DataConfig.LOG_DIR}/main_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=getattr(logging, DataConfig.LOG_LEVEL),
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def initialize_modules(self) -> bool:
        """모든 모듈 초기화"""
        try:
            self.logger.info("모듈 초기화 시작...")
            
            # 1. 키움 클라이언트 초기화
            self.logger.info("1. 키움 클라이언트 초기화")
            self.kiwoom_client = KiwoomClient()
            
            # 2. QTimer 기반 관리자들 초기화
            self.logger.info("2. TR 관리자 초기화")
            self.tr_manager = SimpleTRManager(self.kiwoom_client)
            
            self.logger.info("3. 연결 모니터링 초기화")
            self.connection_monitor = ConnectionMonitor(self.kiwoom_client)
            
            self.logger.info("4. 수급 데이터 관리자 초기화")
            self.investor_manager = InvestorNetManager(self.target_stocks)
            
            # 5. 데이터 프로세서 초기화
            self.logger.info("5. 데이터 프로세서 초기화")
            self.data_processor = DataProcessor(self.target_stocks, self.kiwoom_client)
            
            # 6. CSV 저장소 초기화
            self.logger.info("6. CSV 저장소 초기화")
            self.csv_writer = BatchCSVWriter(
                base_dir=DataConfig.CSV_DIR,
                batch_size=DataConfig.CSV_BATCH_SIZE
            )
            
            # 7. 콜백 함수 연결
            self.logger.info("7. 콜백 함수 연결")
            self.kiwoom_client.set_realdata_callback(self.on_realdata_received)
            self.kiwoom_client.set_tr_callback(self.on_tr_data_received)
            self.data_processor.set_indicator_callback(self.on_indicators_calculated)
            
            # 8. TR 관리자와 수급 관리자 연동 (콜백 대신 직접 참조)
            self.tr_manager.investor_manager = self.investor_manager
            
            # 8.1. IndicatorCalculator와 InvestorNetManager 연동 (수급 지표 0 문제 해결)
            for stock_code in self.target_stocks:
                self.data_processor.calculators[stock_code].investor_manager = self.investor_manager
            
            # 9. 시스템 모니터링 초기화
            self.logger.info("9. 시스템 모니터링 초기화")
            self.system_monitor = ComprehensiveMonitor(
                kiwoom_client=self.kiwoom_client,
                csv_dir=DataConfig.CSV_DIR
            )
            
            # 10. 장 시작 스케줄러 초기화
            self.logger.info("10. 장 시작 스케줄러 초기화")
            self.market_scheduler = MarketScheduler(self.kiwoom_client)
            self.market_scheduler.reconnect_signal.connect(self.on_reconnected)
            self.market_scheduler.market_open_signal.connect(self.on_market_open)
            self.market_scheduler.market_close_signal.connect(self.on_market_close)
            
            # 10. 통계 초기화
            for stock_code in self.target_stocks:
                self.tick_counts[stock_code] = 0
            
            self.logger.info("모든 모듈 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"모듈 초기화 실패: {e}")
            return False
    
    def connect_and_register(self) -> bool:
        """키움 연결 및 실시간 데이터 등록"""
        try:
            # 수동 로그인만 사용
            self.logger.info("💡 수동 로그인 - 로그인 창에서 직접 입력하세요.")
            
            # 키움 서버 연결 (자동 로그인 활성화)
            self.logger.info("키움 서버 연결 시도...")
            # use_auto_login=True로 바꾸면 자동 로그인 사용
            if not self.kiwoom_client.connect(use_auto_login=True):  # False=수동, True=자동
                self.logger.error("키움 서버 연결 실패")
                return False
            
            # 실시간 데이터 등록
            self.logger.info("실시간 데이터 등록...")
            if not self.kiwoom_client.register_realdata(self.target_stocks):
                self.logger.error("실시간 데이터 등록 실패")
                return False
            
            # 수급 데이터 TR 스케줄링 시작 (즉시 첫 요청)
            self.logger.info("수급 데이터 TR 스케줄링 시작...")
            for i, stock_code in enumerate(self.target_stocks):
                # 0.2초씩 지연하여 순차 요청
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(i * 200, lambda sc=stock_code: self.tr_manager.request_opt10059(sc))
            
            # 연결 모니터링 시작 (자동 재시작 시스템)
            self.logger.info("연결 모니터링 시작...")
            self.start_connection_monitor()
            
            # 시스템 모니터링 시작
            self.logger.info("시스템 모니터링 시작...")
            self.system_monitor.start_monitoring()
            
            self.logger.info("연결 및 등록 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"연결 및 등록 실패: {e}")
            return False
    
    
    
    # ========================================================================
    # 자동 재시작 시스템
    # ========================================================================
    
    def start_connection_monitor(self):
        """연결 상태 모니터링 시작 (자동 재시작)"""
        from PyQt5.QtCore import QTimer
        
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_connection_status)
        self.connection_timer.start(10000)  # 10초마다 체크
        self.logger.info("자동 재시작 시스템 활성화")
    
    def check_connection_status(self):
        """연결 상태 확인"""
        try:
            state = self.kiwoom_client.ocx.dynamicCall("GetConnectState()")
            
            if state == 0:  # 연결 끊김
                self.logger.error("🔴 연결 끊김 감지! 자동 재시작을 위해 프로그램을 종료합니다...")
                
                # 안전한 종료
                import sys
                self.connection_timer.stop()
                
                # 3초 후 종료 (재시작용 exit code)
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(3000, lambda: sys.exit(1))
                
        except Exception as e:
            self.logger.error(f"연결 상태 확인 실패: {e}")
            # 심각한 오류시에도 재시작
            import sys
            QTimer.singleShot(2000, lambda: sys.exit(1))
    
    # ========================================================================
    # 콜백 함수들
    # ========================================================================
    
    def on_realdata_received(self, stock_code: str, real_type: str, tick_data: Dict):
        """실시간 데이터 수신 콜백 (크래시 방지 강화)"""
        try:
            # 데이터 수신 로그 (처음 10틱만)
            if self.tick_counts.get(stock_code, 0) < 10:
                self.logger.info(f"[실시간데이터수신] {stock_code} - {real_type} - 가격: {tick_data.get('current_price', 'N/A')}")
            
            # 시스템 모니터링에 데이터 수신 알림
            if self.system_monitor:
                self.system_monitor.on_realdata_received(stock_code)
            
            # 데이터 프로세서로 전달
            self.data_processor.process_realdata(stock_code, real_type, tick_data)
            
            # 통계 업데이트
            self.tick_counts[stock_code] = self.tick_counts.get(stock_code, 0) + 1
            
        except Exception as e:
            self.logger.error(f"💥 실시간 데이터 처리 오류: {e}")
            import traceback
            self.logger.error(f"스택트레이스: {traceback.format_exc()}")
            
            # 크리티컬 에러 시 시스템 모니터에 알림
            if self.system_monitor:
                try:
                    self.system_monitor.crash_detector.crash_detected.emit('realdata_exception', {
                        'stock_code': stock_code,
                        'real_type': real_type,
                        'exception': str(e),
                        'traceback': traceback.format_exc()
                    })
                except:
                    pass
    
    def on_tr_data_received(self, tr_code: str, tr_data: Dict):
        """TR 데이터 수신 콜백"""
        try:
            # TR Manager로 전달하여 수급 데이터 처리
            if tr_code == TRCode.INVESTOR_NET_VOL:
                stock_code = tr_data.get('stock_code', '')
                self.investor_manager.update_from_tr(stock_code, tr_data)
                self.logger.info(f"[수급TR처리완료] {stock_code}")
            
            # 기타 TR 데이터는 데이터 프로세서로
            self.data_processor.process_tr_data(tr_code, tr_data)
            
            self.logger.debug(f"TR 데이터 처리 완료: {tr_code}")
            
        except Exception as e:
            self.logger.error(f"TR 데이터 처리 오류: {e}")
    
    def on_indicators_calculated(self, stock_code: str, indicators: Dict):
        """33개 지표 계산 완료 콜백"""
        try:
            # 콜백 호출 로그 (처음 5틱만)
            if self.tick_counts.get(stock_code, 0) <= 5:
                self.logger.info(f"[지표계산완료] {stock_code} - 지표개수: {len(indicators)} - 가격: {indicators.get('current_price', 'N/A')}")
            
            # CSV에 저장
            if self.csv_writer:
                success = self.csv_writer.write_indicators(stock_code, indicators)
                if self.tick_counts.get(stock_code, 0) <= 5:
                    self.logger.info(f"[CSV저장결과] {stock_code} - {'성공' if success else '실패'}")
            else:
                self.logger.warning("CSV writer가 None입니다!")
            
            # 주요 지표 로깅 (100틱마다)
            if self.tick_counts.get(stock_code, 0) % 100 == 0:
                self.logger.info(
                    f"[{stock_code}] 틱#{self.tick_counts[stock_code]} - "
                    f"가격:{indicators.get('current_price', 0):,.0f} "
                    f"MA5:{indicators.get('ma5', 0):.1f} "
                    f"RSI:{indicators.get('rsi14', 0):.1f} "
                    f"스프레드:{indicators.get('spread', 0):.0f}"
                )
            
        except Exception as e:
            self.logger.error(f"지표 저장 오류: {e}")
            import traceback
            self.logger.error(f"상세 오류: {traceback.format_exc()}")
    
    # ========================================================================
    # 실행 관리
    # ========================================================================
    
    def run(self):
        """메인 실행"""
        try:
            # 설정 검증
            if not validate_config():
                self.logger.error("설정 검증 실패")
                return False
            
            # 모듈 초기화
            if not self.initialize_modules():
                self.logger.error("모듈 초기화 실패")
                return False
            
            # 연결 및 등록
            if not self.connect_and_register():
                self.logger.error("연결 및 등록 실패")
                return False
            
            
            # 시그널 핸들러 설정
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # 실행 시작
            self.running = True
            self.start_time = time.time()
            
            self.logger.info("=" * 60)
            self.logger.info("실시간 데이터 수집 시작!")
            self.logger.info("Ctrl+C로 안전하게 종료할 수 있습니다.")
            self.logger.info("=" * 60)
            
            # 주기적 상태 리포트 시작
            self.start_status_reporting()
            
            # 이벤트 루프 실행
            if self.kiwoom_client and self.kiwoom_client.app:
                return self.kiwoom_client.app.exec_()
            else:
                self.logger.error("QApplication이 초기화되지 않음")
                return False
                
        except Exception as e:
            self.logger.error(f"실행 중 오류: {e}")
            return False
        finally:
            self.cleanup()
    
    def start_status_reporting(self):
        """주기적 상태 리포트 시작"""
        try:
            status_timer = QTimer()
            status_timer.timeout.connect(self.print_status_report)
            status_timer.start(60000)  # 1분마다
            
        except Exception as e:
            self.logger.error(f"상태 리포트 시작 실패: {e}")
    
    def print_status_report(self):
        """상태 리포트 출력"""
        try:
            current_time = time.time()
            running_time = current_time - self.start_time if self.start_time else 0
            
            # 틱 통계
            total_ticks = sum(self.tick_counts.values())
            ticks_per_minute = total_ticks / (running_time / 60) if running_time > 0 else 0
            
            self.logger.info("=" * 50)
            self.logger.info("상태 리포트")
            self.logger.info("=" * 50)
            self.logger.info(f"실행 시간: {running_time / 60:.1f}분")
            self.logger.info(f"총 틱 수: {total_ticks:,} (분당 {ticks_per_minute:.1f}틱)")
            
            # 종목별 틱 수
            for stock_code, count in self.tick_counts.items():
                self.logger.info(f"  {stock_code}: {count:,}틱")
            
            # CSV 통계
            if self.csv_writer:
                csv_stats = self.csv_writer.get_statistics()
                self.logger.info(f"CSV 저장: {csv_stats['total_writes']:,}행")
                if csv_stats['total_errors'] > 0:
                    self.logger.warning(f"CSV 오류: {csv_stats['total_errors']}건")
            
            # 클라이언트 상태
            if self.kiwoom_client:
                client_status = self.kiwoom_client.get_status()
                self.logger.info(f"연결 상태: {'연결' if client_status['connected'] else '끊김'}")
                self.logger.info(f"등록 종목: {client_status['registered_stocks_count']}개")
                if client_status['tr_queue_size'] > 0:
                    self.logger.info(f"TR 큐: {client_status['tr_queue_size']}개 대기")
            
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.error(f"상태 리포트 오류: {e}")
    
    def on_reconnected(self):
        """재연결 성공 시 콜백"""
        try:
            self.logger.info("🔄 재연결 성공 - 실시간 데이터 재등록")
            # 실시간 데이터 재등록
            self.kiwoom_client.register_realdata(self.target_stocks)
            # TR 매니저 재시작
            if self.tr_manager:
                self.tr_manager.start_scheduler()
        except Exception as e:
            self.logger.error(f"재연결 처리 오류: {e}")
    
    def on_market_open(self):
        """정규장 시작 시 콜백 (9:00)"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            self.logger.info("=" * 60)
            self.logger.info(f"🔔 [{current_time}] 정규장 시작!")
            self.logger.info("데이터 수집 시간: 9:00 ~ 15:20")
            self.logger.info("=" * 60)
            
            # 통계 초기화
            self.start_time = time.time()
            for stock_code in self.target_stocks:
                self.tick_counts[stock_code] = 0
            
            # 연결 상태 확인 후 실시간 등록
            if self.kiwoom_client.GetConnectState():
                self.logger.info("실시간 데이터 등록 시작")
                self.kiwoom_client.register_realdata(self.target_stocks)
                
                # TR 매니저 시작
                if self.tr_manager:
                    self.tr_manager.start_scheduler()
            else:
                self.logger.warning("연결 끊김 - 재연결 필요")
                self.market_scheduler.start_reconnect()
        except Exception as e:
            self.logger.error(f"장 시작 처리 오류: {e}")
    
    def on_market_close(self):
        """정규장 마감 시 콜백 (15:20)"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            self.logger.info("=" * 60)
            self.logger.info(f"🔕 [{current_time}] 정규장 마감!")
            self.logger.info("실시간 데이터 수집 중지")
            self.logger.info("=" * 60)
            
            # 실시간 등록 해제
            if self.kiwoom_client:
                self.logger.info("실시간 데이터 등록 해제")
                # 모든 종목 실시간 해제
                for stock_code in self.target_stocks:
                    self.kiwoom_client.DisconnectRealData(KiwoomConfig.SCREEN_NO_REALTIME)
                
                # TR 매니저 중지
                if self.tr_manager:
                    self.tr_manager.stop_scheduler()
            
            # CSV 버퍼 플러시
            if self.csv_writer:
                self.logger.info("CSV 버퍼 모두 저장")
                self.csv_writer.flush_all_buffers()
            
            # 오늘 통계 출력
            if self.start_time:
                total_time = time.time() - self.start_time
                total_ticks = sum(self.tick_counts.values())
                
                self.logger.info("=" * 50)
                self.logger.info("오늘 수집 통계")
                self.logger.info("=" * 50)
                self.logger.info(f"수집 시간: {total_time / 60:.1f}분")
                self.logger.info(f"총 틱 수: {total_ticks:,}개")
                if total_time > 0:
                    self.logger.info(f"평균 틱/분: {total_ticks / (total_time / 60):.1f}")
                
                for stock_code, count in sorted(self.tick_counts.items()):
                    self.logger.info(f"  {stock_code}: {count:,}틱")
                    
            self.logger.info("=" * 50)
            self.logger.info("다음 거래일 9:00까지 대기")
            self.logger.info("시간외 거래 데이터는 수집하지 않습니다")
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.error(f"장 마감 처리 오류: {e}")
    
    def signal_handler(self, signum, frame):
        """시그널 핸들러 (Ctrl+C 등)"""
        self.logger.info(f"\n시그널 수신: {signum}")
        self.logger.info("안전하게 종료 중...")
        self.stop()
    
    def stop(self):
        """데이터 수집 중단"""
        self.running = False
        if self.kiwoom_client and self.kiwoom_client.app:
            self.kiwoom_client.app.quit()
    
    def cleanup(self):
        """리소스 정리"""
        try:
            self.logger.info("시스템 종료 중...")
            
            # 모든 버퍼 플러시
            if self.csv_writer:
                self.logger.info("CSV 버퍼 플러시...")
                self.csv_writer.flush_all_buffers()
                self.csv_writer.close_all()
            
            # 스케줄러 정리
            if self.market_scheduler:
                self.logger.info("장 시작 스케줄러 종료...")
                self.market_scheduler.cleanup()
            
            # 시스템 모니터링 종료
            if self.system_monitor:
                self.logger.info("시스템 모니터링 종료...")
                self.system_monitor.stop_monitoring()
            
            # 키움 연결 종료
            if self.kiwoom_client:
                self.logger.info("키움 연결 종료...")
                self.kiwoom_client.disconnect()
            
            # 최종 통계
            if self.start_time:
                total_time = time.time() - self.start_time
                total_ticks = sum(self.tick_counts.values())
                
                self.logger.info("=" * 60)
                self.logger.info("최종 통계")
                self.logger.info("=" * 60)
                self.logger.info(f"총 실행 시간: {total_time / 60:.1f}분")
                self.logger.info(f"총 수집 틱: {total_ticks:,}개")
                self.logger.info(f"평균 틱/분: {total_ticks / (total_time / 60):.1f}")
                
                for stock_code, count in self.tick_counts.items():
                    self.logger.info(f"  {stock_code}: {count:,}틱")
                
                if self.csv_writer:
                    csv_stats = self.csv_writer.get_statistics()
                    self.logger.info(f"CSV 저장: {csv_stats['total_writes']:,}행")
            
            self.logger.info("시스템 종료 완료")
            
        except Exception as e:
            self.logger.error(f"종료 중 오류: {e}")

def main():
    """메인 실행 함수"""
    print("키움 OpenAPI+ 실시간 데이터 수집 시스템")
    print("CLAUDE.md 기반 - 틱 기반 데이터 취합, 33개 지표 계산, CSV 저장")
    print("=" * 60)
    
    # 대상 종목 출력
    print(f"대상 종목 ({len(TARGET_STOCKS)}개):")
    for i, stock_code in enumerate(TARGET_STOCKS, 1):
        print(f"  {i:2d}. {stock_code}")
    print()
    
    # 수집기 생성 및 실행
    collector = KiwoomDataCollector(TARGET_STOCKS)
    
    try:
        success = collector.run()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
        return 0
    except Exception as e:
        print(f"실행 중 오류: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())