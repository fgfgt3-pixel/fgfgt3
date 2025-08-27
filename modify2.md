### 지표별 심도 분석 및 문제점
제공된 CSV 데이터를 code_execution 도구로 분석한 결과(229행 데이터)를 바탕으로 각 지표를 재검토했습니다. 통계, 상관 분석, 수동 계산 검증(예: ma5 실제 평균 비교, ret_1s vs 가격 diff)을 통해 패턴을 확인했습니다. 데이터에서 가격(current_price)은 70500~70600으로 좁게 변동하나, 지표들은 초기 기본값(50, 0, 1, 100) 고착, 비현실적 점프(예: obv_delta ±922xxxx), 계산 불일치(예: ma5 reported vs calculated 차이)를 보입니다. 이는 데이터 버퍼 누적 실패, 계산 타이밍 오류, API 데이터 파싱 문제로 보입니다.

modify.md의 이전 제안(예: try-except 추가, CSV flush, 디버깅 로그)을 적용했음에도 문제가 지속되는 이유를 고민: 이는 수정이 증상(에러 방지)에 치중하고, 근본 원인(실시간 데이터 흐름, 버퍼 상태 관리, 이벤트 핸들링)을 놓쳤기 때문입니다. 키움 API는 이벤트 기반(OnReceiveRealData 등)으로, 틱 데이터가 불규칙하게 들어오는데, 코드가 이를 제대로 누적/업데이트하지 않으면 지표가 "고착"되거나 잘못 계산됩니다. 또한, 초기 데이터 부족 시 기본값으로 대체하지만, 이후 데이터가 쌓여도 재계산 트리거가 없어 지속됩니다. 아래에서 문제 지표 중심으로 분석하고, modify.md를 보완한 구체적 수정 제안을 합니다.

#### 1. 가격 지표 (ma5, rsi14, disparity, stoch_k, stoch_d)
   - **ma5 (5일 이동평균)**:
     - **관찰 문제**: 초반 0, 이후 70520~70600으로 업데이트되지만 느리고 불일관적. 도구 분석: 마지막 10행에서 reported ma5(예: 70540) vs 실제 최근 5가격 평균(70545.9) 불일치. 상관 분석: ma5와 가격 diff 상관 0.06 (낮음), 데이터 누적 부족으로 보임.
     - **근본 원인**: 버퍼(deque or list)가 초기 데이터 부족 시 0으로 채우고, 새 틱마다 전체 재계산 안 함. min_periods=1 설정했어도, API 틱이 불완전(예: 가격만 업데이트)하면 평균 왜곡. modify.md의 try-except가 division by zero 방지하지만, 버퍼 상태 유지 실패로 지속.
     - **수정 제안**: `data_processor.py`에서 deque(maxlen=5)로 가격 버퍼 관리, 매 틱 `ma5 = sum(buffer) / len(buffer) if buffer else 0`. OnReceiveRealData 콜백에서 버퍼 append 후 즉시 재계산. 초기화 시 과거 5틱 로드(API Opt10081 호출). 로그: "Buffer length: {len(buffer)}, ma5: {ma5}".

   - **rsi14 (14기간 RSI)**:
     - **관찰 문제**: 평균 49.97, std 5.39로 중립 고착, 변화율(rsi_diff) -20~20 점프. 가격 상승 시 rsi 증가 기대되나, 상관 0.45로 약함. 초기 50 지속 후 갑작 변동(예: 50 → 40).
     - **근본 원인**: RSI는 14개 up/down moves 필요; 버퍼가 14개 미만 시 50 기본값, 하지만 데이터 쌓인 후에도 평균 gain/loss 계산이 누적 안 됨(초기화 버그). modify.md의 epsilon 추가가 오버플로 방지하지만, 실시간 up/down 업데이트 타이밍(가격 변화 시만?) 미스.
     - **수정 제안**: 별도 up_moves, down_moves 리스트(deque(maxlen=14)), 매 틱 price_diff >0 시 up 추가, <0 시 down. `rs = avg_up / (avg_down + 1e-10)`, rsi=100 - 100/(1+rs). 초기 RSI=50 설정 후, 14틱부터 업데이트. 이벤트 핸들러에 "RSI buffer full: {len(up_moves)}" 로그.

   - **disparity (가격/ma 비율 *100)**:
     - **관찰 문제**: ~99.9~100.1로 중립, ma5와 상관 0.57. ma5=0 시 100 기본, 하지만 ma5 업데이트 후에도 지연(예: 가격 70600, ma5 70520 → 100.1134 정확하나 초기 지연).
     - **근본 원인**: ma5 지연으로 disparity도 지연. modify.md의 if ma5 else 100이 적용됐으나, ma5 계산 타이밍과 disparity 호출 동기화 안 됨.
     - **수정 제안**: ma5 계산 직후 disparity 즉시 업데이트. `disparity = (current_price / ma5 * 100) if ma5 > 0 else 100`. 함수화해 순차 호출 보장.

   - **stoch_k, stoch_d (스토캐스틱 %K, %D)**:
     - **관찰 문제**: stoch_k 평균 ~68, 가격 up 시 71.77, down 시 63.22로 방향성 있으나, 값이 63.63636(100/1.57?), 72.72727(100/1.375?) 등 반복 패턴(11분의 7 등). stoch_d는 k의 3기간 평균 기대되나 지연(상관 0.15 낮음).
     - **근본 원인**: %K = 100*(C - L14)/(H14 - L14), 14기간 high/low 버퍼 미관리. 패턴은 잘못된 분모(고정값 사용)로 의심. modify.md의 min/max 계산 수정에도, 실시간 high/low 업데이트 누락(틱마다 max/min 재계산 안 함).
     - **수정 제안**: high_buffer, low_buffer deque(maxlen=14), 매 틱 append 후 `stoch_k = 100 * (current - min(low_buffer)) / (max(high_buffer) - min(low_buffer) + 1e-10)`. stoch_d = 최근 3 stoch_k 평균. 초기 버퍼 채우기 위해 과거 데이터 로드.

