"""
FID 스캔 도구 - 올바른 매수호가 잔량 FID 찾기
"""

import sys
import time
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget

class FIDScanner:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.stock_code = "005930"  # 삼성전자
        
    def scan_fids(self, fid_range):
        """FID 범위 스캔"""
        print(f"=== FID {fid_range[0]}~{fid_range[1]} 스캔 ===")
        results = {}
        
        for fid in range(fid_range[0], fid_range[1] + 1):
            try:
                value = self.ocx.dynamicCall("GetCommRealData(QString, int)", self.stock_code, fid)
                if value and value.strip():
                    cleaned = value.strip().replace('+', '').replace('-', '').replace(',', '')
                    try:
                        num_value = int(cleaned)
                        if num_value > 0:
                            results[fid] = num_value
                            print(f"FID {fid}: {num_value:,}주")
                    except ValueError:
                        pass
            except Exception as e:
                pass
                
        return results
    
    def find_target_values(self, target_values):
        """특정 값들을 찾는 FID 스캔"""
        print(f"\n=== 목표값 검색: {target_values} ===")
        
        # 일반적인 호가 FID 범위들
        ranges = [
            (60, 80),   # 호가 잔량 관련
            (27, 50),   # 기본 호가 관련  
            (121, 130), # 확장 호가 관련
        ]
        
        all_results = {}
        for fid_range in ranges:
            results = self.scan_fids(fid_range)
            all_results.update(results)
            
        # 목표값과 가까운 FID 찾기
        print(f"\n=== 목표값 근사치 FID ===")
        for target in target_values:
            closest_fid = None
            closest_diff = float('inf')
            
            for fid, value in all_results.items():
                diff = abs(value - target)
                if diff < closest_diff:
                    closest_diff = diff
                    closest_fid = fid
                    
            if closest_fid:
                print(f"목표 {target:,}주 → FID {closest_fid}: {all_results[closest_fid]:,}주 (차이: {closest_diff:,})")
        
        return all_results

def main():
    scanner = FIDScanner()
    
    # 목표값: 모바일에서 본 매수호가 잔량
    target_values = [480000, 340000]  # 48만, 34만
    
    print("FID 스캔 시작...")
    print("※ 키움에 로그인되어 있어야 합니다.")
    
    results = scanner.find_target_values(target_values)
    
    print(f"\n=== 전체 결과 ===")
    for fid, value in sorted(results.items()):
        print(f"FID {fid}: {value:,}주")

if __name__ == "__main__":
    main()