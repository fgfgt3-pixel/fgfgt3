# 🔒 키움 자동 로그인 보안 가이드

## 📋 개요
키움 OpenAPI의 매번 로그인 불편함을 해결하는 **보안 자동 로그인 시스템**입니다.

### 🔐 보안 특징
- **암호화 저장**: 비밀번호를 평문으로 저장하지 않음
- **머신별 암호화**: 다른 컴퓨터에서는 복호화 불가
- **Git 유출 방지**: .gitignore로 완전 차단
- **메모리 보안**: 사용 후 즉시 메모리에서 삭제

---

## 🚀 설정 방법

### 1단계: 인증 정보 설정
```bash
# 보안 설정 도구 실행
python secure_helper.py
```

**입력 정보:**
- 키움 아이디
- 키움 비밀번호  
- 공인인증서 비밀번호

### 2단계: 자동 생성 파일 확인
```
✅ local_config.py 파일이 생성됨
🔒 암호화되어 저장됨
⚠️  절대 공유 금지!
```

---

## 💻 사용 방법

### 자동 로그인 (권장)
```bash
# 일반 실행 (자동 로그인 활성화)
python main.py
```

**결과:**
- ✅ 자동 로그인 활성화됨
- 🔑 로그인 정보 자동 로드
- 👤 사용자 정보: abc*** (마스킹)
- 💡 **로그인 창에서 Enter만 누르세요!**

### 수동 로그인 (fallback)
```bash
# 설정 파일이 없으면 자동으로 수동 모드
python main.py
```

---

## 🛡️ 보안 구조

### 파일 보안
```python
# ❌ 유출 방지된 파일명들
auth_*, login_*, credential_*, secret_*
pwd_*, pass_*, user_*, *.key, *.secret
config_*.py, settings_*.py, private_*.py
secure_*.py, local_*.py, personal_*.py
kiwoom_login*.py, auto_login*.py
```

### 암호화 방식
```
원본: "user_id||password||cert_password"
      ↓
[머신별 키로 암호화]
      ↓
Base64 인코딩
      ↓
파일 저장: "DATA=암호화된텍스트"
```

### 메모리 보안
```python
# 사용 후 즉시 삭제
user_id = password = cert_password = None
del user_id, password, cert_password
```

---

## 🚨 주의사항

### ❌ 절대 금지
- `local_config.py` 파일 공유
- GitHub/외부 저장소 업로드
- 평문 비밀번호 저장
- 암호화 키 노출

### ✅ 안전 수칙
- 파일 백업시 제외
- 다른 컴퓨터 이동시 재설정
- 정기적 비밀번호 변경
- 의심스러운 접근 모니터링

---

## 🔧 문제 해결

### 자동 로그인 실패
```bash
# 1. 설정 파일 재생성
python secure_helper.py

# 2. 파일 권한 확인
# local_config.py 파일이 읽기 가능한지 확인

# 3. 수동 로그인으로 전환
# 자동으로 fallback 모드 실행됨
```

### 암호화 오류
```bash
# 의존성 재설치
pip install cryptography

# Python 32비트 환경 확인
python --version
# Python 3.8.x (32-bit)
```

---

## 📁 파일 구조

```
kiwoom/
├── secure_helper.py          # 🔒 보안 헬퍼 (공개)
├── local_config.py          # 🚫 암호화 인증정보 (비공개)
├── kiwoom_client.py         # 자동로그인 통합
├── main.py                  # 자동로그인 활용
└── .gitignore              # 유출 방지 설정
```

---

## 🎯 작동 원리

### 로그인 프로세스
```
1. main.py 실행
2. 자동로그인 확인 (enable_auto_login)
3. 인증정보 복호화 (get_login_credentials)
4. 로그인 정보 표시 (마스킹)
5. 키움 로그인 창 표시
6. 사용자가 Enter만 입력
7. 연결 완료
```

### 보안 장치
```
- 머신별 암호화 키 (다른 PC에서 복호화 불가)
- Git 완전 차단 (.gitignore 패턴 매칭)
- 메모리 즉시 삭제 (정보 유출 방지)
- 파일명 암호화 (패턴 인식 방지)
```

---

## 💡 팁

### 빠른 로그인
1. `python main.py` 실행
2. 로그인 창이 뜨면 **Enter만** 입력
3. 공인인증서 창에서 **Enter만** 입력
4. 완료!

### 다중 계정
```bash
# 다른 계정용 설정 파일 생성
python secure_helper.py  # -> account2_config.py

# 특정 계정으로 실행
# kiwoom_client.enable_auto_login("account2_config.py")
```

---

**✅ 이제 키움 로그인이 간편해집니다!** 🎉
**🔒 보안도 안전하게 보장됩니다!** 🛡️