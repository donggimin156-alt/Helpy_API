# Helpychat API 테스트 자동화 (2차 프로젝트)

pytest + requests 기반의 REST API 기능 테스트 + JMeter 성능 테스트 자동화 프로젝트.

---

## 1차 Page Object Model → 2차 Service Layer Client

> **핵심 메시지: UI든 API든 동일한 캡슐화/계층 분리 사고를 적용한다.**

1차 프로젝트(Selenium E2E)와 2차 프로젝트(API 테스트)는 도구가 다르지만,
설계 철학은 완전히 같다. 아래 표가 그 1:1 대응을 보여준다.

### 계층 구조 대응

| 역할 | 1차 (Selenium + POM) | 2차 (pytest + requests) |
|---|---|---|
| **연결 객체 생성** | `WebDriver` (Firefox 브라우저) | `requests.Session` (HTTP 세션) |
| **기반 클래스** | `BasePage(driver, wait)` | `BaseClient(session, timeout)` |
| **리소스별 클래스** | `ModelPage`, `ChatroomPage` | `ModelApi`, `ChatroomApi` |
| **공통 인증** | `do_login()` → 쿠키 주입 | `set_token()` → Bearer 헤더 주입 |
| **공통 대기** | `WebDriverWait(driver, N)` | `timeout=(CONNECT, READ)` |
| **테스트 파일** | `test_model.py` (UI 조작) | `test_model.py` (HTTP 요청) |
| **공통 준비물** | `conftest.py` (driver, login fixture) | `conftest.py` (auth_client, model_api fixture) |
| **환경 분리** | `settings.py` (URL, 계정) | `settings.py` (URL, 토큰, .env) |
| **CI/CD** | `Jenkinsfile` + Selenium Grid | `Jenkinsfile` + Docker |
| **리포트** | Allure (Epic/Feature/Story/Step) | Allure (동일) |

### 코드 레벨 대응

**기반 클래스 (Base)**

```python
# 1차: pages/base_page.py
class BasePage:
    def __init__(self, driver, wait):
        self.driver = driver   # 연결 객체
        self.wait   = wait     # 대기 설정

# 2차: api/base_client.py
class BaseClient:
    def __init__(self, base_url):
        self.session = requests.Session()  # 연결 객체
        self.timeout = (CONNECT, READ)     # 대기 설정
```

**리소스별 클래스 (Resource Layer)**

```python
# 1차: pages/model_page.py
class ModelPage(BasePage):
    def create_model(self, name):
        self.driver.find_element(...).click()   # UI 조작
        self.driver.find_element(...).send_keys(name)

# 2차: api/model_api.py
class ModelApi(BaseClient):
    def create_model(self, payload):
        return self.post("/model", json=payload)  # HTTP 요청
```

**공통 인증 (Authentication)**

```python
# 1차: 이메일 + 비밀번호 입력 → 로그인 버튼 클릭
do_login(driver, wait)   # 쿠키에 세션 키 주입

# 2차: 토큰 한 줄
client.set_token(API_TOKEN)   # Authorization: Bearer <TOKEN> 헤더 주입
```

**공통 준비물 (conftest.py)**

```python
# 1차: module 단위 드라이버 + 로그인
@pytest.fixture(scope="module")
def login_module(driver_module):
    do_login_cached(driver_module, wait)
    return driver_module, wait

# 2차: session 단위 클라이언트 + 토큰
@pytest.fixture(scope="session")
def model_api():
    client = ModelApi(BASE_API_URL)
    client.set_token(API_TOKEN)
    yield client
    client.close()
```

---

## 프로젝트 구조

```
Helpy_API/
├── api/
│   ├── base_client.py      # requests.Session 기반 공통 클라이언트 (1차 BasePage 대응)
│   ├── model_api.py        # /model 엔드포인트 래퍼
│   ├── chatroom_api.py     # /chatroom 엔드포인트 래퍼
│   └── message_api.py      # /chatroom/{id}/message 래퍼 (LLM 전용 타임아웃)
├── config/
│   ├── settings.py         # .env 우선 + OS 환경변수 fallback, is_production()
│   └── requirements.txt
├── schemas/
│   ├── model_schema.py     # 응답 본문 검증용 Pydantic 모델
│   ├── chatroom_schema.py
│   └── message_schema.py
├── tests/
│   ├── test_model.py       # CRUD 전체 + 성공/검증실패/인증실패 케이스
│   ├── test_chatroom.py    # 핵심 케이스 위주
│   ├── test_message.py     # LLM 특별 취급 (구조만 검증, 내용 미검증)
│   └── test_e2e_flow.py    # 전체 시나리오 스모크 테스트
├── performance/
│   ├── test_plan.jmx       # JMeter 테스트 플랜 (GUI 로 작성)
│   └── README.md           # 비GUI 실행·HTML 리포트 생성 방법
├── conftest.py             # 공통 fixture (API 클라이언트, 데이터 생성/정리)
├── pytest.ini              # 마커 등록, --strict-markers, --alluredir
├── ruff.toml               # 포맷 + 린트 설정
├── Dockerfile              # pytest 실행 환경 (python:3.11-slim)
├── Jenkinsfile             # CI/CD 파이프라인
├── .env.example            # 환경 변수 예시 (실제 .env 는 gitignore)
└── .gitignore
```

