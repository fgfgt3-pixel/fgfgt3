#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.gitignore 수정하여 선택적 CSV 업로드 허용
"""

import os
import shutil
from pathlib import Path

def update_gitignore_for_selective_csv():
    """선택적 CSV 업로드를 위한 .gitignore 수정"""
    gitignore_path = ".gitignore"
    
    # 현재 .gitignore 읽기
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # CSV 관련 부분 수정
    new_content = content.replace(
        "# CSV 데이터 파일\npure_websocket_data/\n*.csv",
        """# CSV 데이터 파일 (선택적 업로드)
pure_websocket_data/*.csv
!pure_websocket_data/sample_*.csv
!pure_websocket_data/latest_*.csv"""
    )
    
    # .gitignore 업데이트
    with open(gitignore_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✓ .gitignore 업데이트 완료")
    print("이제 다음 파일들만 업로드됩니다:")
    print("- sample_*.csv (샘플 파일)")  
    print("- latest_*.csv (최신 파일)")

def create_sample_csv():
    """샘플 CSV 파일 생성"""
    data_dir = Path("pure_websocket_data")
    
    # 가장 최근 CSV 파일 찾기
    csv_files = list(data_dir.glob("*.csv"))
    if not csv_files:
        print("CSV 파일이 없습니다.")
        return
    
    latest_file = max(csv_files, key=os.path.getmtime)
    print(f"최신 파일: {latest_file}")
    
    # 샘플 파일 생성 (처음 100줄만)
    sample_file = data_dir / f"sample_{latest_file.name}"
    latest_file_link = data_dir / f"latest_{latest_file.name}"
    
    # 샘플 파일 생성 (헤더 + 100행)
    with open(latest_file, 'r', encoding='utf-8-sig') as src:
        lines = src.readlines()
        
    with open(sample_file, 'w', encoding='utf-8-sig') as dst:
        # 헤더 + 처음 100행 (또는 전체 파일이 100행 미만인 경우)
        dst.writelines(lines[:min(101, len(lines))])
    
    # 최신 파일 링크 생성
    shutil.copy2(latest_file, latest_file_link)
    
    print(f"✓ 샘플 파일 생성: {sample_file}")
    print(f"✓ 최신 파일 링크: {latest_file_link}")
    print(f"샘플 파일 크기: {sample_file.stat().st_size:,} bytes")
    print(f"원본 파일 크기: {latest_file.stat().st_size:,} bytes")

if __name__ == "__main__":
    print("CSV 파일 선택적 GitHub 업로드 설정")
    print("=" * 50)
    
    update_gitignore_for_selective_csv()
    create_sample_csv()
    
    print("\n다음 명령어로 업로드하세요:")
    print("git add . && git commit -m 'CSV 샘플 및 최신 파일 추가' && git push origin main")