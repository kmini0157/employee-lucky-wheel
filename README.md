# 출근 행운 룰렛 - 서버 관리 버전

브라우저 로컬 저장이 아니라 **서버 + SQLite DB**로 참여 기록을 관리하는 버전입니다.

## 들어간 기능

- 사번 입력 후 하루 1회 룰렛 참여
- 결과 확률 유지
  - 운세 90%
  - 3000 Will 7%
  - 커피 기프티콘 3%
- 서버 DB 저장
- 관리자 로그인
- 관리자 대시보드
  - 오늘 참여 수
  - 오늘 운세/3000 Will/커피 개수
  - 미수령 경품 수
  - 최근 참여 내역
  - 당첨자 수령 처리
  - CSV 다운로드

## 폴더 구조

- `app.py` : Flask 서버
- `templates/index.html` : 사용자 페이지
- `templates/admin_login.html` : 관리자 로그인
- `templates/admin_dashboard.html` : 관리자 대시보드
- `requirements.txt` : Python 패키지
- `.env.example` : 환경변수 예시

## 실행 방법

### 1) 가상환경 생성
Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) 패키지 설치
```bash
pip install -r requirements.txt
```

### 3) 환경변수 설정
`.env.example` 내용을 참고해서 환경변수를 설정하세요.

Windows PowerShell:
```powershell
$env:FLASK_SECRET_KEY="your-secret"
$env:ADMIN_PASSWORD="your-admin-password"
$env:PORT="5000"
```

macOS / Linux:
```bash
export FLASK_SECRET_KEY="your-secret"
export ADMIN_PASSWORD="your-admin-password"
export PORT="5000"
```

### 4) 서버 실행
```bash
python app.py
```

브라우저 접속:
- 사용자 페이지: `http://localhost:5000/`
- 관리자 페이지: `http://localhost:5000/admin`

## 운영 시 권장 사항

- 기본 관리자 비밀번호 `change-me`는 반드시 변경
- 사번 직접 입력 대신 사내 SSO 또는 HR 시스템 검증 API 연동 권장
- SQLite는 소규모 내부 이벤트에는 충분하지만, 참여자가 많아지면 PostgreSQL/MySQL 전환 권장
- 사내 배포 시 Nginx + Gunicorn 조합 권장

## 실제 배포 예시

### Gunicorn
```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

### Nginx 리버스 프록시
사내 서버 또는 VM 앞단에 Nginx를 두고 Flask 앱으로 프록시하면 됩니다.

## 데이터베이스

최초 실행 시 `lucky_wheel.db` 파일이 자동 생성됩니다.

테이블:
- `spins`
  - 사번
  - 참여일자
  - 결과 종류
  - 메시지
  - 수령코드
  - 파워
  - 수령 여부
  - 참여 시각

같은 사번은 같은 날짜에 한 번만 저장되도록 `UNIQUE(employee_id, spin_date)` 제약이 걸려 있습니다.

## 다음 단계로 붙이기 좋은 것

- 사내 SSO 로그인
- 사번 검증 API
- 관리자 권한 다중 계정
- 지급 완료 이력 / 메모
- 3000 Will, 커피 지급 자동화
- 실사용 URL 기반 최종 QR 코드 생성

## Render 배포용 권장값

Render에 배포할 때는 아래처럼 설정하면 됩니다.

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Health Check Path: `/healthz`
- Environment Variables:
  - `FLASK_SECRET_KEY`
  - `ADMIN_PASSWORD`
  - `DB_PATH=/var/data/lucky_wheel.db`
- Persistent Disk:
  - Mount Path: `/var/data`

이렇게 하면 SQLite DB 파일이 디스크에 저장되어 재배포 후에도 기록이 유지됩니다.
