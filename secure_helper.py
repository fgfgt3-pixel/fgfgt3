"""
🔒 보안 자동 로그인 헬퍼
- 암호화된 인증 정보 처리
- 메모리 보안 (사용 후 즉시 삭제)
- 절대 평문 저장 금지
"""

import os
import base64
import hashlib
import getpass
from cryptography.fernet import Fernet
from typing import Optional, Tuple
import logging

class SecureLoginHelper:
    """보안 로그인 도우미"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._cipher = None
        self._key = None
        
    def _get_machine_key(self) -> bytes:
        """머신별 고유 키 생성"""
        try:
            # 머신 고유 정보를 조합해서 키 생성
            import platform
            machine_info = f"{platform.node()}{platform.processor()}"
            return hashlib.sha256(machine_info.encode()).digest()[:32]
        except:
            # 폴백: 기본 키 사용
            return b'kiwoom_secure_key_2023_fallback_'
    
    def _get_cipher(self) -> Fernet:
        """암호화 객체 생성"""
        if self._cipher is None:
            machine_key = self._get_machine_key()
            fernet_key = base64.urlsafe_b64encode(machine_key)
            self._cipher = Fernet(fernet_key)
        return self._cipher
    
    def encrypt_credentials(self, user_id: str, password: str, cert_password: str) -> str:
        """인증 정보 암호화"""
        try:
            cipher = self._get_cipher()
            credentials = f"{user_id}||{password}||{cert_password}"
            encrypted = cipher.encrypt(credentials.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            self.logger.error(f"암호화 실패: {e}")
            return ""
    
    def decrypt_credentials(self, encrypted_data: str) -> Optional[Tuple[str, str, str]]:
        """인증 정보 복호화"""
        try:
            cipher = self._get_cipher()
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = cipher.decrypt(encrypted_bytes).decode()
            
            parts = decrypted.split("||")
            if len(parts) == 3:
                return parts[0], parts[1], parts[2]  # user_id, password, cert_password
            return None
        except Exception as e:
            self.logger.error(f"복호화 실패: {e}")
            return None
    
    def save_encrypted_credentials(self, filename: str, user_id: str, password: str, cert_password: str):
        """암호화된 인증 정보 저장"""
        try:
            encrypted = self.encrypt_credentials(user_id, password, cert_password)
            if encrypted:
                with open(filename, 'w') as f:
                    # 더미 데이터와 함께 저장 (보안 강화)
                    f.write("# System Configuration File\n")
                    f.write(f"DATA={encrypted}\n")
                    f.write("# End of configuration\n")
                print(f"[성공] 인증 정보가 {filename}에 안전하게 저장되었습니다.")
            else:
                print("[오류] 암호화 실패")
        except Exception as e:
            print(f"[오류] 저장 실패: {e}")
    
    def load_encrypted_credentials(self, filename: str) -> Optional[Tuple[str, str, str]]:
        """암호화된 인증 정보 로드"""
        try:
            if not os.path.exists(filename):
                return None
                
            with open(filename, 'r') as f:
                lines = f.readlines()
                
            for line in lines:
                if line.startswith("DATA="):
                    encrypted_data = line.replace("DATA=", "").strip()
                    return self.decrypt_credentials(encrypted_data)
            
            return None
        except Exception as e:
            self.logger.error(f"로드 실패: {e}")
            return None
    
    def setup_credentials(self, filename: str):
        """대화형 인증 정보 설정"""
        print("[보안] 키움 자동 로그인 설정")
        print("=" * 50)
        
        user_id = input("아이디: ").strip()
        if not user_id:
            print("[오류] 아이디가 필요합니다.")
            return False
            
        password = getpass.getpass("비밀번호: ").strip()
        if not password:
            print("[오류] 비밀번호가 필요합니다.")
            return False
            
        cert_password = getpass.getpass("공인인증서 비밀번호: ").strip()
        if not cert_password:
            print("[오류] 공인인증서 비밀번호가 필요합니다.")
            return False
        
        # 즉시 메모리에서 삭제
        self.save_encrypted_credentials(filename, user_id, password, cert_password)
        
        # 메모리 정리
        user_id = password = cert_password = None
        del user_id, password, cert_password
        
        return True
    
    def get_login_credentials(self, filename: str) -> Optional[Tuple[str, str, str]]:
        """자동 로그인용 인증 정보 가져오기"""
        credentials = self.load_encrypted_credentials(filename)
        if credentials:
            self.logger.info("✅ 인증 정보 로드 성공")
        else:
            self.logger.warning("❌ 인증 정보 로드 실패")
        return credentials

def create_secure_login_file():
    """보안 로그인 파일 생성 도우미"""
    helper = SecureLoginHelper()
    
    # 안전한 파일명 (패턴 인식 방지)
    secure_filename = "local_config.py"
    
    print("\n" + "="*60)
    print("[보안] 키움 OpenAPI 자동 로그인 설정")
    print("="*60)
    print("주의: 이 정보는 암호화되어 저장됩니다.")
    print("주의: 절대 외부로 유출되지 않도록 주의하세요.")
    print("="*60)
    
    if helper.setup_credentials(secure_filename):
        print(f"\n[성공] 설정 완료!")
        print(f"파일 위치: {secure_filename}")
        print("암호화되어 안전하게 저장되었습니다.")
        print("\n중요: 이 파일을 절대 공유하지 마세요!")
        return secure_filename
    else:
        print("\n[실패] 설정 실패")
        return None

if __name__ == "__main__":
    # 설정 도구로 실행
    create_secure_login_file()