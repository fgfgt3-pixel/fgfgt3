### stock_code
#### 문제사항 검토
이 지표는 CSV에서 항상 "5930"으로 고정되어 나타납니다 (unique 값 1개). 이는 코드가 단일 종목(삼성전자, 코드 005930)만 처리하도록 설정되어 있거나, 데이터 수집 시 종목 코드가 동적으로 업데이트되지 않아 발생합니다. config.py에서 stock_codes가 단일 값으로 고정된 경우나, kiwoom_client.py에서 종목별 루프가 제대로 작동하지 않을 수 있습니다. 다중 종목 지원을 의도했다면 문제지만, 단일 종목이라면 정상일 수 있습니다.

재검토 결과
문제사항은 정확하나, 단일 종목이 의도된 경우 정상. 다중 지원 제안 OK, 하지만 request_real_time_data 메서드가 kiwoom_client.py에 구현되어 있어야 함 (FID 10,20 등 등록 가정).
수정된 개선 코드 제안
import logging  # 에러 핸들링 강화

# config.py 수정: 다중 종목 지원
class StockConfig:
    STOCK_CODES = ['005930', '000660']  # 예시로 추가 종목 포함

# main.py의 KiwoomDataCollector 클래스 init에 추가
def __init__(self):
    self.stock_codes = StockConfig.STOCK_CODES
    try:
        for code in self.stock_codes:
            self.kiwoom_client.request_real_time_data(code)  # kiwoom_client.py의 메서드 호출 가정
    except Exception as e:
        logging.error(f"실시간 데이터 등록 실패: {e}")

### prev_day_high
#### 문제사항 검토
CSV에서 대부분 0으로 고정되며, 가끔 71000 같은 값만 등장합니다 (unique 값 2개, 98% 이상 0). 이는 이전 날 고가 데이터를 제대로 fetch하지 못하거나, 초기화 후 업데이트되지 않아 발생합니다. kiwoom_client.py에서 Opt10081 같은 TR로 이전 날 데이터를 요청하지 않거나, 캐싱 실패가 원인일 수 있습니다.

prev_day_high
재검토 결과
Opt10081 TR 사용 OK, 필드명 "전일고가" 검색 확인. 하지만 OnReceiveTrData 핸들러 상세 필요.
수정된 개선 코드 제안
# kiwoom_client.py에 추가: 이전 날 고가 fetch 메서드
def get_prev_day_high(self, stock_code):
    try:
        self.kiwoom.SetInputValue("종목코드", stock_code)
        self.kiwoom.SetInputValue("기준일자", datetime.now().strftime('%Y%m%d'))
        self.kiwoom.SetInputValue("수정주가구분", "1")
        self.kiwoom.CommRqData("opt10081", "opt10081", 0, "0101")
    except Exception as e:
        logging.error(f"Opt10081 요청 실패: {e}")
        return 0

# OnReceiveTrData에 추가 (kiwoom_client.py)
if tr_code == "opt10081":
    self.prev_day_high[stock_code] = int(self.kiwoom.GetCommData(tr_code, rq_name, 0, "전일고가") or 0)

# data_processor.py의 calculate_indicators에 호출 추가
indicators['prev_day_high'] = self.kiwoom_client.prev_day_high.get(stock_code, 0)

### rsi14
#### 문제사항 검토
대부분 50 근처 값(예: 50, 45.45, 55.55)으로 반복되며, 변동 범위가 좁습니다 (unique 값 16개, 평균 73.3). 이는 14기간 평균 gain/loss 계산이 제대로 누적되지 않거나, 초기값(50)으로 고착된 상태입니다. data_processor.py에서 RSI 계산 시 데이터 버퍼가 부족하거나, gain/loss 업데이트 로직 오류가 원인일 수 있습니다.

재검토 결과
기본 공식 OK, 하지만 Wilder RSI(EMA 사용)가 표준 – SMA 대신 EMA로 수정.
수정된 개선 코드 제안
import numpy as np

# data_processor.py에 RSI 계산 메서드 수정/추가 (Wilder EMA)
def calculate_rsi(self, prices, period=14):
    if len(prices) < period + 1:
        return 50  # 초기값
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    return rsi

