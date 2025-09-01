#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
키움 프로그램 종료 원인 분석 및 시스템 모니터링
프로그램 크래시 원인을 실시간으로 감지하고 로깅
"""

import os
import sys
import time
import psutil
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional
from PyQt5.QtCore import QTimer, QObject, pyqtSignal

class SystemCrashDetector(QObject):
    """
    시스템 크래시 감지 및 분석
    """
    crash_detected = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('crash_detector')
        self.start_time = time.time()
        self.last_heartbeat = time.time()
        
        # 시스템 리소스 추적
        self.memory_history = []
        self.cpu_history = []
        self.connection_history = []
        
        # 모니터링 타이머들
        self.resource_timer = QTimer()
        self.heartbeat_timer = QTimer()
        self.crash_check_timer = QTimer()
        
        self.setup_timers()
        
    def setup_timers(self):
        """타이머 설정"""
        # 리소스 모니터링 (30초마다)
        self.resource_timer.timeout.connect(self.check_system_resources)
        self.resource_timer.start(30000)
        
        # 하트비트 (5초마다)
        self.heartbeat_timer.timeout.connect(self.update_heartbeat)
        self.heartbeat_timer.start(5000)
        
        # 크래시 체크 (10초마다)
        self.crash_check_timer.timeout.connect(self.check_for_crashes)
        self.crash_check_timer.start(10000)
        
    def check_system_resources(self):
        """시스템 리소스 모니터링"""
        try:
            # 메모리 사용량
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            
            # 시스템 전체 메모리
            system_memory = psutil.virtual_memory()
            
            self.memory_history.append({
                'time': time.time(),
                'process_memory_mb': memory_mb,
                'system_memory_percent': system_memory.percent,
                'system_available_mb': system_memory.available / 1024 / 1024
            })
            
            self.cpu_history.append({
                'time': time.time(),
                'cpu_percent': cpu_percent
            })
            
            # 위험 임계값 체크
            if memory_mb > 500:  # 500MB 초과
                self.logger.warning(f"⚠️ 메모리 사용량 높음: {memory_mb:.1f}MB")
            
            if system_memory.percent > 90:  # 시스템 메모리 90% 초과
                self.logger.warning(f"⚠️ 시스템 메모리 부족: {system_memory.percent:.1f}%")
            
            # 최근 1시간 데이터만 유지
            cutoff_time = time.time() - 3600
            self.memory_history = [h for h in self.memory_history if h['time'] > cutoff_time]
            self.cpu_history = [h for h in self.cpu_history if h['time'] > cutoff_time]
            
        except Exception as e:
            self.logger.error(f"리소스 모니터링 오류: {e}")
    
    def update_heartbeat(self):
        """하트비트 업데이트"""
        self.last_heartbeat = time.time()
        
    def check_for_crashes(self):
        """크래시 가능성 체크"""
        try:
            current_time = time.time()
            
            # 하트비트 체크
            if current_time - self.last_heartbeat > 30:  # 30초 이상 응답 없음
                crash_info = {
                    'type': 'heartbeat_timeout',
                    'last_heartbeat': self.last_heartbeat,
                    'timeout_seconds': current_time - self.last_heartbeat
                }
                self.logger.error(f"💀 하트비트 타임아웃 감지: {crash_info}")
                self.crash_detected.emit('heartbeat_timeout', crash_info)
            
            # 메모리 급증 체크
            if len(self.memory_history) >= 2:
                recent = self.memory_history[-1]['process_memory_mb']
                previous = self.memory_history[-2]['process_memory_mb']
                if recent - previous > 100:  # 100MB 급증
                    crash_info = {
                        'type': 'memory_spike',
                        'previous_mb': previous,
                        'current_mb': recent,
                        'increase_mb': recent - previous
                    }
                    self.logger.warning(f"⚠️ 메모리 급증 감지: {crash_info}")
                    
        except Exception as e:
            self.logger.error(f"크래시 체크 오류: {e}")

class ConnectionStabilityMonitor(QObject):
    """
    키움 연결 안정성 모니터링
    """
    connection_issue_detected = pyqtSignal(str, dict)
    
    def __init__(self, kiwoom_client):
        super().__init__()
        self.kiwoom_client = kiwoom_client
        self.logger = logging.getLogger('connection_monitor')
        
        # 연결 상태 추적
        self.connection_log = []
        self.last_data_time = {}  # 종목별 마지막 데이터 수신 시간
        self.data_timeout_threshold = 300  # 5분
        
        # 모니터링 타이머
        self.stability_timer = QTimer()
        self.stability_timer.timeout.connect(self.check_connection_stability)
        self.stability_timer.start(20000)  # 20초마다
        
    def check_connection_stability(self):
        """연결 안정성 체크"""
        try:
            current_time = time.time()
            
            # 키움 연결 상태 체크
            if hasattr(self.kiwoom_client, 'ocx') and self.kiwoom_client.ocx:
                try:
                    state = self.kiwoom_client.ocx.dynamicCall("GetConnectState()")
                    self.connection_log.append({
                        'time': current_time,
                        'state': state,
                        'connected': state == 1
                    })
                    
                    if state != 1:
                        issue_info = {
                            'type': 'disconnection',
                            'state': state,
                            'time': current_time
                        }
                        self.logger.error(f"🔴 연결 끊김 감지: {issue_info}")
                        self.connection_issue_detected.emit('disconnection', issue_info)
                        
                except Exception as ocx_e:
                    issue_info = {
                        'type': 'ocx_error',
                        'error': str(ocx_e),
                        'time': current_time
                    }
                    self.logger.error(f"🔴 OCX 호출 오류: {issue_info}")
                    self.connection_issue_detected.emit('ocx_error', issue_info)
            
            # 데이터 수신 타임아웃 체크
            for stock_code, last_time in self.last_data_time.items():
                if current_time - last_time > self.data_timeout_threshold:
                    issue_info = {
                        'type': 'data_timeout',
                        'stock_code': stock_code,
                        'last_data_time': last_time,
                        'timeout_seconds': current_time - last_time
                    }
                    self.logger.warning(f"⚠️ 데이터 수신 타임아웃: {issue_info}")
                    
            # 최근 1시간 데이터만 유지
            cutoff_time = current_time - 3600
            self.connection_log = [log for log in self.connection_log if log['time'] > cutoff_time]
            
        except Exception as e:
            self.logger.error(f"연결 안정성 체크 오류: {e}")
    
    def on_data_received(self, stock_code: str):
        """데이터 수신 시 호출"""
        self.last_data_time[stock_code] = time.time()

class ExceptionTracker:
    """
    예외 발생 추적 및 분석
    """
    
    def __init__(self):
        self.logger = logging.getLogger('exception_tracker')
        self.exception_history = []
        self.original_excepthook = sys.excepthook
        
        # 시스템 예외 후킹
        sys.excepthook = self.exception_hook
        
    def exception_hook(self, exc_type, exc_value, exc_traceback):
        """시스템 예외 후킹"""
        try:
            import traceback
            
            exc_info = {
                'time': time.time(),
                'type': exc_type.__name__,
                'message': str(exc_value),
                'traceback': ''.join(traceback.format_tb(exc_traceback))
            }
            
            self.exception_history.append(exc_info)
            
            # 크리티컬 예외 로깅
            self.logger.critical(f"💥 처리되지 않은 예외 감지:")
            self.logger.critical(f"   타입: {exc_info['type']}")
            self.logger.critical(f"   메시지: {exc_info['message']}")
            self.logger.critical(f"   스택트레이스:\n{exc_info['traceback']}")
            
            # 원본 핸들러 호출
            self.original_excepthook(exc_type, exc_value, exc_traceback)
            
        except Exception as e:
            self.logger.error(f"예외 후킹 오류: {e}")
            self.original_excepthook(exc_type, exc_value, exc_traceback)

class FilePermissionMonitor:
    """
    파일 권한 및 I/O 오류 모니터링
    """
    
    def __init__(self, csv_dir: str):
        self.csv_dir = csv_dir
        self.logger = logging.getLogger('file_monitor')
        self.permission_errors = []
        
    def check_file_permissions(self) -> Dict:
        """CSV 파일 권한 체크"""
        results = {
            'accessible_files': [],
            'locked_files': [],
            'permission_denied': [],
            'disk_space_mb': 0
        }
        
        try:
            # 디스크 공간 체크
            disk_usage = psutil.disk_usage(self.csv_dir)
            results['disk_space_mb'] = disk_usage.free / 1024 / 1024
            
            # CSV 파일들 체크
            if os.path.exists(self.csv_dir):
                for filename in os.listdir(self.csv_dir):
                    if filename.endswith('.csv'):
                        filepath = os.path.join(self.csv_dir, filename)
                        
                        try:
                            # 쓰기 권한 테스트
                            with open(filepath, 'a') as f:
                                pass
                            results['accessible_files'].append(filename)
                            
                        except PermissionError:
                            results['permission_denied'].append(filename)
                            self.logger.warning(f"🔒 권한 거부: {filename}")
                            
                        except Exception as e:
                            results['locked_files'].append((filename, str(e)))
                            self.logger.warning(f"🔒 파일 잠금: {filename} - {e}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"파일 권한 체크 오류: {e}")
            return results

class ComprehensiveMonitor:
    """
    종합 모니터링 시스템
    """
    
    def __init__(self, kiwoom_client=None, csv_dir="pure_websocket_data"):
        self.logger = logging.getLogger('comprehensive_monitor')
        
        # 개별 모니터들
        self.crash_detector = SystemCrashDetector()
        self.connection_monitor = ConnectionStabilityMonitor(kiwoom_client) if kiwoom_client else None
        self.exception_tracker = ExceptionTracker()
        self.file_monitor = FilePermissionMonitor(csv_dir)
        
        # 이벤트 연결
        self.crash_detector.crash_detected.connect(self.on_crash_detected)
        if self.connection_monitor:
            self.connection_monitor.connection_issue_detected.connect(self.on_connection_issue)
        
        # 상태 로깅
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.log_comprehensive_status)
        self.status_timer.start(120000)  # 2분마다
        
        self.logger.info("🔍 종합 모니터링 시스템 시작")
        
    def on_crash_detected(self, crash_type: str, crash_info: dict):
        """크래시 감지 시 처리"""
        self.logger.critical(f"💥 시스템 크래시 감지: {crash_type}")
        self.logger.critical(f"   상세 정보: {crash_info}")
        
        # 크래시 시점 스냅샷 저장
        self.save_crash_snapshot(crash_type, crash_info)
        
    def on_connection_issue(self, issue_type: str, issue_info: dict):
        """연결 문제 감지 시 처리"""
        self.logger.error(f"🔴 연결 문제 감지: {issue_type}")
        self.logger.error(f"   상세 정보: {issue_info}")
        
    def save_crash_snapshot(self, crash_type: str, crash_info: dict):
        """크래시 스냅샷 저장"""
        try:
            snapshot_filename = f"crash_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            snapshot_path = os.path.join("logs", snapshot_filename)
            
            with open(snapshot_path, 'w', encoding='utf-8') as f:
                f.write(f"크래시 감지 시간: {datetime.now()}\n")
                f.write(f"크래시 타입: {crash_type}\n")
                f.write(f"크래시 정보: {crash_info}\n\n")
                
                # 시스템 상태
                f.write("=== 시스템 상태 ===\n")
                try:
                    process = psutil.Process()
                    f.write(f"메모리 사용량: {process.memory_info().rss / 1024 / 1024:.1f}MB\n")
                    f.write(f"CPU 사용률: {process.cpu_percent():.1f}%\n")
                    f.write(f"실행 시간: {time.time() - self.crash_detector.start_time:.1f}초\n")
                except:
                    f.write("시스템 상태 조회 실패\n")
                
                # 메모리 히스토리
                f.write("\n=== 최근 메모리 히스토리 ===\n")
                for record in self.crash_detector.memory_history[-10:]:
                    dt = datetime.fromtimestamp(record['time'])
                    f.write(f"{dt.strftime('%H:%M:%S')}: {record['process_memory_mb']:.1f}MB\n")
                
                # 연결 히스토리
                if self.connection_monitor:
                    f.write("\n=== 최근 연결 히스토리 ===\n")
                    for record in self.connection_monitor.connection_log[-10:]:
                        dt = datetime.fromtimestamp(record['time'])
                        f.write(f"{dt.strftime('%H:%M:%S')}: 상태={record['state']}, 연결={'OK' if record['connected'] else 'FAIL'}\n")
                
                # 예외 히스토리
                f.write("\n=== 최근 예외 히스토리 ===\n")
                for exc in self.exception_tracker.exception_history[-5:]:
                    dt = datetime.fromtimestamp(exc['time'])
                    f.write(f"{dt.strftime('%H:%M:%S')}: {exc['type']} - {exc['message']}\n")
            
            self.logger.info(f"크래시 스냅샷 저장: {snapshot_path}")
            
        except Exception as e:
            self.logger.error(f"크래시 스냅샷 저장 실패: {e}")
    
    def log_comprehensive_status(self):
        """종합 상태 로깅"""
        try:
            self.logger.info("🔍 === 종합 모니터링 상태 ===")
            
            # 시스템 리소스
            if self.crash_detector.memory_history:
                latest_memory = self.crash_detector.memory_history[-1]
                self.logger.info(f"메모리: {latest_memory['process_memory_mb']:.1f}MB, 시스템: {latest_memory['system_memory_percent']:.1f}%")
            
            # 파일 권한 상태
            file_status = self.file_monitor.check_file_permissions()
            self.logger.info(f"CSV 파일: 접근가능 {len(file_status['accessible_files'])}개, 권한거부 {len(file_status['permission_denied'])}개")
            self.logger.info(f"디스크 여유공간: {file_status['disk_space_mb']:.1f}MB")
            
            if file_status['permission_denied']:
                self.logger.warning(f"권한 거부 파일들: {file_status['permission_denied']}")
            
            # 연결 안정성
            if self.connection_monitor and self.connection_monitor.connection_log:
                recent_connections = self.connection_monitor.connection_log[-5:]
                connected_count = sum(1 for log in recent_connections if log['connected'])
                self.logger.info(f"최근 연결 상태: {connected_count}/{len(recent_connections)} 성공")
            
            # 예외 발생 현황
            if self.exception_tracker.exception_history:
                recent_exceptions = len([exc for exc in self.exception_tracker.exception_history 
                                       if time.time() - exc['time'] < 600])  # 최근 10분
                if recent_exceptions > 0:
                    self.logger.warning(f"최근 10분 예외 발생: {recent_exceptions}건")
            
        except Exception as e:
            self.logger.error(f"종합 상태 로깅 오류: {e}")
    
    def on_realdata_received(self, stock_code: str):
        """실시간 데이터 수신 시 호출"""
        if self.connection_monitor:
            self.connection_monitor.on_data_received(stock_code)
    
    def start_monitoring(self):
        """모니터링 시작"""
        self.logger.info("🔍 종합 모니터링 시작")
        
    def stop_monitoring(self):
        """모니터링 중지"""
        try:
            if hasattr(self.crash_detector, 'resource_timer'):
                self.crash_detector.resource_timer.stop()
            if hasattr(self.crash_detector, 'heartbeat_timer'):
                self.crash_detector.heartbeat_timer.stop()
            if hasattr(self.crash_detector, 'crash_check_timer'):
                self.crash_detector.crash_check_timer.stop()
            
            if self.connection_monitor and hasattr(self.connection_monitor, 'stability_timer'):
                self.connection_monitor.stability_timer.stop()
                
            if hasattr(self, 'status_timer'):
                self.status_timer.stop()
                
            self.logger.info("🔍 종합 모니터링 중지")
            
        except Exception as e:
            self.logger.error(f"모니터링 중지 오류: {e}")

def create_crash_resistant_wrapper(original_function, function_name: str):
    """
    함수를 크래시 방지 래퍼로 감싸기
    """
    def wrapper(*args, **kwargs):
        try:
            return original_function(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger('crash_wrapper')
            logger.error(f"💥 {function_name}에서 예외 발생: {type(e).__name__}: {e}")
            logger.error(f"   Args: {args}")
            logger.error(f"   Kwargs: {kwargs}")
            
            # 스택 트레이스
            import traceback
            logger.error(f"   스택트레이스:\n{traceback.format_exc()}")
            
            # 예외를 다시 발생시키지 않고 None 리턴
            return None
    
    return wrapper

if __name__ == "__main__":
    # 독립 실행 테스트
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    monitor = ComprehensiveMonitor()
    monitor.start_monitoring()
    
    print("시스템 모니터링 테스트 실행 중... (Ctrl+C로 종료)")
    
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("\n모니터링 테스트 종료")
        monitor.stop_monitoring()