---

## 빠른 시작

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에 실제 API_TOKEN 입력
```

### 2. 의존성 설치

```bash
pip install -r config/requirements.txt
```

### 3. 테스트 실행

```bash
# 전체 실행
pytest -v

# 스모크 테스트만 (배포 직후 sanity check)
pytest -m smoke -v

# 파괴적 테스트 제외 (운영 환경 수동 실행 시)
pytest -m "not destructive" -v

# Allure 리포트 생성
pytest -v --alluredir=allure-results
allure serve allure-results
```

### 4. 코드 품질 검사

```bash
ruff format --check .   # 포맷 위반 확인
ruff check .            # 린트 오류 확인
ruff format .           # 포맷 자동 수정
```

### 5. Docker 로 실행

```bash
docker build -t helpychat-api-test .
docker run --env-file .env helpychat-api-test
```

---

## 마커 체계

| 마커 | 의미 | 사용 시점 |
|---|---|---|
| `smoke` | 핵심 경로만 빠르게 검증 | 배포 직후 sanity check |
| `regression` | 전체 기능 검증 | PR 머지 전 |
| `destructive` | 데이터 생성·수정·삭제 | 스테이징 전용, 운영 자동 차단 |

---

## 운영 환경 안전 장치 (2중 방어)

```
1차 (수동): pytest -m "not destructive"  로 명시적 제외
2차 (자동): ENVIRONMENT=production 이면 conftest 가 destructive 테스트를 자동 스킵
            → 명령어를 잘못 입력해도 운영 데이터 파괴 없음
```

---

## CI/CD 파이프라인

```
Checkout → Install → Code Quality → 기능 테스트 → 성능 테스트
                     (ruff 검사)    (Docker+pytest)  (Docker+JMeter)
                                         ↓ 완료 후에만 순차 실행 ↓
                     post: Allure 발행 + JMeter HTML 발행 + Discord 알림 + cleanWs
```

시크릿(토큰, Discord URL)은 Jenkins Credentials → `withCredentials` → OS 환경변수로 주입.
`.env` 는 gitignore 처리, CI 에 절대 올라가지 않는다.

---

## 트러블슈팅 / 알려진 제약

### ✅ 해결됨: Allure·JMeter 리포트가 Jenkins에서 렌더링 안 됨 (CSP)

**현상:** Jenkins HTML Publisher가 발행한 Allure·JMeter 리포트를 열면 차트가 비어있거나 JS 오류 발생.

**원인:** Jenkins 기본 Content Security Policy(CSP)가 인라인 스크립트와 외부 리소스를 차단.

**해결:** Jenkins 시작 시 CSP를 해제하는 Groovy 초기화 스크립트 적용.

```groovy
// $JENKINS_HOME/init.groovy.d/csp.groovy
System.setProperty("hudson.model.DirectoryBrowserSupport.CSP", "")
```

Jenkins 재시작마다 자동 적용된다. (임시 해결인 Script Console 방식과 달리 영구 적용)

---

### ⚠️ 인지된 제약: Allure Overview의 Behaviors 위젯 미표시

**현상:** Allure 리포트 Overview 및 Behaviors 탭에서 `500 / Unexpected token '<', "<!DOCTYPE"... is not valid JSON` 표시.

**원인:**

- allure-pytest가 raw 결과(result.json)에 `epic` / `feature` / `story` 레이블을 정상 생성함 ✓
- Allure CLI 2.40.0이 새 포맷(`widgets/` 디렉토리)으로 리포트를 생성함
- Jenkins Allure 플러그인이 `behaviors.json`을 구 포맷(`data/` 디렉토리) 기준으로 요청 → 302(파일 없음) → HTML 반환 → JSON 파싱 오류

**테스트 결과에 미치는 영향:** 없음. 35 passed 정상 확인, TREND·SUITES·Categories 위젯 모두 정상 작동.

**의도적으로 유지하는 이유:**

Jenkins Allure 플러그인을 구버전으로 다운그레이드하면 현재 정상 작동하는 TREND·SUITES·History 기능이 깨질 수 있다. 이 위젯 하나를 살리기 위한 플러그인 교체는 회귀 위험 대비 효과가 낮다고 판단.

**향후 해결 방안:** Jenkins Allure 플러그인이 Allure 3.x 포맷과 호환되는 버전으로 업데이트되면 자동 해결 예상.