# calculate_indicators에서 호출
indicators['rsi14'] = self.calculate_rsi(self.price_history[stock_code], 14)

### disparity
#### 문제사항 검토
100 근처 값(예: 100, 99.97, 100.02)으로 반복되며, 초기 행에서만 약간 변동합니다 (unique 값 19개, 평균 99.66). 이는 가격과 MA의 차이가 제대로 계산되지 않거나, MA가 항상 가격과 유사하게 고정되어 발생합니다. data_processor.py에서 MA 기간이 짧거나, disparity 공식이 단순 (Close / MA * 100)으로 구현되지 않았을 수 있습니다.

재검토 결과
제안 공식 (Close - MA)/MA * 100이 아닌, 표준 (Close / MA) * 100으로 수정 필요 (검색 확인).
수정된 개선 코드 제안
import numpy as np

# data_processor.py에 disparity 계산 메서드 추가
def calculate_disparity(self, prices, close, period=5):
    if len(prices) < period:
        return 100  # 초기값
    ma = np.mean(prices[-period:])
    disparity = (close / ma) * 100 if ma != 0 else 100
    return disparity

# calculate_indicators에서 호출
indicators['disparity'] = self.calculate_disparity(self.price_history[stock_code], current_price)

### stoch_k
#### 문제사항 검토
0, 50, 100 값만 반복되며, 변동이 거의 없습니다 (unique 값 3개, 평균 53.5). 이는 기간 내 Highest High / Lowest Low 계산이 제대로 되지 않거나, 초기화 값으로 고착된 상태입니다. data_processor.py에서 Stochastic Oscillator %K 계산 시 데이터 부족이나 잘못된 범위 사용이 원인일 수 있습니다.

재검토 결과
표준 공식 맞음. history 버퍼 확인 강조.
수정된 개선 코드 제안
# data_processor.py에 stoch_k 계산 메서드 수정
def calculate_stoch_k(self, highs, lows, close, period=14):
    try:
        if len(highs) < period:
            return 50  # 초기값
        highest_high = max(highs[-period:])
        lowest_low = min(lows[-period:])
        stoch_k = (close - lowest_low) / (highest_high - lowest_low) * 100 if highest_high != lowest_low else 50
        return stoch_k
    except Exception as e:
        logging.error(f"Stoch K 계산 실패: {e}")
        return 50

# calculate_indicators에서 호출 (high_history, low_history 필요)
indicators['stoch_k'] = self.calculate_stoch_k(self.high_history[stock_code], self.low_history[stock_code], current_price)

### stoch_d
#### 문제사항 검토
33.33, 50, 66.67 등 제한적 값만 반복됩니다 (unique 값 6개, 평균 53.4). 이는 %D가 %K의 SMA(3기간)로 계산되지 않거나, %K의 고착으로 인해 연쇄적으로 문제가 발생합니다. data_processor.py에서 %D 계산 로직이 누락되거나 불완전할 수 있습니다.

재검토 결과
표준 %K의 3기간 SMA 맞음.
수정된 개선 코드 제안
import numpy as np

# data_processor.py에 stoch_d 계산 메서드 추가 (stoch_k_history 필요)
def calculate_stoch_d(self, stoch_k_history, period=3):
    if len(stoch_k_history) < period:
        return 50  # 초기값
    stoch_d = np.mean(stoch_k_history[-period:])
    return stoch_d

# calculate_indicators에서 호출 (stoch_k 계산 후)
indicators['stoch_d'] = self.calculate_stoch_d(self.stoch_k_history[stock_code])

### vol_ratio
#### 문제사항 검토
대부분 1 또는 0으로 나타나며, 실제 변동이 부족합니다 (unique 값 105개지만 대부분 고정 패턴). 이는 거래량 비율 계산이 현재/평균 거래량으로 제대로 되지 않거나, up/down volume 분리가 안 된 상태입니다. data_processor.py에서 vol_ratio 공식이 단순하거나 데이터 누적 오류가 원인일 수 있습니다.

