"""
CSV 저장 모듈
CLAUDE.md 기반 - 종목별 CSV 파일, 틱마다 34개 지표 저장
"""

import os
import csv
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from config import DataConfig, IndicatorConfig, get_csv_filename

class CSVWriter:
    """
    CSV 파일 저장 관리
    - 종목별 개별 CSV 파일
    - 34개 지표를 한 행으로 저장 (틱 기반)
    - I/O 에러 처리 및 무결성 보장
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or DataConfig.CSV_DIR
        self.logger = logging.getLogger(__name__)
        
        # CSV 파일 핸들러 관리
        self.file_handles: Dict[str, any] = {}
        self.csv_writers: Dict[str, csv.DictWriter] = {}
        self.file_locks: Dict[str, threading.Lock] = {}
        
        # 저장 통계
        self.write_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}
        
        # 디렉토리 생성
        self.ensure_directory()
        
        # 34개 지표 헤더 정의
        self.csv_headers = IndicatorConfig.ALL_INDICATORS
        
        self.logger.info(f"CSVWriter 초기화: {self.base_dir}")
    
    def ensure_directory(self):
        """디렉토리 생성"""
        try:
            Path(self.base_dir).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"CSV 디렉토리 생성/확인: {self.base_dir}")
        except Exception as e:
            self.logger.error(f"CSV 디렉토리 보장 실패: {self.base_dir}, 오류: {e}")
            raise
    
    def get_csv_filepath(self, stock_code: str) -> str:
        """CSV 파일 경로 생성"""
        date_str = datetime.now().strftime("%Y%m%d")
        filename = get_csv_filename(stock_code, date_str)
        return os.path.join(self.base_dir, filename)
    
    def initialize_stock_csv(self, stock_code: str) -> bool:
        """종목별 CSV 파일 초기화"""
        try:
            filepath = self.get_csv_filepath(stock_code)
            self.logger.debug(f"CSV 초기화 시도: {stock_code}, 경로: {filepath}")
            self.logger.info(f"[DEBUG] CSV 초기화 진행중: {stock_code}")
            
            # 파일 락 생성
            if stock_code not in self.file_locks:
                self.file_locks[stock_code] = threading.Lock()
            
            with self.file_locks[stock_code]:
                # 파일이 이미 존재하는지 확인
                file_exists = os.path.exists(filepath)
                
                # 파일 핸들 생성 (append mode)
                self.file_handles[stock_code] = open(filepath, 'a', newline='', encoding='utf-8-sig')
                
                # CSV writer 생성
                self.csv_writers[stock_code] = csv.DictWriter(
                    self.file_handles[stock_code],
                    fieldnames=self.csv_headers,
                    extrasaction='ignore'  # 추가 필드 무시
                )
                
                # 헤더 작성 (새 파일인 경우만)
                if not file_exists:
                    self.csv_writers[stock_code].writeheader()
                    self.file_handles[stock_code].flush()
                    self.logger.info(f"CSV 파일 생성: {filepath}")
                else:
                    self.logger.info(f"기존 CSV 파일 열기: {filepath}")
                
                # 통계 초기화
                self.write_counts[stock_code] = 0
                self.error_counts[stock_code] = 0
                
            return True
            
        except Exception as e:
            self.logger.error(f"CSV 초기화 실패 ({stock_code}): {e}")
            return False
    
    def write_indicators(self, stock_code: str, indicators: Dict) -> bool:
        """34개 지표를 CSV에 저장"""
        try:
            self.logger.debug(f"쓰기 시도: {stock_code}, 데이터 키: {list(indicators.keys())[:5]}...")
            # CSV가 초기화되지 않은 경우 초기화
            if stock_code not in self.csv_writers:
                if not self.initialize_stock_csv(stock_code):
                    return False
            
            with self.file_locks[stock_code]:
                # 데이터 검증 및 정제
                clean_indicators = self._clean_indicators(indicators)
                
                # CSV 행 작성
                self.csv_writers[stock_code].writerow(clean_indicators)
                self.file_handles[stock_code].flush()  # 즉시 디스크 쓰기
                
                # 통계 업데이트
                self.write_counts[stock_code] += 1
                
                # 로그 (100틱마다)
                if self.write_counts[stock_code] % 100 == 0:
                    self.logger.info(
                        f"CSV 저장 ({stock_code}): {self.write_counts[stock_code]}틱 완료"
                    )
                
            return True
            
        except Exception as e:
            self.error_counts[stock_code] = self.error_counts.get(stock_code, 0) + 1
            self.logger.error(f"CSV 저장 실패 ({stock_code}): {e}")
            
            # 오류가 많으면 재초기화 시도
            if self.error_counts[stock_code] >= 10:
                self.logger.warning(f"오류 다발, CSV 재초기화 시도: {stock_code}")
                self._reinitialize_csv(stock_code)
            
            return False
    
    def _clean_indicators(self, indicators: Dict) -> Dict:
        """지표 데이터 정제 및 검증"""
        clean_data = {}
        
        for header in self.csv_headers:
            value = indicators.get(header, 0)
            
            # 데이터 타입 정제
            try:
                if header == 'time':
                    # 시간은 정수 (밀리초)
                    clean_data[header] = int(value) if value else 0
                elif header == 'stock_code':
                    # 종목코드는 문자열
                    clean_data[header] = str(value) if value else ""
                elif 'qty' in header or header in ['volume']:
                    # 수량은 정수
                    clean_data[header] = int(float(value)) if value else 0
                else:
                    # 나머지는 실수
                    clean_data[header] = float(value) if value else 0.0
                    
            except (ValueError, TypeError):
                # 변환 실패시 기본값
                if header == 'time':
                    clean_data[header] = int(datetime.now().timestamp() * 1000)
                elif header == 'stock_code':
                    clean_data[header] = ""
                elif 'qty' in header or header in ['volume']:
                    clean_data[header] = 0
                else:
                    clean_data[header] = 0.0
        
        return clean_data
    
    def _reinitialize_csv(self, stock_code: str):
        """CSV 재초기화"""
        try:
            # 기존 핸들 정리
            if stock_code in self.file_handles:
                self.file_handles[stock_code].close()
                del self.file_handles[stock_code]
            
            if stock_code in self.csv_writers:
                del self.csv_writers[stock_code]
            
            # 재초기화
            if self.initialize_stock_csv(stock_code):
                self.error_counts[stock_code] = 0
                self.logger.info(f"CSV 재초기화 성공: {stock_code}")
            
        except Exception as e:
            self.logger.error(f"CSV 재초기화 실패: {e}")
    
    def close_stock_csv(self, stock_code: str):
        """종목별 CSV 파일 닫기"""
        try:
            if stock_code in self.file_locks:
                with self.file_locks[stock_code]:
                    if stock_code in self.file_handles:
                        self.file_handles[stock_code].close()
                        del self.file_handles[stock_code]
                        
                    if stock_code in self.csv_writers:
                        del self.csv_writers[stock_code]
                        
                    self.logger.info(
                        f"CSV 닫기 ({stock_code}): {self.write_counts.get(stock_code, 0)}틱 저장 완료"
                    )
        except Exception as e:
            self.logger.error(f"CSV 닫기 실패 ({stock_code}): {e}")
    
    def close_all(self):
        """모든 CSV 파일 닫기"""
        stock_codes = list(self.file_handles.keys())
        for stock_code in stock_codes:
            self.close_stock_csv(stock_code)
        
        self.logger.info("모든 CSV 파일 닫기 완료")
    
    def get_statistics(self) -> Dict:
        """저장 통계 조회"""
        stats = {
            'total_files': len(self.file_handles),
            'total_writes': sum(self.write_counts.values()),
            'total_errors': sum(self.error_counts.values()),
            'by_stock': {}
        }
        
        for stock_code in set(list(self.write_counts.keys()) + list(self.error_counts.keys())):
            stats['by_stock'][stock_code] = {
                'writes': self.write_counts.get(stock_code, 0),
                'errors': self.error_counts.get(stock_code, 0),
                'filepath': self.get_csv_filepath(stock_code) if stock_code in self.file_handles else None
            }
        
        return stats
    
    def backup_csv_files(self, backup_suffix: str = None) -> bool:
        """CSV 파일 백업"""
        try:
            if backup_suffix is None:
                backup_suffix = f"_backup_{datetime.now().strftime('%H%M%S')}"
            
            backup_count = 0
            for stock_code in self.file_handles.keys():
                original_path = self.get_csv_filepath(stock_code)
                backup_path = original_path.replace('.csv', f'{backup_suffix}.csv')
                
                try:
                    # 파일 복사
                    import shutil
                    shutil.copy2(original_path, backup_path)
                    backup_count += 1
                    
                except Exception as e:
                    self.logger.error(f"백업 실패 ({stock_code}): {e}")
            
            self.logger.info(f"CSV 백업 완료: {backup_count}개 파일")
            return backup_count > 0
            
        except Exception as e:
            self.logger.error(f"백업 중 오류: {e}")
            return False

class BatchCSVWriter(CSVWriter):
    """
    배치 처리 CSV 저장
    - 메모리에 일정량 버퍼링 후 한번에 쓰기
    - 고빈도 틱 데이터 처리 최적화
    """
    
    def __init__(self, base_dir: str = None, batch_size: int = 100):
        super().__init__(base_dir)
        
        self.batch_size = batch_size
        self.buffers: Dict[str, List[Dict]] = {}
        self.buffer_locks: Dict[str, threading.Lock] = {}
        
        self.logger.info(f"BatchCSVWriter 초기화: 배치 크기 {batch_size}")
    
    def write_indicators(self, stock_code: str, indicators: Dict) -> bool:
        """지표를 버퍼에 추가 (배치 처리)"""
        try:
            # 버퍼 초기화
            if stock_code not in self.buffers:
                self.buffers[stock_code] = []
                self.buffer_locks[stock_code] = threading.Lock()
            
            with self.buffer_locks[stock_code]:
                # 데이터 정제 후 버퍼에 추가
                clean_indicators = self._clean_indicators(indicators)
                self.buffers[stock_code].append(clean_indicators)
                
                # 배치 크기 도달시 플러시
                if len(self.buffers[stock_code]) >= self.batch_size:
                    return self._flush_buffer(stock_code)
            
            return True
            
        except Exception as e:
            self.logger.error(f"배치 저장 실패 ({stock_code}): {e}")
            return False
    
    def _flush_buffer(self, stock_code: str) -> bool:
        """버퍼 플러시 (실제 CSV 쓰기)"""
        try:
            if stock_code not in self.buffers or not self.buffers[stock_code]:
                return True
            
            # CSV 초기화 확인
            if stock_code not in self.csv_writers:
                if not self.initialize_stock_csv(stock_code):
                    return False
            
            with self.file_locks[stock_code]:
                # 배치 쓰기
                for data in self.buffers[stock_code]:
                    self.csv_writers[stock_code].writerow(data)
                
                self.file_handles[stock_code].flush()
                
                # 통계 업데이트
                batch_size = len(self.buffers[stock_code])
                self.write_counts[stock_code] = self.write_counts.get(stock_code, 0) + batch_size
                
                self.logger.debug(f"배치 플러시 ({stock_code}): {batch_size}틱")
                
                # 버퍼 초기화
                self.buffers[stock_code].clear()
            
            return True
            
        except Exception as e:
            self.logger.error(f"배치 플러시 실패 ({stock_code}): {e}")
            return False
    
    def flush_all_buffers(self):
        """모든 버퍼 플러시"""
        stock_codes = list(self.buffers.keys())
        for stock_code in stock_codes:
            if self.buffers[stock_code]:  # 버퍼에 데이터가 있는 경우만
                with self.buffer_locks[stock_code]:
                    self._flush_buffer(stock_code)
        
        self.logger.info("모든 배치 버퍼 플러시 완료")
    
    def close_all(self):
        """모든 버퍼 플러시 후 파일 닫기"""
        self.flush_all_buffers()
        super().close_all()

if __name__ == "__main__":
    # 테스트
    import logging
    import time
    
    logging.basicConfig(level=logging.INFO)
    
    # 일반 CSV Writer 테스트
    writer = CSVWriter("test_data")
    
    sample_indicators = {
        'time': int(time.time() * 1000),
        'stock_code': '005930',
        'current_price': 70500.0,
        'volume': 1000000,
        'ma5': 70400.0,
        'rsi14': 55.5,
        'ask1': 70600.0,
        'bid1': 70500.0,
        'ask1_qty': 100,
        'bid1_qty': 150
    }
    
    # 샘플 데이터 저장
    for i in range(5):
        sample_indicators['current_price'] += i * 100
        sample_indicators['time'] += i * 1000
        success = writer.write_indicators('005930', sample_indicators)
        print(f"저장 {i+1}: {'성공' if success else '실패'}")
    
    # 통계 출력
    stats = writer.get_statistics()
    print(f"통계: {stats}")
    
    # 정리
    writer.close_all()
    
    print("\n배치 Writer 테스트")
    
    # 배치 CSV Writer 테스트
    batch_writer = BatchCSVWriter("test_data", batch_size=3)
    
    for i in range(7):  # 3개씩 2배치 + 1개 남음
        sample_indicators['current_price'] += i * 50
        sample_indicators['time'] += i * 500
        success = batch_writer.write_indicators('000660', sample_indicators)
        print(f"배치 저장 {i+1}: {'성공' if success else '실패'}")
    
    # 남은 버퍼 플러시
    batch_writer.flush_all_buffers()
    
    # 통계 출력
    batch_stats = batch_writer.get_statistics()
    print(f"배치 통계: {batch_stats}")
    
    # 정리
    batch_writer.close_all()