"""
데이터 처리 및 34개 지표 계산 엔진
CLAUDE.md 기반 - 틱 기반 업데이트, 종목별 독립 상태 유지
"""

import time
import logging
import numpy as np
from collections import deque, defaultdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from config import (
    DataConfig, IndicatorConfig, TARGET_STOCKS
)

class IndicatorCalculator:
    """
    34개 지표 계산 클래스
    - 틱 기반 실시간 업데이트
    - 종목별 독립 상태 관리
    - rolling window (deque) 사용
    """
    
    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.logger = logging.getLogger(__name__)
        
        # 틱 데이터 버퍼 (deque with maxlen)
        self.price_buffer = deque(maxlen=DataConfig.MAX_TICK_BUFFER)
        self.volume_buffer = deque(maxlen=DataConfig.MAX_TICK_BUFFER)
        self.time_buffer = deque(maxlen=DataConfig.MAX_TICK_BUFFER)
        
        # 호가 데이터 버퍼
        self.bid_ask_buffer = deque(maxlen=100)  # 최근 100틱 호가
        
        # 지표 계산용 상태 변수
        self.prev_price = 0
        self.prev_volume = 0
        self.prev_obv = 0
        self.rsi_gains = deque(maxlen=DataConfig.RSI14_WINDOW)
        self.rsi_losses = deque(maxlen=DataConfig.RSI14_WINDOW)
        
        # 스토캐스틱 계산용
        self.stoch_k_buffer = deque(maxlen=3)
        
        # 수급 데이터 (TR 기반)
        self.investor_net_data = {}
        self.prev_investor_net = {}
        
        # 기타 상태
        self.prev_day_high = 0
        self.session_start_price = 0
        self.last_update_time = 0
        
    def update_tick_data(self, tick_data: Dict) -> Dict:
        """
        틱 데이터 업데이트 및 34개 지표 계산
        
        Args:
            tick_data: 실시간 틱 데이터 dict
            
        Returns:
            Dict: 계산된 34개 지표
        """
        try:
            current_time = tick_data.get('time', int(time.time() * 1000))
            
            # kiwoom_client에서 이미 숫자로 변환된 값을 받음
            current_price = float(tick_data.get('current_price', 0))
            current_volume = int(tick_data.get('volume', 0))
            
            if current_price <= 0:
                return {}
            
            # 버퍼 업데이트
            self.price_buffer.append(current_price)
            self.volume_buffer.append(current_volume)
            self.time_buffer.append(current_time)
            
            # 호가 데이터 업데이트
            bid_ask_data = self._extract_bid_ask_data(tick_data)
            if bid_ask_data:
                self.bid_ask_buffer.append(bid_ask_data)
            
            # 34개 지표 계산
            indicators = self._calculate_all_indicators(tick_data)
            
            # 상태 업데이트 (타입 보장)
            self.prev_price = float(current_price) if current_price else 0
            self.prev_volume = int(current_volume) if current_volume else 0
            self.last_update_time = current_time
            
            return indicators
            
        except Exception as e:
            import traceback
            self.logger.error(f"틱 데이터 처리 오류 ({self.stock_code}): {e}")
            self.logger.error(f"상세 오류: {traceback.format_exc()}")
            self.logger.error(f"입력 데이터: {tick_data}")
            return {}
    
    def _extract_bid_ask_data(self, tick_data: Dict) -> Optional[Dict]:
        """호가 데이터 추출"""
        bid_ask = {}
        
        # 호가 가격 및 잔량 추출
        for i in range(1, 6):
            ask_price_key = f'ask{i}_price'
            ask_qty_key = f'ask{i}_qty'
            bid_price_key = f'bid{i}_price'
            bid_qty_key = f'bid{i}_qty'
            
            # kiwoom_client에서 이미 숫자로 변환된 값을 받음
            bid_ask[f'ask{i}'] = float(tick_data.get(ask_price_key, 0))
            bid_ask[f'ask{i}_qty'] = int(tick_data.get(ask_qty_key, 0))
            bid_ask[f'bid{i}'] = float(tick_data.get(bid_price_key, 0))
            bid_ask[f'bid{i}_qty'] = int(tick_data.get(bid_qty_key, 0))
        
        # 총 호가 잔량 (kiwoom_client에서 이미 숫자로 변환됨)
        bid_ask['total_ask_qty'] = int(tick_data.get('total_ask_qty', 0))
        bid_ask['total_bid_qty'] = int(tick_data.get('total_bid_qty', 0))
        
        return bid_ask if any(v > 0 for v in bid_ask.values()) else None
    
    def _calculate_all_indicators(self, tick_data: Dict) -> Dict:
        """34개 지표 전체 계산"""
        current_time = tick_data.get('time', int(time.time() * 1000))
        
        # kiwoom_client에서 이미 숫자로 변환된 값을 받음
        current_price = float(tick_data.get('current_price', 0))
        current_volume = int(tick_data.get('volume', 0))
        
        indicators = {}
        
        # ====================================================================
        # 1. 기본 데이터 (5개)
        # ====================================================================
        indicators['time'] = current_time
        indicators['stock_code'] = self.stock_code
        indicators['current_price'] = current_price
        indicators['volume'] = current_volume
        indicators['prev_day_high'] = self.prev_day_high
        
        # ====================================================================
        # 2. 가격 지표 (5개)
        # ====================================================================
        indicators['ma5'] = self._calculate_ma5()
        indicators['rsi14'] = self._calculate_rsi14(current_price)
        indicators['disparity'] = self._calculate_disparity(current_price)
        indicators['stoch_k'] = self._calculate_stoch_k(tick_data)
        indicators['stoch_d'] = self._calculate_stoch_d()
        
        # ====================================================================
        # 3. 볼륨 지표 (3개)
        # ====================================================================
        indicators['vol_ratio'] = self._calculate_vol_ratio(current_volume)
        indicators['z_vol'] = self._calculate_z_vol(current_volume)
        indicators['obv_delta'] = self._calculate_obv_delta(current_price, current_volume)
        
        # ====================================================================
        # 4. Bid/Ask 지표 (2개)
        # ====================================================================
        indicators['spread'] = self._calculate_spread()
        indicators['bid_ask_imbalance'] = self._calculate_bid_ask_imbalance()
        
        # ====================================================================
        # 5. 기타 지표 (2개)
        # ====================================================================
        indicators['accel_delta'] = self._calculate_accel_delta()
        indicators['ret_1s'] = self._calculate_ret_1s(current_time, current_price)
        
        # ====================================================================
        # 6. 호가 가격 (10개)
        # ====================================================================
        bid_ask_data = self.bid_ask_buffer[-1] if self.bid_ask_buffer else {}
        for i in range(1, 6):
            indicators[f'ask{i}'] = bid_ask_data.get(f'ask{i}', 0)
            indicators[f'bid{i}'] = bid_ask_data.get(f'bid{i}', 0)
        
        # ====================================================================
        # 7. 호가 잔량 (6개) - 34개 맞추기 위해 조정
        # ====================================================================
        indicators['ask1_qty'] = bid_ask_data.get('ask1_qty', 0)
        indicators['ask2_qty'] = bid_ask_data.get('ask2_qty', 0)
        indicators['ask3_qty'] = bid_ask_data.get('ask3_qty', 0)
        indicators['bid1_qty'] = bid_ask_data.get('bid1_qty', 0)
        indicators['bid2_qty'] = bid_ask_data.get('bid2_qty', 0)
        indicators['bid3_qty'] = bid_ask_data.get('bid3_qty', 0)
        
        # ====================================================================
        # 8. 수급 통합 지표 (11개) - CLAUDE.md 요구사항: 개별 컬럼으로 저장
        # ====================================================================
        investor_indicators = self._calculate_investor_individual_indicators()
        indicators.update(investor_indicators)
        
        return indicators
    
    # ========================================================================
    # 가격 지표 계산 함수들
    # ========================================================================
    
    def _calculate_ma5(self) -> float:
        """5틱 이동평균"""
        if len(self.price_buffer) < 5:
            return 0.0
        return float(np.mean(list(self.price_buffer)[-5:]))
    
    def _calculate_rsi14(self, current_price: float) -> float:
        """14틱 RSI"""
        if len(self.price_buffer) < 2:
            return 50.0  # 기본값
        
        # 가격 변화 계산
        price_change = current_price - self.prev_price
        
        if price_change > 0:
            self.rsi_gains.append(price_change)
            self.rsi_losses.append(0)
        elif price_change < 0:
            self.rsi_gains.append(0)
            self.rsi_losses.append(abs(price_change))
        else:
            self.rsi_gains.append(0)
            self.rsi_losses.append(0)
        
        if len(self.rsi_gains) < DataConfig.RSI14_WINDOW:
            return 50.0
        
        # RSI 계산
        avg_gain = np.mean(self.rsi_gains)
        avg_loss = np.mean(self.rsi_losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def _calculate_disparity(self, current_price: float) -> float:
        """이격도 (현재가 / MA5 * 100)"""
        ma5 = self._calculate_ma5()
        if ma5 == 0:
            return 100.0
        return float((current_price / ma5) * 100)
    
    def _calculate_stoch_k(self, tick_data: Dict) -> float:
        """스토캐스틱 K"""
        if len(self.price_buffer) < DataConfig.STOCH_WINDOW:
            return 50.0
        
        # 최근 N틱의 고가, 저가
        recent_prices = list(self.price_buffer)[-DataConfig.STOCH_WINDOW:]
        highest = max(recent_prices)
        lowest = min(recent_prices)
        
        # kiwoom_client에서 이미 숫자로 변환된 값을 받음
        current_price = float(tick_data.get('current_price', 0))
        
        if highest == lowest:
            stoch_k = 50.0
        else:
            stoch_k = ((current_price - lowest) / (highest - lowest)) * 100
        
        self.stoch_k_buffer.append(stoch_k)
        return float(stoch_k)
    
    def _calculate_stoch_d(self) -> float:
        """스토캐스틱 D (K의 3틱 이동평균)"""
        if len(self.stoch_k_buffer) < 3:
            return 50.0
        return float(np.mean(self.stoch_k_buffer))
    
    # ========================================================================
    # 볼륨 지표 계산 함수들
    # ========================================================================
    
    def _calculate_vol_ratio(self, current_volume: int) -> float:
        """거래량 비율 (현재 틱 거래량 / 평균 거래량)"""
        if len(self.volume_buffer) < 10:
            return 1.0
        
        avg_volume = np.mean(self.volume_buffer)
        if avg_volume == 0:
            return 1.0
            
        # 누적거래량에서 이전 누적거래량을 빼서 틱 거래량 계산
        tick_volume = current_volume - self.prev_volume if self.prev_volume > 0 else 0
        if tick_volume <= 0:
            return 1.0
            
        return float(tick_volume / avg_volume)
    
    def _calculate_z_vol(self, current_volume: int) -> float:
        """거래량 Z-Score"""
        if len(self.volume_buffer) < 10:
            return 0.0
        
        volumes = np.array(self.volume_buffer)
        mean_vol = np.mean(volumes)
        std_vol = np.std(volumes)
        
        if std_vol == 0:
            return 0.0
        
        return float((current_volume - mean_vol) / std_vol)
    
    def _calculate_obv_delta(self, current_price: float, current_volume: int) -> float:
        """OBV 변화량"""
        if self.prev_price == 0:
            self.prev_obv = current_volume
            return 0.0
        
        # OBV 계산
        if current_price > self.prev_price:
            new_obv = self.prev_obv + current_volume
        elif current_price < self.prev_price:
            new_obv = self.prev_obv - current_volume
        else:
            new_obv = self.prev_obv
        
        obv_delta = new_obv - self.prev_obv
        self.prev_obv = new_obv
        
        return float(obv_delta)
    
    # ========================================================================
    # Bid/Ask 지표 계산 함수들
    # ========================================================================
    
    def _calculate_spread(self) -> float:
        """스프레드 (ask1 - bid1)"""
        if not self.bid_ask_buffer:
            return 0.0
        
        latest_hoga = self.bid_ask_buffer[-1]
        ask1 = latest_hoga.get('ask1', 0)
        bid1 = latest_hoga.get('bid1', 0)
        
        return float(ask1 - bid1)
    
    def _calculate_bid_ask_imbalance(self) -> float:
        """호가 불균형 (bid_qty - ask_qty) / total"""
        if not self.bid_ask_buffer:
            return 0.0
        
        latest_hoga = self.bid_ask_buffer[-1]
        total_bid = latest_hoga.get('total_bid_qty', 0)
        total_ask = latest_hoga.get('total_ask_qty', 0)
        total = total_bid + total_ask
        
        if total == 0:
            return 0.0
        
        return float((total_bid - total_ask) / total)
    
    # ========================================================================
    # 기타 지표 계산 함수들
    # ========================================================================
    
    def _calculate_accel_delta(self) -> float:
        """가속도 변화 (가격 변화의 변화율)"""
        if len(self.price_buffer) < 3:
            return 0.0
        
        prices = list(self.price_buffer)[-3:]
        
        # 1차 변화율
        change1 = prices[1] - prices[0]
        change2 = prices[2] - prices[1]
        
        # 2차 변화율 (가속도)
        acceleration = change2 - change1
        
        return float(acceleration)
    
    def _calculate_ret_1s(self, current_time: int, current_price: float) -> float:
        """1초 수익률"""
        if not self.time_buffer or not self.price_buffer:
            return 0.0
        
        # 1초 전 데이터 찾기
        one_sec_ago = current_time - 1000  # 1초 = 1000ms
        
        for i in range(len(self.time_buffer) - 1, -1, -1):
            if self.time_buffer[i] <= one_sec_ago:
                prev_price = self.price_buffer[i]
                if prev_price > 0:
                    return float((current_price - prev_price) / prev_price * 100)
                break
        
        return 0.0
    
    def _calculate_investor_individual_indicators(self) -> dict:
        """수급 지표 11개 개별 계산 (CLAUDE.md 요구사항: 개별 컬럼으로 저장)"""
        from config import IndicatorConfig
        
        investor_indicators = {}
        
        # 투자주체별 순매수량을 개별 컬럼으로 저장
        field_mapping = {
            'indiv_net_vol': 'indiv_net',
            'foreign_net_vol': 'foreign_net', 
            'inst_net_vol': 'inst_net',
            'pension_net_vol': 'pension_net',
            'trust_net_vol': 'trust_net',
            'insurance_net_vol': 'insurance_net',
            'private_fund_net_vol': 'private_fund_net',
            'bank_net_vol': 'bank_net',
            'state_net_vol': 'state_net',
            'other_net_vol': 'other_net',
            'prog_net_vol': 'prog_net'
        }
        
        # 각 투자주체별 데이터 추출
        for csv_column, data_key in field_mapping.items():
            investor_indicators[csv_column] = float(self.investor_net_data.get(data_key, 0))
        
        return investor_indicators
    
    # ========================================================================
    # 수급 데이터 업데이트 (TR 기반)
    # ========================================================================
    
    def update_investor_data(self, investor_data: Dict):
        """수급 데이터 업데이트 (OPT10059 TR 결과)"""
        try:
            self.prev_investor_net = self.investor_net_data.copy()
            self.investor_net_data = investor_data.copy()
            
            self.logger.debug(f"수급 데이터 업데이트 ({self.stock_code}): {investor_data.get('total_net', 0)}")
            
        except Exception as e:
            self.logger.error(f"수급 데이터 업데이트 오류 ({self.stock_code}): {e}")
    
    def set_prev_day_high(self, high_price: float):
        """전일 고가 설정"""
        self.prev_day_high = float(high_price)
    
    def get_buffer_status(self) -> Dict:
        """버퍼 상태 조회"""
        return {
            'stock_code': self.stock_code,
            'price_buffer_size': len(self.price_buffer),
            'volume_buffer_size': len(self.volume_buffer),
            'bid_ask_buffer_size': len(self.bid_ask_buffer),
            'last_update_time': self.last_update_time,
            'last_price': self.prev_price
        }

class DataProcessor:
    """
    전체 데이터 처리 관리자
    - 종목별 IndicatorCalculator 관리
    - 실시간 데이터 라우팅
    - TR 데이터 처리
    """
    
    def __init__(self, target_stocks: List[str] = None):
        self.target_stocks = target_stocks or TARGET_STOCKS
        self.logger = logging.getLogger(__name__)
        
        # 종목별 계산기 생성
        self.calculators: Dict[str, IndicatorCalculator] = {}
        for stock_code in self.target_stocks:
            self.calculators[stock_code] = IndicatorCalculator(stock_code)
        
        # 콜백 함수
        self.indicator_callback: Optional[callable] = None
        
        self.logger.info(f"DataProcessor 초기화: {len(self.calculators)}개 종목")
    
    def process_realdata(self, stock_code: str, real_type: str, tick_data: Dict) -> Optional[Dict]:
        """실시간 데이터 처리"""
        if stock_code not in self.calculators:
            self.logger.warning(f"등록되지 않은 종목: {stock_code}")
            return None
        
        try:
            # 지표 계산
            indicators = self.calculators[stock_code].update_tick_data(tick_data)
            
            if indicators and self.indicator_callback:
                self.indicator_callback(stock_code, indicators)
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"실시간 데이터 처리 오류 ({stock_code}): {e}")
            return None
    
    def process_tr_data(self, tr_code: str, tr_data: Dict):
        """TR 데이터 처리 (수급 데이터 등)"""
        try:
            if tr_code == "OPT10059":
                # 수급 데이터를 해당 종목에 업데이트
                stock_code = tr_data.get('stock_code')
                if stock_code and stock_code in self.calculators:
                    self.calculators[stock_code].update_investor_data(tr_data)
                    
        except Exception as e:
            self.logger.error(f"TR 데이터 처리 오류: {e}")
    
    def set_indicator_callback(self, callback: callable):
        """지표 콜백 함수 설정"""
        self.indicator_callback = callback
    
    def get_all_status(self) -> Dict:
        """전체 상태 조회"""
        status = {
            'total_stocks': len(self.calculators),
            'calculators': {}
        }
        
        for stock_code, calc in self.calculators.items():
            status['calculators'][stock_code] = calc.get_buffer_status()
        
        return status

if __name__ == "__main__":
    # 테스트
    import logging
    logging.basicConfig(level=logging.INFO)
    
    processor = DataProcessor(['005930'])
    
    def test_callback(stock_code, indicators):
        print(f"[지표] {stock_code}: MA5={indicators.get('ma5', 0):.2f}, RSI={indicators.get('rsi14', 0):.2f}")
    
    processor.set_indicator_callback(test_callback)
    
    # 샘플 데이터 테스트
    sample_tick = {
        'time': int(time.time() * 1000),
        'current_price': 70500,
        'volume': 1000000,
        'ask1_price': 70600,
        'bid1_price': 70500,
        'ask1_qty': 100,
        'bid1_qty': 150
    }
    
    result = processor.process_realdata('005930', '주식체결', sample_tick)
    print(f"결과: {result}")