#### 2. 볼륨 지표 (vol_ratio, z_vol, obv_delta)
   - **vol_ratio (현재/평균 거래량 비율)**:
     - **관찰 문제**: 모든 229행 1 고정(std NaN). volume 증가에도 변동 없음.
     - **근본 원인**: 평균 vol 계산 버퍼 초기화 버그(항상 current_vol / current_vol =1). modify.md의 rolling 평균 추가에도, 버퍼가 비거나 리셋됨.
     - **수정 제안**: vol_history deque(maxlen=20), 매 틱 append(volume diff), `vol_ratio = current_vol / (sum(vol_history)/len(vol_history) or 1)`. 초기화 시 0 아닌 과거 vol 로드.

   - **z_vol (거래량 z-스코어)**:
     - **관찰 문제**: 평균 1.66, std 0.49로 작고, volume과 상관 0.16 낮음. 가격/volume 변화 무시.
     - **근본 원인**: mean/std가 고정 또는 짧은 버퍼로 계산. modify.md의 stats 업데이트에도, 실시간 재계산 미스.
     - **수정 제안**: vol_buffer deque(maxlen=50), `mean = np.mean(vol_buffer)`, `std = np.std(vol_buffer) + 1e-10`, z_vol = (current_vol - mean)/std. 매 틱 업데이트.

   - **obv_delta (OBV 변화량)**:
     - **관찰 문제**: 가격 up 시 평균 +9221851, down 시 -9221897 – 방향성은 맞으나, 값이 전체 volume 크기(922xxxx)로 과도(누적처럼 보임). 상관 0.98 높지만, delta 아닌 절대값.
     - **근본 원인**: OBV = prev_OBV + (vol if up else -vol), 하지만 delta가 prev_OBV로 잘못 계산(초기 0 + vol = vol). modify.md의 부호 수정에도, prev_OBV 상태 저장 실패.
     - **수정 제안**: 클래스 var prev_obv=0, `obv_delta = vol if ret_1s>0 else -vol if ret_1s<0 else 0`, then prev_obv += obv_delta. 누적 확인 로그.