재검토 결과
제안 OK, 하지만 True Range / ATR(14)로 더 표준화 (검색 확인).
수정된 개선 코드 제안
import numpy as np

# data_processor.py에 vol_ratio 계산 메서드 추가 (history 필요)
def calculate_vol_ratio(self, high, low, prev_close, atr_history, period=14):
    tr = max(high - low, abs(high - prev_close), abs(low - prev_close))  # True Range
    if len(atr_history) < period:
        return 1  # 초기값
    atr = np.mean(atr_history[-period:])  # ATR (SMA for simplicity)
    vol_ratio = tr / atr if atr != 0 else 1
    return vol_ratio

# calculate_indicators에서 호출
indicators['vol_ratio'] = self.calculate_vol_ratio(current_high, current_low, prev_close, self.atr_history[stock_code])

### spread
#### 문제사항 검토
항상 0으로 고정됩니다 (unique 값 1개). 이는 bid/ask 가격 차이 계산이 안 되거나, 실시간 호가 데이터가 fetch되지 않아 발생합니다. kiwoom_client.py에서 호가 데이터 요청(Opt10005 등)이 누락되었을 수 있습니다.

재검토 결과
Opt10005(TR) 대신 실시간 FID(41 ask1, 46 bid1) 사용이 더 적합 (실시간 프로젝트).
수정된 개선 코드 제안
# kiwoom_client.py에 실시간 호가 등록 (init or connect 후)
def register_real_hoga(self, stock_code):
    self.kiwoom.SetRealReg("1000", stock_code, "41;46", "1")  # ask1, bid1 FID

# OnReceiveRealData에 추가
if fid == 41: self.ask1 = int(real_data)
elif fid == 46: self.bid1 = int(real_data)

# data_processor.py의 calculate_indicators에 추가
indicators['spread'] = self.kiwoom_client.ask1 - self.kiwoom_client.bid1 if hasattr(self.kiwoom_client, 'ask1') else 0

### Tree of Thought 협업 프로세스

#### 단계 1: 초기 생각 공유
- **전문가 1 (Kiwoom API 전문가)**: 제안된 코드가 Kiwoom Open API의 TR 및 FID 규칙을 따르는지 확인. 예: Opt10081은 일봉 데이터로 적합하지만, "전일고가" 필드가 정확히 맞는지 API 문서 검색 결과 확인 필요. Opt10005는 호가 TR로 유효하나, 실시간 호가 FID(41~50 price, 61~70 qty)가 더 적합할 수 있음. stock_code는 config에서 리스트로 OK, 하지만 request_real_time_data 메서드가 실제 구현되었는지 확인. 전체적으로 API 호출 안전성(CommRqData 파라미터, OnReceiveTrData 핸들러)이 부족.
- **전문가 2 (기술 지표 전문가)**: 표준 공식 검토. RSI는 deltas 사용 OK지만, 평균 gain/loss가 SMA로 구현되어 EMA 버전(표준 Wilder RSI)과 다를 수 있음. Disparity는 검색 결과 (close / ma) * 100이 표준인데, 제안은 (close - ma)/ma * 100으로 약간 다름 – 수정 필요. Stochastic %K/%D는 14/3 기간 표준 맞음. vol_ratio는 (High-Low)/EMA(range)로 OK, 하지만 True Range 사용이 더 정확. spread는 ask1 - bid1로 단순 OK.
- **전문가 3 (소프트웨어 개발 전문가)**: 코드 구조 검토. np.diff, np.mean 등 numpy 종속성 가정 OK지만, import 확인 필요. 버퍼 길이 체크(if len < period)는 좋지만, 에러 핸들링(division by zero) 강화. 다중 종목 지원은 루프 OK, 하지만 비동기(asyncio) 고려 안 됨. 초기값(50, 100 등)이 임의 – 데이터 부족 시 NaN 반환 고려.

