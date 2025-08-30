# GitHub 저장소 관리 가이드
<!-- PERMANENT GUIDE - 영구 보관 문서 - 절대 삭제 금지 -->

## 📌 저장소 정보
- **URL**: https://github.com/fgfgt3-pixel/fgfgt3
- **브랜치**: main (단일 브랜치)
- **상태**: Public

## 🤖 다른 AI들을 위한 프로젝트 상태 (2025-08-29 최신)

### 프로젝트 개요
키움 OpenAPI+ 실시간 데이터 수집 시스템 - **완전 정상 작동**

### 핵심 파일 구조
- `main.py` - 메인 실행 파일
- `kiwoom_client.py` - 키움 API 클라이언트  
- `data_processor.py` - 36개 지표 계산 엔진
- `csv_writer.py` - CSV 배치 저장
- `config.py` - 설정 관리
- `CLAUDE.md` - 개발 가이드

### 실행 방법
```bash
C:\python38_32bit\python.exe main.py
```

### 지표 (36개 → 44개 CSV 컬럼)
기본(4) + 가격(5) + 볼륨(3) + 호가(16) + 수급(11) + 기타(5)

## 📤 GitHub 업로드 방법

### 빠른 업로드
```bash
git add . && git commit -m "Update" && git push
```

### 상세 업로드
```bash
# 1. 상태 확인
git status

# 2. 파일 추가
git add [파일명]

# 3. 커밋
git commit -m "설명"

# 4. 업로드  
git push
```

## 🔧 다른 AI 접근 문제 해결

### ✅ 해결 완료 (2025-08-29)
**문제**: 다른 AI가 저장소 읽기 불가
**원인**: `AI_ACCESS_UPDATE.md` 파일 누락 (8월 27일 정리 시 삭제됨)
**해결**: 핵심 내용을 이 파일에 통합

### 문제 발생 시 체크리스트
1. **이 파일 존재 확인** - `GITHUB_GUIDE.md`
2. **최신 변경사항 push** - `git status` 확인
3. **올바른 URL 사용** - https://github.com/fgfgt3-pixel/fgfgt3

## 🚨 중요 사항
<!-- 삭제 방지 마커 -->
1. **이 파일은 영구 보관** - 파일 정리 시에도 삭제 금지
2. **다른 AI 접근용 핵심 파일** - 프로젝트 상태 파악용
3. **변경사항은 항상 push** - 최신 상태 유지 필수

---
<!-- PERMANENT GUIDE END -->
🤖 Updated: 2025-08-29