#### 3. Bid/Ask 지표 (spread, bid_ask_imbalance)
   - **spread (매도-매수 스프레드)**:
     - **관찰 문제**: 모든 행 0. ask1~5, bid1~5 모두 0.
     - **근본 원인**: API 주문장 데이터 미수신(Opt10005 등 호출 실패). modify.md의 파싱 수정에도, 실시간 Reg 미등록.
     - **수정 제안**: `kiwoom_client.py`에서 SetRealReg("주문장코드") 추가, 이벤트에서 ask/bid parse. `spread = ask1 - bid1 if ask1>bid1 else 0`.

   - **bid_ask_imbalance (매수-매도 불균형)**:
     - **관찰 문제**: 모든 행 0(unique [0]). qty 필드 0으로 계산 불가.
     - **근본 원인**: qty 데이터 미파싱. modify.md의 sum 계산에도, 입력 0.
     - **수정 제안**: `imbalance = (sum(bid_qty) - sum(ask_qty)) / (sum(bid_qty) + sum(ask_qty) + 1e-10)`. API 이벤트 확인.

#### 4. 기타 지표 (accel_delta, ret_1s)
   - **accel_delta (가속도 변화)**:
     - **관찰 문제**: 평균 0, std 110, 값 ±100~200 점프. ret_1s와 상관 0.24 낮음.
     - **근본 원인**: accel = ret_1s - prev_ret, 하지만 prev_ret 저장 실패. modify.md의 버퍼에도 타이밍 미스.
     - **수정 제안**: ret_buffer deque(maxlen=2), `accel_delta = ret_buffer[-1] - ret_buffer[-2] if len>=2 else 0`.

   - **ret_1s (1초 수익률)**:
     - **관찰 문제**: 도구 분석: reported vs calculated 불일치(예: reported -0.14164 vs calc -0.000708). 가격不变 시 비제로.
     - **근본 원인**: (current - prev)/prev지만, prev_price가 잘못 저장(시간 간격 무시). modify.md의 업데이트에도, 초단위 아닌 틱 기반 오류.
     - **수정 제안**: timestamp 사용, `ret_1s = (current_price - prev_price) / prev_price`, prev 업데이트. 시간 diff <1s 시 0.

### 왜 modify.md 적용 후에도 작동 안 하는가?
- **고민 포인트**: modify.md는 에러 핸들링(try-except, epsilon)에 초점, 하지만 실시간 시스템의 핵심(버퍼 상태 유지, 이벤트 동기화, 초기 데이터 로드)을 간과. API 틱이 비동기라, 계산 함수가 호출 안 되거나 버퍼 리셋됨. 데이터 부족 시 기본값 과다 사용.
- **전체 수정 제안**: `kiwoom_client.py`에 글로벌 버퍼 클래스 추가, 모든 지표 함수화. 테스트: 모의 데이터로 시뮬레이션(code_execution처럼). 로그 강화: 매 틱 "Data received, buffers updated". 재시작 시 과거 데이터 preload. 에러 로그 공유 시 더 세밀 조정.

### 지표별 심도 분석 및 문제점
제공된 CSV 데이터(229행)를 code_execution 도구로 재분석한 결과(통계 요약: 모든 호가 가격/잔량 필드 평균 0, std 0; 수급 지표 모두 0), 이 지표들은 완전히 업데이트되지 않고 0으로 고정되어 있습니다. 이는 기본 지표(가격, 거래량)와 달리 실시간 API 구독 또는 TR 요청이 제대로 작동하지 않음을 나타냅니다. 웹 검색 결과를 바탕으로 키움 Open API 문서를 참조: 호가 지표는 SetRealReg로 실시간 구독, OPT10059는 CommRqData로 주기적 TR 요청 필요. modify.md의 이전 제안(예: 파싱 수정, try-except 추가)이 적용됐음에도 문제가 지속되는 이유를 고민: 이는 수정이 코드 레벨(에러 방지)에 초점 맞췄으나, API의 본질적 메커니즘(로그인 상태, 이벤트 핸들링, 구독 등록, 요청 타이밍)을 무시했기 때문입니다. 키움 API는 COM 기반으로, 연결 불안정(로그인 실패, 서버 지연) 시 이벤트가 트리거되지 않고, 실시간 데이터는 구독 후에만 들어오며, TR은 명시적 요청 후 OnReceiveTrData에서만 처리됩니다. 초기 연결 시 구독/TR이 누락되거나, 이벤트 핸들러가 데이터를 제대로 저장하지 않으면 0 고착 발생. 또한, 실시간 틱이 불규칙해 타이머나 루프 없이 요청하면 데이터 누락. 아래에서 지표별로 문제 관찰, 근본 원인, 수정 제안(modify.md 보완 포함)을 합니다.

