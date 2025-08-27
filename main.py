"""
키움 OpenAPI+ 실시간 데이터 수집 시스템 메인 실행
CLAUDE.md 기반 - 틱 기반 데이터 취합, 33개 지표 계산, CSV 저장
"""

import sys
import time
import signal
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

from config import (
    TARGET_STOCKS, KiwoomConfig, DataConfig, TRCode, 
    validate_config
)
from kiwoom_client import KiwoomClient
from data_processor import DataProcessor
from csv_writer import BatchCSVWriter

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
        
        # 통계
        self.start_time = None
        self.tick_counts = {}
        self.last_stats_time = time.time()
        
        # 수급 데이터 업데이트 관리
        self.investor_update_timer = None
        self.last_investor_update = {}
        
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
            
            # 2. 데이터 프로세서 초기화
            self.logger.info("2. 데이터 프로세서 초기화")
            self.data_processor = DataProcessor(self.target_stocks, self.kiwoom_client)
            
            # 3. CSV 저장소 초기화
            self.logger.info("3. CSV 저장소 초기화")
            self.csv_writer = BatchCSVWriter(
                base_dir=DataConfig.CSV_DIR,
                batch_size=50  # 50틱마다 배치 저장
            )
            
            # 4. 콜백 함수 연결
            self.logger.info("4. 콜백 함수 연결")
            self.kiwoom_client.set_realdata_callback(self.on_realdata_received)
            self.kiwoom_client.set_tr_callback(self.on_tr_data_received)
            self.data_processor.set_indicator_callback(self.on_indicators_calculated)
            
            # 5. 통계 초기화
            for stock_code in self.target_stocks:
                self.tick_counts[stock_code] = 0
                self.last_investor_update[stock_code] = 0
            
            self.logger.info("모든 모듈 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"모듈 초기화 실패: {e}")
            return False
    
    def connect_and_register(self) -> bool:
        """키움 연결 및 실시간 데이터 등록"""
        try:
            # 키움 서버 연결
            self.logger.info("키움 서버 연결 시도...")
            if not self.kiwoom_client.connect():
                self.logger.error("키움 서버 연결 실패")
                return False
            
            # 실시간 데이터 등록
            self.logger.info("실시간 데이터 등록...")
            if not self.kiwoom_client.register_realdata(self.target_stocks):
                self.logger.error("실시간 데이터 등록 실패")
                return False
            
            # 전일고가 데이터 초기 요청
            self.logger.info("전일고가 데이터 요청...")
            self.request_initial_data()
            
            self.logger.info("연결 및 등록 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"연결 및 등록 실패: {e}")
            return False
    
    def start_investor_data_updates(self):
        """수급 데이터 주기적 업데이트 시작"""
        try:
            from PyQt5.QtCore import QTimer
            
            self.investor_update_timer = QTimer()
            self.investor_update_timer.timeout.connect(self.update_investor_data)
            self.investor_update_timer.start(DataConfig.INVESTOR_UPDATE_INTERVAL * 1000)  # 밀리초 단위
            
            self.logger.info(f"수급 데이터 업데이트 시작: {DataConfig.INVESTOR_UPDATE_INTERVAL}초 간격")
            
        except Exception as e:
            self.logger.error(f"수급 데이터 업데이트 시작 실패: {e}")
    
    def update_investor_data(self):
        """수급 데이터 업데이트 (OPT10059 TR 요청)"""
        try:
            current_time = time.time()
            today = datetime.now().strftime("%Y%m%d")
            
            for stock_code in self.target_stocks:
                # 중복 요청 방지 (1분 이내 재요청 금지)
                if current_time - self.last_investor_update[stock_code] < 60:
                    continue
                
                # TR 요청
                tr_inputs = {
                    "종목코드": stock_code,
                    "기준일자": today,
                    "수정주가구분": "1"
                }
                
                if self.kiwoom_client.request_tr(TRCode.INVESTOR_NET_VOL, tr_inputs):
                    self.last_investor_update[stock_code] = current_time
                    self.logger.debug(f"수급 데이터 요청: {stock_code}")
                
                # API 제한 방지 (asyncio 대신 time.sleep 사용)
                time.sleep(0.2)
                
        except Exception as e:
            self.logger.error(f"수급 데이터 업데이트 오류: {e}")
    
    def request_initial_data(self):
        """초기 데이터 요청"""
        try:
            # 초기 데이터 요청이 필요한 경우 여기에 추가
            self.logger.info(f"초기 데이터 요청 완료 - 대상 종목: {len(self.target_stocks)}개")
                
        except Exception as e:
            self.logger.error(f"초기 데이터 요청 오류: {e}")
    
    # ========================================================================
    # 콜백 함수들
    # ========================================================================
    
    def on_realdata_received(self, stock_code: str, real_type: str, tick_data: Dict):
        """실시간 데이터 수신 콜백"""
        try:
            # 데이터 수신 로그 (처음 10틱만)
            if self.tick_counts.get(stock_code, 0) < 10:
                self.logger.info(f"[실시간데이터수신] {stock_code} - {real_type} - 가격: {tick_data.get('current_price', 'N/A')}")
            
            # 데이터 프로세서로 전달
            self.data_processor.process_realdata(stock_code, real_type, tick_data)
            
            # 통계 업데이트
            self.tick_counts[stock_code] = self.tick_counts.get(stock_code, 0) + 1
            
        except Exception as e:
            self.logger.error(f"실시간 데이터 처리 오류: {e}")
    
    def on_tr_data_received(self, tr_code: str, tr_data: Dict):
        """TR 데이터 수신 콜백"""
        try:
            # 데이터 프로세서로 전달
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
            
            # 수급 데이터 업데이트 시작
            self.start_investor_data_updates()
            
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
            
            # 수급 데이터 주기적 업데이트 시작
            self.start_investor_data_updates()
            
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
            from PyQt5.QtCore import QTimer
            
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