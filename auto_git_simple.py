#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git 자동화 스크립트 (간단 버전)
"""

import os
import subprocess
import time
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class GitAutoHandler(FileSystemEventHandler):
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.last_commit_time = 0
        self.commit_delay = 30
        
    def should_ignore(self, file_path):
        ignore_patterns = [
            '__pycache__', '.git', 'logs', '.log', '.pyc', 
            'pure_websocket_data', '.csv', 'nul'
        ]
        path_str = str(file_path).lower()
        return any(pattern in path_str for pattern in ignore_patterns)
    
    def on_modified(self, event):
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        if self.should_ignore(file_path):
            return
            
        if not file_path.suffix in ['.py', '.md']:
            return
            
        print(f"[Change] {file_path.name}")
        
        current_time = time.time()
        if current_time - self.last_commit_time < self.commit_delay:
            return
            
        self.auto_commit_push()
        self.last_commit_time = current_time
    
    def auto_commit_push(self):
        try:
            os.chdir(self.repo_path)
            
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True)
            
            if not result.stdout.strip():
                print("[Git] No changes")
                return
                
            print("[Git] Auto-committing changes...")
            
            subprocess.run(['git', 'add', '.'], check=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"Auto-commit: {timestamp}"
            
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            
            print(f"[Git] SUCCESS: {timestamp}")
            
        except subprocess.CalledProcessError as e:
            print(f"[Git] ERROR: {e}")
        except Exception as e:
            print(f"[Git] EXCEPTION: {e}")

def main():
    repo_path = Path(__file__).parent
    
    print("=" * 50)
    print("Git Auto-commit Started")
    print(f"Path: {repo_path}")
    print("Monitoring: .py, .md files")
    print("Delay: 30 seconds")
    print("Exit: Ctrl+C")
    print("=" * 50)
    
    event_handler = GitAutoHandler(repo_path)
    observer = Observer()
    observer.schedule(event_handler, str(repo_path), recursive=True)
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Git] Stopping automation...")
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()