#### 1. 호가 가격 (ask1~ask5, bid1~bid5)
   - **관찰 문제**: 모든 행에서 ask1~ask5, bid1~bid5가 0으로 고정(std 0, unique 값 [0]). 가격 변동(70500~70600)에도 호가 업데이트 없음. 도구 분석: 가격 변화 시 호가 변화 기대되나 상관 0. 가격 틱은 들어오지만 호가는 무시됨.
     - 현실적 예: 삼성전자(5930) 호가는 보통 70500 근처에서 ask1=70600, bid1=70500 등으로 변동해야 하나, 데이터상 0 → API 데이터 미수신.
   - **근본 원인**: 키움 API에서 호가 데이터는 FID(41: ask1, 42: ask2, ..., 51: bid1 등)로 실시간 구독(SetRealReg)해야 함. modify.md의 파싱 수정(예: GetChejanData)이 적용됐어도, 초기 구독 등록(SetRealReg)이 누락되거나, OnReceiveRealData 이벤트가 호가 아이템을 처리하지 않음. 연결 재시작 시 구독 재등록 안 돼 지속. 웹 검색: "키움 Open API 호가 구독" 결과, screen_no와 item_code로 SetRealReg 필수, 미등록 시 데이터 0.
   - **왜 modify.md 적용 후에도 안 되는가?**: modify.md는 이벤트 핸들러 내 파싱에 초점, 하지만 구독 자체(SetRealReg 호출)가 로그인 후 즉시 안 됨(예: CommConnect 후 지연). 서버 응답 지연 시 이벤트 무응답.
   - **수정 제안**:
     - `kiwoom_client.py`에서 로그인 성공(OnLogin) 후 즉시 `self.SetRealReg(screen_no="1000", code_list=stock_code, fid_list="41;42;43;44;45;61;62;63;64;65", opt_type="0")` 호출 (ask1~5: 41~45, bid1~5: 61~65).
     - OnReceiveRealData에서 sRealType=="주식호가잔량" 확인 후, `ask1 = int(self.GetRealData(fid=41))` 등으로 추출, 클래스 변수에 저장.
     - 타이머 추가: QTimer로 1초마다 구독 상태 체크(SetRealRemove 후 재등록)로 연결 안정화.
     - 로그 강화: "호가 구독 등록: code={stock_code}", "호가 데이터 수신: ask1={ask1}".
     - 테스트: 모의투자 모드로 호가 데이터 확인(code_execution으로 시뮬레이션 불가하나, 로그로 검증).

#### 2. 호가 잔량 (ask1_qty~ask5_qty, bid1_qty~bid5_qty)
   - **관찰 문제**: 모든 행 0(std 0). 호가 가격처럼 업데이트 없음. 도구 분석: 잔량은 보통 수백~수천 주이나, 0 → 완전 미수신. bid_ask_imbalance 계산 시 분모 0으로 에러 가능하나, CSV상 0으로 대체.
     - 예: 실제 시장에서 ask1_qty=100 등 변동해야 하나, 데이터상 없음.
   - **근본 원인**: 잔량 FID(71: ask1_qty, 72: ask2_qty, ..., 81: bid1_qty 등) 구독 필요. 호가 가격과 동일 FID 리스트로 SetRealReg하나, 파싱 시 qty FID 미포함. modify.md의 sum 계산 수정에도, 입력 데이터 자체 0. 웹 검색: 호가 잔량은 호가 FID와 함께 구독, OnReceiveRealData에서 별도 처리.
   - **왜 modify.md 적용 후에도 안 되는가?**: modify.md는 계산 로직(합산)에 초점, 하지만 실시간 이벤트가 qty 데이터를 트리거 안 함(구독 FID 리스트 불완전). 다중 종목 시 screen_no 충돌 가능.
   - **수정 제안**:
     - SetRealReg fid_list 확장: "41;42;43;44;45;71;72;73;74;75;61;62;63;64;65;81;82;83;84;85" (가격 + 잔량).
     - OnReceiveRealData에서 `ask1_qty = int(self.GetRealData(fid=71))` 등 추출.
     - 데이터 저장: 딕셔너리(self.hoga_data = {'ask1': ask1, 'ask1_qty': ask1_qty, ...})로 유지, CSV 쓰기 시 참조.
     - 에러 핸들링: GetRealData 실패 시 0 아닌 이전 값 유지(클래스 var last_hoga).
     - 로그: "잔량 수신: ask1_qty={ask1_qty}", 연결 끊김 시 재구독.

