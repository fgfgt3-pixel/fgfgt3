# GitHub 접근 및 업로드 가이드
<!-- IMPORTANT: DO NOT DELETE THIS FILE - 영구 보관 문서 -->
<!-- 이 파일은 프로젝트 핵심 운영 가이드입니다. 절대 삭제하지 마세요. -->
<!-- PERMANENT GUIDE - KEEP THIS FILE EVEN DURING CLEANUP -->

## 📌 이 문서의 목적
컴퓨터 재시작 후에도 GitHub 저장소 관리 및 다른 AI와의 코드 공유를 위한 영구 참조 가이드

## 🔗 GitHub 저장소 정보
- **저장소 URL**: https://github.com/fgfgt3-pixel/fgfgt3
- **접근 상태**: Public (공개)
- **브랜치**: main
- **생성일**: 2025년 8월 26일

## ✅ 다른 AI가 코드를 읽을 수 있게 하는 방법

### 1. 저장소 전체 공유
```
https://github.com/fgfgt3-pixel/fgfgt3
```

### 2. 특정 파일 Raw URL 제공 (권장)
다른 AI에게 아래 형식의 Raw URL을 제공하면 직접 코드를 읽을 수 있습니다:

#### 핵심 파일 Raw URL 목록:
```
https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/main.py
https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/kiwoom_client.py
https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/data_processor.py
https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/csv_writer.py
https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/config.py
https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/CLAUDE.md
https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/README.md
```

### 3. API 접근 (JSON 형식)
```
https://api.github.com/repos/fgfgt3-pixel/fgfgt3
```

## 📤 GitHub에 변경사항 업로드하기

### 수동 업로드 방법
```bash
# 1. 현재 상태 확인
git status

# 2. 변경된 파일 추가
git add .
# 또는 특정 파일만
git add main.py kiwoom_client.py

# 3. 커밋 메시지와 함께 저장
git commit -m "설명적인 커밋 메시지"

# 4. GitHub에 업로드
git push origin main
```

### 32비트 Python 환경에서 실행
```bash
# PowerShell 또는 CMD에서
cd "C:\Users\fgfgt\OneDrive\바탕 화면\kiwoom"
git add .
git commit -m "변경 내용 설명"
git push
```

## 🔍 문제 해결

### 다른 AI가 코드를 못 읽는다고 할 때
1. **Raw URL 사용 확인**: 위의 Raw URL 형식을 정확히 사용했는지 확인
2. **최신 변경사항 Push 확인**: `git status`로 모든 변경사항이 push되었는지 확인
3. **브랜치 확인**: main 브랜치의 URL인지 확인
4. **저장소 공개 상태**: Public으로 설정되어 있는지 확인

### Push 전 확인사항
```bash
# 현재 브랜치 확인
git branch

# 원격 저장소 확인  
git remote -v

# 최근 커밋 확인
git log --oneline -5
```

## 📝 자동 업로드 스크립트 (삭제됨)
- 2025년 8월 27일 프로젝트 정리 중 `auto_git.py`, `auto_git_simple.py` 삭제
- 필요시 수동으로 git 명령어 사용

## 🚨 중요 사항
<!-- DO NOT DELETE MARKERS - 삭제 방지 마커 -->
1. **이 파일은 영구 보관 문서입니다**
2. **파일 정리 시에도 삭제하지 마세요**
3. **GitHub 토큰이 포함된 URL은 공개하지 마세요**
4. **변경사항은 항상 push해야 다른 AI가 최신 코드를 볼 수 있습니다**

## 📅 히스토리
- 2025-08-29: 이 가이드 문서 생성
- 2025-08-28: 프로젝트 정리 및 최적화
- 2025-08-27: auto_git 스크립트 삭제
- 2025-08-26: 저장소 생성

## 💡 Quick Reference
```bash
# 빠른 업로드 (모든 변경사항)
git add . && git commit -m "Update" && git push

# 상태 확인
git status

# 동기화 확인
git push --dry-run
```

---
<!-- END OF PERMANENT GUIDE - DO NOT DELETE -->
<!-- 이 파일은 GITHUB_ACCESS_GUIDE.md로 영구 보관됩니다 -->