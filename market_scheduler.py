"""
장 시작 스케줄러 및 자동 재연결 관리
오전 7시 실행 → 9시 장 시작까지 안정적 대기
"""

import time
from datetime import datetime, timedelta
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
import logging
import ctypes
import sys

logger = logging.getLogger(__name__)

class MarketScheduler(QObject):
    """장 시작 대기 및 자동 재연결 관리"""
    
    reconnect_signal = pyqtSignal()
    market_open_signal = pyqtSignal()
    market_close_signal = pyqtSignal()  # 장 마감 신호 추가
    
    def __init__(self, kiwoom_client):
        super().__init__()
        self.kiwoom = kiwoom_client
        self.reconnect_timer = QTimer()
        self.heartbeat_timer = QTimer()
        self.market_wait_timer = QTimer()
        
        # 재연결 설정
        self.max_reconnect_attempts = 10
        self.reconnect_count = 0
        self.last_reconnect_time = None
        
        # 정규장 시간 설정 (9:00 ~ 15:20)
        self.market_open_time = "09:00:00"
        self.market_close_time = "15:20:00"
        self.is_market_open = False
        
        # Windows 절전 방지
        self.prevent_sleep()
        
        self.setup_timers()
        
    def setup_timers(self):
        """타이머 설정"""
        # 5분마다 연결 상태 체크
        self.heartbeat_timer.timeout.connect(self.check_connection)
        self.heartbeat_timer.start(300000)  # 5분
        
        # 재연결 타이머 (필요시 활성화)
        self.reconnect_timer.timeout.connect(self.attempt_reconnect)
        
        # 장 시작 체크 (1분마다)
        self.market_wait_timer.timeout.connect(self.check_market_time)
        self.market_wait_timer.start(60000)  # 1분
        
    def prevent_sleep(self):
        """Windows 절전 모드 방지"""
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            logger.info("Windows 절전 모드 방지 활성화")
        except Exception as e:
            logger.warning(f"절전 모드 방지 설정 실패: {e}")
    
    def check_connection(self):
        """연결 상태 체크 및 유지"""
        try:
            # 연결 상태 확인
            if not self.kiwoom.GetConnectState():
                logger.warning("연결 끊김 감지 - 재연결 시도")
                self.start_reconnect()
                return
                
            # 현재 시간 체크
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            
            # 서버 점검 시간 회피 (5:00-6:30)
            if "05:00" <= current_time <= "06:30":
                logger.info("서버 점검 시간 - 연결 유지 스킵")
                return
                
            # Keep-alive 신호 (간단한 조회)
            if self.kiwoom.GetConnectState():
                logger.debug(f"[{current_time}] 연결 상태 정상 - Keep-alive")
                # 서버 시간 조회로 연결 유지
                self.kiwoom.GetServerGubun()
                
        except Exception as e:
            logger.error(f"연결 체크 중 오류: {e}")
            self.start_reconnect()
    
    def check_market_time(self):
        """정규장 시간 체크 (9:00~15:20)"""
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        weekday = now.weekday()  # 0=월, 4=금
        
        # 주말 체크
        if weekday > 4:
            if self.is_market_open:
                logger.info("주말 - 실시간 데이터 수집 중지")
                self.is_market_open = False
                self.market_close_signal.emit()
            return
            
        # 정규장 시작 (9:00)
        if current_time >= self.market_open_time and current_time < "09:01:00" and not self.is_market_open:
            logger.info("🔔 정규장 시작! 실시간 데이터 수집 시작 (9:00~15:20)")
            self.is_market_open = True
            self.market_open_signal.emit()
            
        # 정규장 마감 (15:20)
        elif current_time >= self.market_close_time and current_time < "15:21:00" and self.is_market_open:
            logger.info("🔕 정규장 마감! 실시간 데이터 수집 중지 (15:20)")
            self.is_market_open = False
            self.market_close_signal.emit()
            
        # 장 시작 준비 (8:50)
        elif current_time >= "08:50:00" and current_time < "09:00:00" and not self.is_market_open:
            logger.info(f"[{current_time}] 장 시작 10분 전 - 준비 중...")
            
        # 대기 상태 로깅 (30분마다)
        elif now.minute % 30 == 0 and now.second < 60:
            if self.is_market_open:
                logger.info(f"[{current_time}] 정규장 진행 중 - 데이터 수집 중")
            elif "09:00:00" <= current_time < self.market_close_time:
                pass  # 정규장 시간 내 이미 시작된 경우
            else:
                logger.info(f"[{current_time}] 정규장 대기 중 (9:00~15:20만 수집)")
    
    def start_reconnect(self):
        """재연결 프로세스 시작"""
        # 최근 재연결 시도 체크 (1분 이내 중복 방지)
        if self.last_reconnect_time:
            time_diff = datetime.now() - self.last_reconnect_time
            if time_diff.seconds < 60:
                return
                
        self.reconnect_count = 0
        self.reconnect_timer.start(5000)  # 5초 후 재연결
        
    def attempt_reconnect(self):
        """재연결 시도"""
        self.reconnect_count += 1
        self.last_reconnect_time = datetime.now()
        
        if self.reconnect_count > self.max_reconnect_attempts:
            logger.error("최대 재연결 시도 초과 - 프로그램 종료 필요")
            self.reconnect_timer.stop()
            return
            
        logger.info(f"재연결 시도 {self.reconnect_count}/{self.max_reconnect_attempts}")
        
        try:
            # 기존 연결 정리
            if self.kiwoom.GetConnectState():
                self.kiwoom.disconnect()
                time.sleep(2)
                
            # 재연결
            result = self.kiwoom.CommConnect()
            if result == 0:
                logger.info("재연결 성공!")
                self.reconnect_timer.stop()
                self.reconnect_count = 0
                self.reconnect_signal.emit()
            else:
                logger.warning(f"재연결 실패 - 30초 후 재시도")
                self.reconnect_timer.setInterval(30000)  # 30초
                
        except Exception as e:
            logger.error(f"재연결 중 오류: {e}")
            self.reconnect_timer.setInterval(30000)
            
    def get_status(self):
        """현재 상태 반환"""
        now = datetime.now()
        status = {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": now.strftime("%A"),
            "connected": self.kiwoom.GetConnectState() if self.kiwoom else False,
            "reconnect_count": self.reconnect_count,
            "market_status": self.get_market_status(),
        }
        return status
        
    def get_market_status(self):
        """장 상태 확인"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        weekday = now.weekday()
        
        if weekday > 4:
            return "주말 휴장"
        elif "05:00" <= current_time <= "06:30":
            return "서버 점검"
        elif "09:00" <= current_time < "15:20":
            return "정규장 진행중 (데이터 수집 중)"
        elif "15:20" <= current_time < "15:30":
            return "정규장 종료 (데이터 수집 중지)"
        elif "08:00" <= current_time < "09:00":
            return "장 시작 대기"
        elif "15:30" <= current_time <= "18:00":
            return "시간외 거래 (데이터 수집 안함)"
        else:
            return "장 마감"
            
    def is_regular_market_hours(self):
        """정규장 시간인지 확인 (9:00~15:20)"""
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        weekday = now.weekday()
        
        # 주말 제외
        if weekday > 4:
            return False
            
        # 정규장 시간 체크
        return self.market_open_time <= current_time < self.market_close_time
            
    def cleanup(self):
        """정리 작업"""
        self.heartbeat_timer.stop()
        self.reconnect_timer.stop()
        self.market_wait_timer.stop()
        
        # 절전 모드 복원
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except:
            pass