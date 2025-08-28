"""
데이터 처리 및 33개 지표 계산 엔진
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
    33개 지표 계산 클래스
    - 틱 기반 실시간 업데이트
    - 종목별 독립 상태 관리
    - rolling window (deque) 사용
    """
    
    def __init__(self, stock_code: str, kiwoom_client=None):
        self.stock_code = stock_code
        self.kiwoom_client = kiwoom_client
        self.logger = logging.getLogger(__name__)
        
        # 틱 데이터 버퍼 (deque with maxlen)
        self.price_buffer = deque(maxlen=DataConfig.MAX_TICK_BUFFER)
        self.volume_buffer = deque(maxlen=DataConfig.MAX_TICK_BUFFER)
        self.time_buffer = deque(maxlen=DataConfig.MAX_TICK_BUFFER)
        
        # 고가/저가 버퍼 (Stochastic 계산용)
        self.high_buffer = deque(maxlen=DataConfig.MAX_TICK_BUFFER)
        self.low_buffer = deque(maxlen=DataConfig.MAX_TICK_BUFFER)
        
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
        
        # ATR 계산용 (vol_ratio 개선용)
        self.atr_buffer = deque(maxlen=DataConfig.RSI14_WINDOW)  # 14기간 ATR
        self.prev_close = 0
        
        # 수급 데이터 (TR 기반)
        self.investor_net_data = {}
        self.prev_investor_net = {}
        
        # 기타 상태
        self.prev_day_high = 0
        self.session_start_price = 0
        self.last_update_time = 0
        
    def update_tick_data(self, tick_data: Dict) -> Dict:
        """
        틱 데이터 업데이트 및 33개 지표 계산
        
        Args:
            tick_data: 실시간 틱 데이터 dict
            
        Returns:
            Dict: 계산된 33개 지표
        """
        try:
            # Unix timestamp (밀리초)로 시간 처리 - kiwoom_client에서 이미 변환됨
            current_time = int(tick_data.get('time', int(time.time() * 1000)))
            
            # kiwoom_client에서 이미 숫자로 변환된 값을 받음
            current_price = float(tick_data.get('current_price', 0))
            current_volume = int(tick_data.get('volume', 0))
            
            if current_price <= 0:
                return {}
            
            # 고가/저가 추출 (키움에서 제공되는 경우)
            current_high = float(tick_data.get('high_price', current_price))
            current_low = float(tick_data.get('low_price', current_price))
            
            # 버퍼 업데이트
            self.price_buffer.append(current_price)
            self.volume_buffer.append(current_volume)
            self.time_buffer.append(current_time)
            self.high_buffer.append(current_high)
            self.low_buffer.append(current_low)
            
            # 호가 데이터 업데이트
            bid_ask_data = self._extract_bid_ask_data(tick_data)
            if bid_ask_data:
                self.bid_ask_buffer.append(bid_ask_data)
                # ✅ modify2.md 근본 문제 해결: 추출된 호가 데이터를 tick_data에 병합
                tick_data.update(bid_ask_data)
                self.logger.debug(f"🔗 [호가병합] {self.stock_code}: ask1={bid_ask_data.get('ask1', 0)}, bid1={bid_ask_data.get('bid1', 0)}")
            
            # 33개 지표 계산
            indicators = self._calculate_all_indicators(tick_data)
            
            # 상태 업데이트 (타입 보장)
            self.prev_close = self.prev_price  # 이전 종가를 ATR 계산용으로 저장
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
        
        # 호가 가격 및 잔량 추출 (키 이름 수정: kiwoom_client에서 ask1, bid1으로 저장)
        for i in range(1, 6):
            ask_price_key = f'ask{i}'        # ask1_price → ask1
            ask_qty_key = f'ask{i}_qty'     # 변경 없음
            bid_price_key = f'bid{i}'       # bid1_price → bid1  
            bid_qty_key = f'bid{i}_qty'     # 변경 없음
            
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
        """33개 지표 전체 계산"""
        # Unix timestamp (밀리초)로 시간 처리 - kiwoom_client에서 이미 변환됨
        current_time = int(tick_data.get('time', int(time.time() * 1000)))
        
        # kiwoom_client에서 이미 숫자로 변환된 값을 받음
        current_price = float(tick_data.get('current_price', 0))
        current_volume = int(tick_data.get('volume', 0))
        
        indicators = {}
        
        # ====================================================================
        # 1. 기본 데이터 (4개)
        # ====================================================================
        indicators['time'] = current_time
        indicators['stock_code'] = self.stock_code
        indicators['current_price'] = current_price
        indicators['volume'] = current_volume
        
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
        indicators['vol_ratio'] = self._calculate_vol_ratio(tick_data)
        indicators['z_vol'] = self._calculate_z_vol(current_volume)
        indicators['obv_delta'] = self._calculate_obv_delta(current_price, current_volume)
        
        # ====================================================================
        # 4. Bid/Ask 지표 (2개)
        # ====================================================================
        indicators['spread'] = self._calculate_spread(tick_data)
        indicators['bid_ask_imbalance'] = self._calculate_bid_ask_imbalance(tick_data)
        
        # ====================================================================
        # 5. 기타 지표 (2개)
        # ====================================================================
        indicators['accel_delta'] = self._calculate_accel_delta()
        indicators['ret_1s'] = self._calculate_ret_1s(current_time, current_price)
        
        # ====================================================================
        # 6. 호가 가격 (10개) - modify2.md 수정: tick_data에서 직접 추출
        # ====================================================================
        # bid_ask_buffer 대신 tick_data에서 직접 가져옴 (병합된 데이터 사용)
        for i in range(1, 6):
            ask_value = float(tick_data.get(f'ask{i}', 0))
            bid_value = float(tick_data.get(f'bid{i}', 0))
            indicators[f'ask{i}'] = ask_value
            indicators[f'bid{i}'] = bid_value
            
            # 🔍 호가 디버깅 (첫 5틱만)
            if len(self.price_buffer) <= 5:
                self.logger.info(f"🎯 [지표계산] {self.stock_code}: ask{i}={ask_value}, bid{i}={bid_value} (tick_data에서 추출)")
        
        # ====================================================================
        # 7. 호가 잔량 (10개) - modify2.md 수정: tick_data에서 직접 추출, 전체 10개 포함
        # ====================================================================
        for i in range(1, 6):
            indicators[f'ask{i}_qty'] = int(tick_data.get(f'ask{i}_qty', 0))
            indicators[f'bid{i}_qty'] = int(tick_data.get(f'bid{i}_qty', 0))
        
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
        if len(self.price_buffer) == 0:
            return 0.0
        # 데이터가 5개 미만이면 현재까지의 평균 계산
        available_data = min(len(self.price_buffer), 5)
        return float(np.mean(list(self.price_buffer)[-available_data:]))
    
    def _calculate_rsi14(self, current_price: float) -> float:
        """14틱 RSI (간소화된 방식)"""
        if len(self.price_buffer) < 2:
            return 50.0  # 기본값
        
        # 가격 변화 계산
        if self.prev_price == 0:
            return 50.0
            
        price_change = current_price - self.prev_price
        
        # Up/Down moves 버퍼에 추가 (modify2.md 제안 반영)
        if price_change > 0:
            self.rsi_gains.append(price_change)
            self.rsi_losses.append(0)
        elif price_change < 0:
            self.rsi_gains.append(0)
            self.rsi_losses.append(abs(price_change))
        else:
            self.rsi_gains.append(0)
            self.rsi_losses.append(0)
        
        # 14개 데이터가 쌓이기 전까지는 기본값
        if len(self.rsi_gains) < DataConfig.RSI14_WINDOW:
            return 50.0
        
        # 최근 14틱의 평균 gain/loss 계산
        recent_gains = list(self.rsi_gains)[-DataConfig.RSI14_WINDOW:]
        recent_losses = list(self.rsi_losses)[-DataConfig.RSI14_WINDOW:]
        
        avg_gain = np.mean(recent_gains)
        avg_loss = np.mean(recent_losses)
        
        # RSI 계산
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / (avg_loss + 1e-10)  # 0으로 나누기 방지
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def _calculate_disparity(self, current_price: float) -> float:
        """이격도 (현재가 / MA5 * 100)"""
        ma5 = self._calculate_ma5()
        if ma5 == 0:
            return 100.0
        return float((current_price / ma5) * 100)
    
    def _calculate_stoch_k(self, tick_data: Dict) -> float:
        """스토캐스틱 K (적절한 high/low 히스토리 사용)"""
        if len(self.high_buffer) < DataConfig.STOCH_WINDOW or len(self.low_buffer) < DataConfig.STOCH_WINDOW:
            return 50.0
        
        try:
            # 최근 N틱의 고가, 저가
            recent_highs = list(self.high_buffer)[-DataConfig.STOCH_WINDOW:]
            recent_lows = list(self.low_buffer)[-DataConfig.STOCH_WINDOW:]
            
            highest_high = max(recent_highs)
            lowest_low = min(recent_lows)
            
            # 현재가
            current_price = float(tick_data.get('current_price', 0))
            
            if highest_high == lowest_low:
                stoch_k = 50.0
            else:
                stoch_k = ((current_price - lowest_low) / (highest_high - lowest_low)) * 100
            
            self.stoch_k_buffer.append(stoch_k)
            return float(stoch_k)
            
        except Exception as e:
            self.logger.error(f"Stoch K 계산 실패: {e}")
            return 50.0
    
    def _calculate_stoch_d(self) -> float:
        """스토캐스틱 D (K의 3틱 이동평균)"""
        if len(self.stoch_k_buffer) < 3:
            return 50.0
        return float(np.mean(self.stoch_k_buffer))
    
    # ========================================================================
    # 볼륨 지표 계산 함수들
    # ========================================================================
    
    def _calculate_vol_ratio(self, tick_data: Dict) -> float:
        """볼륨 비율 (modify2.md 제안: 현재/평균 거래량)"""
        try:
            current_volume = int(tick_data.get('volume', 0))
            
            if current_volume == 0 or len(self.volume_buffer) < 2:
                return 1.0
            
            # 최근 20틱의 평균 거래량 계산
            recent_volumes = list(self.volume_buffer)[-20:] if len(self.volume_buffer) >= 20 else list(self.volume_buffer)
            
            if not recent_volumes:
                return 1.0
                
            avg_volume = np.mean(recent_volumes)
            
            if avg_volume == 0:
                return 1.0
            
            # vol_ratio = 현재 거래량 / 평균 거래량
            vol_ratio = current_volume / avg_volume
            return float(vol_ratio)
            
        except Exception as e:
            self.logger.error(f"vol_ratio 계산 실패: {e}")
            return 1.0
    
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
    
    def _calculate_spread(self, tick_data: Dict) -> float:
        """스프레드 (ask1 - bid1) - tick_data에서 직접 계산"""
        try:
            # tick_data에서 직접 호가 가격 추출
            ask1_price = float(tick_data.get('ask1', 0))
            bid1_price = float(tick_data.get('bid1', 0))
            
            if ask1_price > 0 and bid1_price > 0:
                spread = ask1_price - bid1_price
                return float(spread)
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"spread 계산 실패: {e}")
            return 0.0
    
    def _calculate_bid_ask_imbalance(self, tick_data: Dict) -> float:
        """호가 불균형 (bid_qty - ask_qty) / total - tick_data에서 직접 계산"""
        try:
            # tick_data에서 직접 호가잔량 추출
            total_bid = 0
            total_ask = 0
            
            for i in range(1, 6):
                bid_qty = int(tick_data.get(f'bid{i}_qty', 0))
                ask_qty = int(tick_data.get(f'ask{i}_qty', 0))
                total_bid += bid_qty
                total_ask += ask_qty
            
            total = total_bid + total_ask
            if total == 0:
                return 0.0
            
            imbalance = (total_bid - total_ask) / total
            return float(imbalance)
            
        except Exception as e:
            self.logger.error(f"bid_ask_imbalance 계산 실패: {e}")
            return 0.0
    
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
        investor_indicators = {}
        
        # CSV 컬럼명과 매핑 (modify2.md 수정: 실제 CSV 헤더와 일치)
        investor_columns = [
            'indiv_net_vol', 'foreign_net_vol', 'inst_net_vol', 'pension_net_vol', 
            'trust_net_vol', 'insurance_net_vol', 'private_fund_net_vol', 
            'bank_net_vol', 'state_net_vol', 'other_net_vol', 'prog_net_vol'
        ]
        
        # 각 수급 지표를 0으로 초기화 (TR 데이터가 없을 때)
        for column in investor_columns:
            investor_indicators[column] = 0.0
        
        # 실제 수급 데이터가 있으면 업데이트 (추후 TR 연동시)
        # TODO: OPT10059 TR 데이터 연동 필요
        
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
    
    def __init__(self, target_stocks: List[str] = None, kiwoom_client=None):
        self.target_stocks = target_stocks or TARGET_STOCKS
        self.kiwoom_client = kiwoom_client
        self.logger = logging.getLogger(__name__)
        
        # 종목별 계산기 생성
        self.calculators: Dict[str, IndicatorCalculator] = {}
        for stock_code in self.target_stocks:
            self.calculators[stock_code] = IndicatorCalculator(stock_code, kiwoom_client)
        
        # modify.md 분석: 종목별 최신 호가 저장소 (데이터 흐름 단절 해결)
        self.latest_orderbook: Dict[str, Dict] = {}
        
        # 콜백 함수
        self.indicator_callback: Optional[callable] = None
        
        self.logger.info(f"DataProcessor 초기화: {len(self.calculators)}개 종목 + 호가저장소")
    
    def process_realdata(self, stock_code: str, real_type: str, tick_data: Dict) -> Optional[Dict]:
        """modify.md 분석 반영: 실시간 데이터 처리 + 호가 데이터 병합"""
        if stock_code not in self.calculators:
            self.logger.warning(f"등록되지 않은 종목: {stock_code}")
            return None
        
        try:
            # CLAUDE.md 규칙: 체결 이벤트만 CSV 저장, 호가 이벤트는 메모리만 업데이트
            if real_type in ["주식호가", "주식호가잔량"]:
                # 호가 이벤트: 메모리만 업데이트, CSV 저장 안함
                self.logger.debug(f"📊 [호가업데이트] {stock_code}: {real_type} - 메모리만 갱신")
                self._update_orderbook_only(stock_code, tick_data)
                return None  # CSV 저장하지 않음
            
            elif real_type == "주식체결":
                # 체결 이벤트: CSV 저장
                self.logger.info(f"💾 [체결저장] {stock_code}: {real_type} - CSV 저장")
                if tick_data.get('current_price', 0) == 0:
                    self.logger.warning(f"⚠️ [체결누락] {stock_code}: 체결가 없음")
                    return None
            else:
                # 기타 이벤트 로그
                self.logger.debug(f"📡 [기타이벤트] {stock_code}: {real_type}")
            
            # 모든 데이터를 저장소에 업데이트
            if stock_code not in self.latest_orderbook:
                self.latest_orderbook[stock_code] = {}
            
            # 현재 틱 데이터를 저장소에 병합
            self.latest_orderbook[stock_code].update(tick_data)
            self.latest_orderbook[stock_code]['timestamp'] = time.time()
            
            # 최종 데이터로 지표 계산 (저장소의 모든 데이터 사용)
            final_data = self.latest_orderbook[stock_code].copy()
            
            # 디버깅 로그 (처음 5번만)
            if len(self.calculators[stock_code].price_buffer) < 5:
                self.logger.info(f"🚨 [최종데이터] {stock_code}: ask1={final_data.get('ask1', 0)}, bid1={final_data.get('bid1', 0)}, 가격={final_data.get('current_price', 0)}")
            
            # 지표 계산 및 CSV 저장
            indicators = self.calculators[stock_code].update_tick_data(final_data)
            
            if indicators and self.indicator_callback:
                self.indicator_callback(stock_code, indicators)
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"❌ 실시간 데이터 처리 오류 ({stock_code}): {e}")
            import traceback
            self.logger.error(f"상세 오류: {traceback.format_exc()}")
            return None
    
    def process_tr_data(self, tr_code: str, tr_data: Dict):
        """TR 데이터 처리 (수급 데이터, 전일고가 등)"""
        try:
            if tr_code == "OPT10059":
                # 수급 데이터를 해당 종목에 업데이트
                stock_code = tr_data.get('stock_code')
                if stock_code and stock_code in self.calculators:
                    self.calculators[stock_code].update_investor_data(tr_data)
                    
            elif tr_code == "opt10081":
                # 전일고가 데이터를 해당 종목에 업데이트
                stock_code = tr_data.get('stock_code')
                if stock_code and stock_code in self.calculators:
                    prev_high = tr_data.get('prev_day_high', 0)
                    if prev_high > 0:
                        self.calculators[stock_code].set_prev_day_high(prev_high)
                        self.logger.info(f"전일고가 설정: {stock_code} = {prev_high:,}원")
                    
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
    
    def _update_orderbook_only(self, stock_code: str, tick_data: Dict):
        """호가 이벤트 전용: 메모리만 업데이트, CSV 저장 안함"""
        if stock_code not in self.latest_orderbook:
            self.latest_orderbook[stock_code] = {}
        
        # 호가 데이터를 저장소에 업데이트
        self.latest_orderbook[stock_code].update(tick_data)
        self.latest_orderbook[stock_code]['timestamp'] = time.time()
        
        self.logger.debug(f"호가 저장소 업데이트 완료: {stock_code}")

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

