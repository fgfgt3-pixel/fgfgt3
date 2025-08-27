# GitHub 저장소 접근 가이드

## 문제 상황
다른 AI 모델들(Claude Opus 등)이 GitHub 저장소 링크로 직접 접근할 수 없는 상황

## 원인 분석
1. **AI 모델별 웹 접근 제한**: 일부 AI는 GitHub 저장소 직접 접근이 제한됨
2. **웹 크롤링 제한**: GitHub의 봇 접근 제한
3. **인증 요구**: 일부 경우 GitHub 인증이 필요할 수 있음

## 해결 방법들

### 1. Raw 파일 URL 사용 (추천)
```
메인 저장소 URL: https://github.com/fgfgt3-pixel/fgfgt3

개별 파일 Raw URLs:
- CLAUDE.md: https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/CLAUDE.md
- main.py: https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/main.py
- config.py: https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/config.py
- kiwoom_client.py: https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/kiwoom_client.py
- data_processor.py: https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/data_processor.py
- csv_writer.py: https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/csv_writer.py
- run.py: https://raw.githubusercontent.com/fgfgt3-pixel/fgfgt3/main/run.py
```

### 2. GitHub API 사용
```
API Base: https://api.github.com/repos/fgfgt3-pixel/fgfgt3/contents/
파일 목록: https://api.github.com/repos/fgfgt3-pixel/fgfgt3/contents
개별 파일: https://api.github.com/repos/fgfgt3-pixel/fgfgt3/contents/{filename}
```

### 3. 코드 직접 복사 제공
AI가 위 방법들도 접근할 수 없다면, 파일 내용을 텍스트로 직접 제공

### 4. 다른 플랫폼 사용
- GitHub Gist
- Pastebin
- CodePen

## 다른 AI에게 제공할 지침

1. **첫 번째 시도**: Raw URL로 개별 파일 접근
2. **두 번째 시도**: GitHub API 사용
3. **세 번째 시도**: 코드 직접 복사본 요청

## 테스트 결과
- ✅ WebFetch로 저장소 접근 가능
- ✅ Raw URL로 파일 내용 읽기 가능
- ✅ 저장소가 Public으로 설정됨
- ✅ 웹 크롤러 접근 제한 없음

## 권장사항
다른 AI에게는 **Raw URL 목록을 제공하고**, 각 파일을 개별적으로 접근하도록 안내