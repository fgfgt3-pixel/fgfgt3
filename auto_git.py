#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git 자동화 스크립트 - 파일 변경 감지시 자동 커밋/푸시
"""

import os
import subprocess
import time
import hashlib
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class GitAutoHandler(FileSystemEventHandler):
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.last_commit_time = 0
        self.commit_delay = 30  # 30초 딜레이 (너무 자주 커밋 방지)
        
    def should_ignore(self, file_path):
        """무시할 파일/폴더 확인"""
        ignore_patterns = [
            '__pycache__',
            '.git',
            'logs',
            '.log',
            '.pyc',
            'pure_websocket_data',
            '.csv',
            'nul'
        ]
        
        path_str = str(file_path).lower()
        return any(pattern in path_str for pattern in ignore_patterns)
    
    def on_modified(self, event):
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # 무시할 파일 체크
        if self.should_ignore(file_path):
            return
            
        # Python 파일만 추적
        if not file_path.suffix in ['.py', '.md']:
            return
            
        print(f"[변경감지] {file_path.name}")
        
        # 딜레이 체크 (너무 자주 커밋 방지)
        current_time = time.time()
        if current_time - self.last_commit_time < self.commit_delay:
            return
            
        self.auto_commit_push()
        self.last_commit_time = current_time
    
    def auto_commit_push(self):
        """자동 커밋 및 푸시"""
        try:
            os.chdir(self.repo_path)
            
            # Git 상태 확인
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True)
            
            if not result.stdout.strip():
                print("[Git] 변경사항 없음")
                return
                
            print("[Git] 변경사항 발견, 자동 커밋 시작...")
            
            # Add all changes
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Commit with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"Auto-commit: Code updated at {timestamp}\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
            
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            
            # Push to GitHub
            subprocess.run(['git', 'push', 'origin', 'master'], check=True)
            
            print(f"[Git] ✅ 자동 커밋/푸시 완료: {timestamp}")
            
        except subprocess.CalledProcessError as e:
            print(f"[Git] ❌ 오류: {e}")
        except Exception as e:
            print(f"[Git] ❌ 예외: {e}")

def main():
    repo_path = Path(__file__).parent
    
    print("="*50)
    print("🤖 Git 자동화 시작")
    print(f"📁 모니터링 경로: {repo_path}")
    print("📝 Python, MD 파일 변경시 자동 커밋/푸시")
    print("⏱️  딜레이: 30초 (중복 커밋 방지)")
    print("🛑 종료: Ctrl+C")
    print("="*50)
    
    # 이벤트 핸들러 설정
    event_handler = GitAutoHandler(repo_path)
    observer = Observer()
    observer.schedule(event_handler, str(repo_path), recursive=True)
    
    # 모니터링 시작
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[종료] Git 자동화 종료")
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()