# ============================================================================
# CLAUDE.md 수정사항 - InvestorNetManager 클래스 추가
# ============================================================================

class InvestorNetManager:
    """수급 데이터 관리 - 단순하고 명확한 구조 (CLAUDE.md)"""
    
    def __init__(self, stock_codes):
        self.stock_codes = stock_codes
        self.logger = logging.getLogger(__name__)
        
        # 종목별 현재 수급 데이터 (TR에서 받은 최신 누적값)
        self.current_net_vol = defaultdict(lambda: self._get_empty_dict())
        
        # 종목별 이전 수급 데이터 (delta 계산용)
        self.previous_net_vol = defaultdict(lambda: self._get_empty_dict())
        
        # 종목별 마지막 업데이트 정보
        self.last_update_info = defaultdict(lambda: {
            'time': None,
            'round': 0
        })
        
    def _get_empty_dict(self):
        """빈 수급 딕셔너리 반환"""
        return {
            'individual': 0,      # 개인
            'foreign': 0,         # 외인
            'institution': 0,     # 기관
            'pension': 0,         # 연기금
            'investment': 0,      # 투신
            'insurance': 0,       # 보험
            'private_fund': 0,    # 사모펀드
            'bank': 0,           # 은행
            'state': 0,          # 국가
            'other_corp': 0,     # 기타법인
            'program': 0         # 프로그램
        }
    
    def update_from_tr(self, stock_code, tr_data):
        """TR 응답 처리 - 누적값을 그대로 저장 (대체)"""
        
        # 1. 이전값 백업 (delta 계산용)
        self.previous_net_vol[stock_code] = self.current_net_vol[stock_code].copy()
        
        # 2. 새로운 누적값으로 대체 (키움이 주는 값이 이미 누적값)
        self.current_net_vol[stock_code] = {
            'individual': int(tr_data.get('개인', 0)),
            'foreign': int(tr_data.get('외인', 0)),
            'institution': int(tr_data.get('기관', 0)),
            'pension': int(tr_data.get('연기금', 0)),
            'investment': int(tr_data.get('투신', 0)),
            'insurance': int(tr_data.get('보험', 0)),
            'private_fund': int(tr_data.get('사모펀드', 0)),
            'bank': int(tr_data.get('은행', 0)),
            'state': int(tr_data.get('국가', 0)),
            'other_corp': int(tr_data.get('기타법인', 0)),
            'program': int(tr_data.get('프로그램', 0))
        }
        
        # 3. 업데이트 시간 기록
        self.last_update_info[stock_code]['time'] = time.time()
        self.last_update_info[stock_code]['round'] += 1
        
        self.logger.info(f"수급 데이터 업데이트: {stock_code}, Round {self.last_update_info[stock_code]['round']}")
    
    def get_data_for_tick(self, stock_code):
        """틱마다 현재 저장된 값 반환"""
        current = self.current_net_vol.get(stock_code, self._get_empty_dict())
        previous = self.previous_net_vol.get(stock_code, self._get_empty_dict())
        
        # Delta 계산
        delta = {}
        for key in current.keys():
            delta[key] = current[key] - previous.get(key, 0)
            
        return {
            'net_vol': current,
            'delta': delta,
            'last_update': self.last_update_info[stock_code]['time']
        }
    
    def get_csv_columns(self):
        """CSV용 수급 컬럼 이름 리스트 반환"""
        base_keys = list(self._get_empty_dict().keys())
        columns = []
        
        # 현재 누적값 컬럼
        for key in base_keys:
            columns.append(f'net_{key}')
        
        # 델타 컬럼 (선택적)
        for key in base_keys:
            columns.append(f'delta_{key}')
            
        return columns
    
    def get_csv_data(self, stock_code):
        """CSV 저장용 데이터 반환"""
        data_dict = self.get_data_for_tick(stock_code)
        csv_data = {}
        
        # 현재 누적값
        for key, value in data_dict['net_vol'].items():
            csv_data[f'net_{key}'] = value
            
        # 델타값
        for key, value in data_dict['delta'].items():
            csv_data[f'delta_{key}'] = value
            
        return csv_data