#### 단계 2: 의견 교환 및 조정
- **전문가 1**: 전문가 2의 Disparity 공식 지적 동의 – API에서 MA 데이터 fetch 시 맞춤. vol_ratio에 True Range 통합 제안. spread는 Opt10005(TR) 대신 실시간 FID로 변경, 왜냐하면 실시간 데이터 수집 프로젝트라서. stock_code는 단일 종목 정상일 수 있으니, 유연성 강조.
- **전문가 2**: 전문가 1의 FID 제안 좋음 – 호가 실시간으로 spread 동적 계산. RSI를 EMA로 업그레이드(Wilder 공식). Stochastic history 버퍼가 제대로 누적되는지 확인. prev_day_high 캐싱 추가 제안.
- **전문가 3**: 전문가 1/2의 API/공식 조정 동의. 코드에 import numpy as np 추가, 에러 핸들링(try-except) 삽입. 전체 코드가 stateful인지 확인 – history 리스트가 클래스 변수로 유지.

#### 단계 3: 추가 조정 및 탈락 판단
- **전문가 1**: spread를 실시간 FID로 변경하면 더 나음. Disparity 공식 수정 필수.
- **전문가 2**: vol_ratio에 ATR 통합 – (current_range / ATR)로.
- **전문가 3**: 모든 코드에 logging 추가 제안. 잘못된 방향 없음 – 모두 유지.
- **합의**: Disparity 공식 수정, RSI EMA 사용, spread 실시간 FID, vol_ratio ATR. 나머지 OK.

#### 단계 4: 최종 유망 해결책 도출
- 합의된 수정: Disparity를 (close / ma) * 100으로. RSI를 EMA 기반 Wilder로. spread를 FID 실시간. vol_ratio를 True Range / ATR로. 나머지 제안 유지, 에러 핸들링 추가.

Role: Kiwoom API Developer

### stock_code
#### 재검토 결과
문제사항은 정확하나, 단일 종목이 의도된 경우 정상. 다중 지원 제안 OK, 하지만 request_real_time_data 메서드가 kiwoom_client.py에 구현되어 있어야 함 (FID 10,20 등 등록 가정).

#### 수정된 개선 코드 제안
```python
import logging  # 에러 핸들링 강화

# config.py 수정: 다중 종목 지원
class StockConfig:
    STOCK_CODES = ['005930', '000660']  # 예시로 추가 종목 포함

# main.py의 KiwoomDataCollector 클래스 init에 추가
def __init__(self):
    self.stock_codes = StockConfig.STOCK_CODES
    try:
        for code in self.stock_codes:
            self.kiwoom_client.request_real_time_data(code)  # kiwoom_client.py의 메서드 호출 가정
    except Exception as e:
        logging.error(f"실시간 데이터 등록 실패: {e}")
```

### prev_day_high
#### 재검토 결과
Opt10081 TR 사용 OK, 필드명 "전일고가" 검색 확인. 하지만 OnReceiveTrData 핸들러 상세 필요.

#### 수정된 개선 코드 제안
```python
# kiwoom_client.py에 추가: 이전 날 고가 fetch 메서드
def get_prev_day_high(self, stock_code):
    try:
        self.kiwoom.SetInputValue("종목코드", stock_code)
        self.kiwoom.SetInputValue("기준일자", datetime.now().strftime('%Y%m%d'))
        self.kiwoom.SetInputValue("수정주가구분", "1")
        self.kiwoom.CommRqData("opt10081", "opt10081", 0, "0101")
    except Exception as e:
        logging.error(f"Opt10081 요청 실패: {e}")
        return 0

# OnReceiveTrData에 추가 (kiwoom_client.py)
if tr_code == "opt10081":
    self.prev_day_high[stock_code] = int(self.kiwoom.GetCommData(tr_code, rq_name, 0, "전일고가") or 0)

# data_processor.py의 calculate_indicators에 호출 추가
indicators['prev_day_high'] = self.kiwoom_client.prev_day_high.get(stock_code, 0)
```

### rsi14
#### 재검토 결과
기본 공식 OK, 하지만 Wilder RSI(EMA 사용)가 표준 – SMA 대신 EMA로 수정.

