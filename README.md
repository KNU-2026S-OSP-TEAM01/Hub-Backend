# OpenPark — Hub Server

> KNU-2026S-OSP-TEAM01

일반 사용자에게 주차장 현황을 제공하는 공개 API 서버입니다.  
PLS(Parking Lot Server)의 DB를 직접 공유하며, 인증 없이 주차장 목록과 실시간 잔여 면수를 제공합니다.

---

## 프로젝트 구조

```
Hub-Backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/          # 읽기 전용 ORM 모델 (PLS DB 참조)
│   ├── schemas/         # 응답 스키마
│   └── routers/         # API 엔드포인트
├── tests/
├── docs/
│   ├── hub-analysis.md                      # 요구사항 분석
│   ├── plan/hub-server-implementation-plan.md
│   ├── ref/integration-test-guide.md        # PLS 연동 테스트 가이드
│   └── result/hub-server-v1.md              # v1 구현 결과
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 기술 스택

- **언어/프레임워크**: Python 3.12 / FastAPI
- **DB**: PLS의 PostgreSQL 16 직접 참조 (읽기 전용)
- **인증**: 없음 (공개 API)

---

## 빠른 시작

```bash
# 환경 설정
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env

# 로컬 직접 실행 (PLS DB가 localhost:5432에 실행 중이어야 함)
uvicorn app.main:app --port 8001 --reload
```

Swagger UI: `http://localhost:8001/docs`

---

## 환경변수

| 변수 | 설명 |
|------|------|
| `DATABASE_URL` | PLS PostgreSQL 연결 URL |
| `TEST_DATABASE_URL` | Hub 전용 테스트 DB URL (포트 5434) |
| `FRONTEND_URL` | CORS 허용할 FE 출처. 비어 있으면 CORS 미적용 |

---

## API

| Method | Path | 인증 | 설명 |
|--------|------|------|------|
| GET | `/api/v1/lots` | 없음 | 주차장 목록 |
| GET | `/api/v1/lots/{lot_id}` | 없음 | 주차장 단건 |

---

## Docker 실행

PLS DB가 먼저 실행 중이어야 합니다.

```bash
docker compose up hub -d
```

Hub 컨테이너는 `host.docker.internal:5432`를 통해 PLS DB에 접근합니다.

> Linux에서는 `docker-compose.yml`에 `extra_hosts: - "host.docker.internal:host-gateway"`가 포함되어 있어야 합니다. 현재 파일에 이미 선언되어 있습니다.

---

## 테스트

Hub 전용 테스트 DB를 먼저 기동합니다.

```bash
docker compose up db_test -d
.\.venv\Scripts\Activate.ps1
python -m pytest
```

---

## PLS 연동 테스트

실제 PLS DB와 연동하는 수동 테스트 절차는 아래 문서를 참고합니다.

> `docs/ref/integration-test-guide.md`

---

## 라이선스

MIT