#### 3. 수급 통합 지표 (investor_net_vol dict: indiv_net_vol, foreign_net_vol, inst_net_vol, pension_net_vol, trust_net_vol, insurance_net_vol, private_fund_net_vol, bank_net_vol, state_net_vol, other_net_vol, prog_net_vol)
   - **관찰 문제**: 모든 행 0(std 0, unique [0]). 가격/거래량 변동에도 투자자별 net_vol 업데이트 없음. 도구 분석: 총 sum net도 0, json.dumps 필요하나 CSV상 별도 열조차 0. 실제 시장에서 외인/기관 net_vol ±수천 주 변동 기대.
     - 예: 프로그램(prog_net_vol)은 알고 거래 반영하나, 0 → 미계산.
   - **근본 원인**: OPT10059는 TR(CommRqData)로 요청, OnReceiveTrData에서 데이터 추출. 웹 검색 결과("키움 Open API OPT10059"): 입력값(종목코드, 일자구분, 날짜, 금액수량구분, 매매구분 등)으로 CommRqData("OPT10059", "opt10059", screen_no="2000", input_values), 이벤트에서 GetRepeatCnt로 반복 아이템(개인, 외인 등) 추출. modify.md의 델타 계산(net_vol = buy - sell)에도, TR 요청 자체가 안 됨(타이머 미구현). 실시간 아닌 주기적(분봉) 조회라, 코드가 틱마다 호출 안 함.
   - **왜 modify.md 적용 후에도 안 되는가?**: modify.md는 계산( buy - sell )과 저장(json.dumps)에 초점, 하지만 TR 요청 타이밍(CommRqData 호출)이 로그인 후 1회나 누락. 서버 제한(100 TR/분) 초과 시 블록, 또는 OnReceiveTrData에서 trcode=="opt10059" 분기 미처리. 다중 TR 충돌(screen_no 중복) 가능.
   - **수정 제안**:
     - `kiwoom_client.py`에 타이머(QTimer) 추가: 60초마다 CommRqData("OPT10059", "opt10059", "2000", 0) 호출, 입력 SetInputValue("일자구분"="1", "종목코드"=stock_code, "금액수량구분"="2" (수량), "매매구분"="0" (순매수)).
     - OnReceiveTrData에서 if trcode=="opt10059": repeat_cnt = self.GetRepeatCnt(), for i in range(repeat_cnt): indiv_buy = int(self.GetTrData(i, "개인투자자")), ... net_vol = buy - sell, 딕셔너리 저장(self.investor_net = {'indiv_net_vol': indiv_net_vol, ...}).
     - CSV 저장: 별도 열로(11개 net_vol) 또는 json.dumps(self.investor_net), 총 sum_net = sum(net_vol.values()).
     - 제한 대응: 요청 전 CommGetConnectState 확인, 초과 시 지연(sleep(0.2)).
     - 로그: "OPT10059 요청: code={stock_code}", "수급 데이터 수신: indiv_net_vol={indiv_net_vol}".
     - 초기화: 시작 시 1회 요청으로 과거 데이터 preload.

### 왜 전체적으로 modify.md 적용 후에도 작동 안 하는가?
- **고민 포인트**: modify.md는 증상 치료(파싱, 계산 에러 방지)에 그쳐, API의 동적 특성(구독/TR 타이밍, 이벤트 동기화, 연결 상태 관리)을 놓침. 실시간 시스템이라, 코드 실행 중 연결 끊김/지연 시 데이터 0 유지. 버퍼나 상태 변수가 volatile해 재시작 시 초기화.
- **전체 수정 제안**: Kiwoom 클래스에 상태 머신 추가(연결/구독/요청 상태 추적). 모든 이벤트에 try-except + 로그. 모의 데이터 시뮬레이션 스크립트 작성(예: fake 이벤트 트리거). API 문서(browse_page로 키움 개발자 센터 확인) 참조. 에러 로그 공유 시 더 정확.

이상 modify2.md는 2025.08.27 15:50분경에 적용됨