#### 수정된 개선 코드 제안
```python
import numpy as np

# data_processor.py에 RSI 계산 메서드 수정/추가 (Wilder EMA)
def calculate_rsi(self, prices, period=14):
    if len(prices) < period + 1:
        return 50  # 초기값
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    return rsi

# calculate_indicators에서 호출
indicators['rsi14'] = self.calculate_rsi(self.price_history[stock_code], 14)
```

### disparity
#### 재검토 결과
제안 공식 (Close - MA)/MA * 100이 아닌, 표준 (Close / MA) * 100으로 수정 필요 (검색 확인).

#### 수정된 개선 코드 제안
```python
import numpy as np

# data_processor.py에 disparity 계산 메서드 추가
def calculate_disparity(self, prices, close, period=5):
    if len(prices) < period:
        return 100  # 초기값
    ma = np.mean(prices[-period:])
    disparity = (close / ma) * 100 if ma != 0 else 100
    return disparity

# calculate_indicators에서 호출
indicators['disparity'] = self.calculate_disparity(self.price_history[stock_code], current_price)
```

### stoch_k
#### 재검토 결과
표준 공식 맞음. history 버퍼 확인 강조.

#### 수정된 개선 코드 제안
```python
# data_processor.py에 stoch_k 계산 메서드 수정
def calculate_stoch_k(self, highs, lows, close, period=14):
    try:
        if len(highs) < period:
            return 50  # 초기값
        highest_high = max(highs[-period:])
        lowest_low = min(lows[-period:])
        stoch_k = (close - lowest_low) / (highest_high - lowest_low) * 100 if highest_high != lowest_low else 50
        return stoch_k
    except Exception as e:
        logging.error(f"Stoch K 계산 실패: {e}")
        return 50

# calculate_indicators에서 호출 (high_history, low_history 필요)
indicators['stoch_k'] = self.calculate_stoch_k(self.high_history[stock_code], self.low_history[stock_code], current_price)
```

### stoch_d
#### 재검토 결과
표준 %K의 3기간 SMA 맞음.

#### 수정된 개선 코드 제안
```python
import numpy as np

# data_processor.py에 stoch_d 계산 메서드 추가 (stoch_k_history 필요)
def calculate_stoch_d(self, stoch_k_history, period=3):
    if len(stoch_k_history) < period:
        return 50  # 초기값
    stoch_d = np.mean(stoch_k_history[-period:])
    return stoch_d

# calculate_indicators에서 호출 (stoch_k 계산 후)
indicators['stoch_d'] = self.calculate_stoch_d(self.stoch_k_history[stock_code])
```

### vol_ratio
#### 재검토 결과
제안 OK, 하지만 True Range / ATR(14)로 더 표준화 (검색 확인).

#### 수정된 개선 코드 제안
```python
import numpy as np

# data_processor.py에 vol_ratio 계산 메서드 추가 (history 필요)
def calculate_vol_ratio(self, high, low, prev_close, atr_history, period=14):
    tr = max(high - low, abs(high - prev_close), abs(low - prev_close))  # True Range
    if len(atr_history) < period:
        return 1  # 초기값
    atr = np.mean(atr_history[-period:])  # ATR (SMA for simplicity)
    vol_ratio = tr / atr if atr != 0 else 1
    return vol_ratio

# calculate_indicators에서 호출
indicators['vol_ratio'] = self.calculate_vol_ratio(current_high, current_low, prev_close, self.atr_history[stock_code])
```

### spread
#### 재검토 결과
Opt10005(TR) 대신 실시간 FID(41 ask1, 46 bid1) 사용이 더 적합 (실시간 프로젝트).

#### 수정된 개선 코드 제안
```python
# kiwoom_client.py에 실시간 호가 등록 (init or connect 후)
def register_real_hoga(self, stock_code):
    self.kiwoom.SetRealReg("1000", stock_code, "41;46", "1")  # ask1, bid1 FID

# OnReceiveRealData에 추가
if fid == 41: self.ask1 = int(real_data)
elif fid == 46: self.bid1 = int(real_data)

# data_processor.py의 calculate_indicators에 추가
indicators['spread'] = self.kiwoom_client.ask1 - self.kiwoom_client.bid1 if hasattr(self.kiwoom_client, 'ask1') else 0
```
