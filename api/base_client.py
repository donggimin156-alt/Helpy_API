# api/base_client.py
# ============================================================
# HTTP API 요청의 핵심 기반 클래스
#
# [1차 Selenium 대응 — 3개 파일을 하나로 통합]
#
#   1. config/browser_factory.py  → __init__ 의 Session 생성 로직
#      Selenium : make_firefox_driver() 로 브라우저 인스턴스를 만들었다
#      API      : requests.Session() 으로 HTTP 세션 인스턴스를 만든다
#      공통점   : "반복 사용할 연결 객체를 초기화한다"
#
#   2. pages/base_page.py         → get / post / patch / delete 메서드
#      Selenium : click(), wait_for_element() 등 브라우저 조작 공통 메서드
#      API      : get(), post() 등 HTTP 요청 공통 메서드
#      공통점   : "모든 페이지(클라이언트)가 상속해서 재사용하는 기반"
#
#   3. config/login_helpers.py    → set_token() 을 통한 인증 주입
#      Selenium : do_login() 이 driver 에 쿠키를 심었다
#      API      : set_token() 이 Session 헤더에 Bearer 토큰을 심는다
#      공통점   : "이후 요청이 인증 상태를 유지하도록 만든다"
# ============================================================

import logging  # 요청/응답 로깅용

import requests  # Python 표준 HTTP 클라이언트 라이브러리

from config.settings import CONNECT_TIMEOUT, READ_TIMEOUT  # 타임아웃 상수 재사용

logger = logging.getLogger(__name__)  # 모듈 이름으로 logger 생성 (계층 로깅)


class BaseClient:
    """
    모든 API 클라이언트가 상속하는 기반 클래스.

    [1차 Selenium 대응]
      Selenium의 BasePage(driver, wait) 와 동일한 역할.
      - BasePage 는 driver 를 받아서 브라우저 조작 메서드를 제공했다.
      - BaseClient 는 session 을 직접 생성하고 HTTP 조작 메서드를 제공한다.

    핵심 개념 — requests.Session:
      Session 을 사용하면 동일한 연결에서 쿠키·헤더·인증 정보가 유지된다.
      브라우저가 로그인 후 쿠키를 계속 들고 다니는 것과 같은 원리.
    """

    def __init__(self, base_url: str):
        """
        Parameters
        ----------
        base_url : str
            이 클라이언트가 호출할 API 서버의 루트 URL.
            예) "https://dev-v2-community-api.dev.elicer.io"

        [1차 Selenium 대응]
            BasePage.__init__(self, driver, wait) 와 대응.
            driver  → self.session  (조작 도구 객체)
            wait    → self.timeout  (대기/타임아웃 설정)
            base_url 은 Selenium 에선 settings.py 의 BASE_URL 로 분산돼 있었다.
        """
        self.base_url = base_url.rstrip("/")  # 끝에 슬래시 제거 (URL 중복 방지)

        # requests.Session — 연결 풀 + 공통 헤더/쿠키를 재사용하는 객체
        # Selenium의 WebDriver 인스턴스에 대응
        self.session = requests.Session()

        # 모든 요청에 기본으로 붙는 헤더 설정
        # Content-Type: application/json    → 요청 본문이 JSON 형식임을 서버에 알림
        # Accept: application/json          → 서버에게 JSON 응답을 원한다고 알림
        # x-elice-org-name-short: qaproject → ACL 체크에 필요한 조직 식별자
        #   브라우저는 자동 전송하지만 requests 에서는 수동으로 추가해야 함
        #   없으면 /acl/community/get/ 에서 403 → 409 응답
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-elice-org-name-short": "qaproject",
            }
        )

        # (CONNECT_TIMEOUT, READ_TIMEOUT) 튜플로 타임아웃 설정
        # 모든 _request() 호출에 자동 적용됨
        self.timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        logger.debug(f"BaseClient 초기화 완료 → base_url={self.base_url}")

    # ── 인증 토큰 관리 ─────────────────────────────────────────────

    def set_token(self, token: str):
        """
        Session 헤더에 Bearer 토큰을 주입한다.
        이후의 모든 요청에 Authorization 헤더가 자동으로 붙는다.

        [1차 Selenium 대응]
            login_helpers.do_login() 이 WebDriver 쿠키에 eliceSessionKey 를 주입한 것과 동일.
            Selenium : driver.add_cookie({"name": "eliceSessionKey", "value": token})
            API      : session.headers["Authorization"] = f"Bearer {token}"
            공통점   : "이후 요청이 인증된 상태로 서버에 도달하게 만든다"

        Parameters
        ----------
        token : str
            로그인 API 에서 받은 액세스 토큰 문자열.
        """
        self.session.headers["Authorization"] = f"Bearer {token}"
        # dev 서버 ACL은 브라우저 쿠키 세션(eliceSessionKey)을 함께 검증한다.
        # Bearer 토큰만으로는 no_account_api_session 오류 발생 → 쿠키도 병행 주입
        self.session.cookies.set("eliceSessionKey", token)
        logger.debug("Authorization 토큰 주입 완료")

    def clear_token(self):
        """
        토큰을 제거하여 비인증 상태로 되돌린다.

        [1차 Selenium 대응]
            Selenium 에서는 driver.delete_all_cookies() 로 로그아웃 상태를 만들었다.
            API 에서는 헤더에서 Authorization 키를 제거하면 동일한 효과.
        """
        self.session.headers.pop("Authorization", None)
        self.session.cookies.clear()
        logger.debug("Authorization 토큰 제거 완료")

    # ── 내부 공통 요청 메서드 ──────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """
        모든 HTTP 요청의 단일 진입점.
        URL 조합, 타임아웃 주입, 에러 로깅을 중앙에서 처리한다.

        [1차 Selenium 대응]
            BasePage._wait_and_find() 처럼 공통 로직을 한 곳에 모아두는 패턴.
            개별 get/post/patch/delete 메서드가 이 메서드를 호출한다.

        Parameters
        ----------
        method : str
            HTTP 메서드 문자열. "GET" | "POST" | "PATCH" | "DELETE"
        path : str
            base_url 에 붙는 경로. 예) "/api/v1/users/me"
        **kwargs :
            requests.Session.request() 에 그대로 전달되는 추가 인자.
            주로 json= (요청 본문), params= (쿼리스트링) 를 사용.

        Returns
        -------
        requests.Response
            서버의 응답 객체. .status_code, .json(), .text 로 내용을 꺼낸다.
        """
        url = f"{self.base_url}{path}"  # base_url + path 조합 → 완전한 URL 생성
        logger.info(f"→ {method.upper()} {url}")

        # kwargs에 timeout이 없을 때만 기본값 주입 (테스트에서 개별 override 가능)
        kwargs.setdefault("timeout", self.timeout)

        response = self.session.request(method, url, **kwargs)

        logger.info(f"← {response.status_code} {response.url}")
        return response

    # ── 공개 HTTP 메서드 ───────────────────────────────────────────

    def get(self, path: str, **kwargs) -> requests.Response:
        """
        GET 요청 — 데이터 조회.

        [1차 Selenium 대응]
            driver.get(URL) 로 페이지를 로드하던 것과 유사하지만,
            브라우저 렌더링 없이 서버 데이터만 JSON으로 가져온다.

        사용 예시:
            response = self.get("/api/v1/users/me")
            user_data = response.json()
        """
        return self._request("GET", path, **kwargs)

    def post(self, path: str, json: dict = None, **kwargs) -> requests.Response:
        """
        POST 요청 — 데이터 생성 또는 액션 실행 (로그인, 생성 등).

        [1차 Selenium 대응]
            login_helpers.do_login() 이 브라우저 폼을 제출하던 것을
            직접 HTTP POST 요청으로 대체한다.

            Selenium : 이메일 입력 → 비밀번호 입력 → 로그인 버튼 클릭
            API      : {"loginId": "...", "password": "..."} 를 POST

        Parameters
        ----------
        json : dict
            요청 본문으로 보낼 딕셔너리. requests 가 자동으로 JSON 직렬화.
        """
        return self._request("POST", path, json=json, **kwargs)

    def patch(self, path: str, json: dict = None, **kwargs) -> requests.Response:
        """
        PATCH 요청 — 리소스 일부 수정.

        [1차 Selenium 대응]
            mypage, settings 테스트에서 입력창에 값을 바꾸고 저장 버튼을 클릭하던 것.
            Selenium : 필드 클릭 → 값 입력 → 저장 버튼 클릭 → URL/텍스트 변화 검증
            API      : PATCH + {"field": "new_value"} → 응답 상태코드 검증
        """
        return self._request("PATCH", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        """
        DELETE 요청 — 리소스 삭제.

        [1차 Selenium 대응]
            mypage_withdraw 테스트에서 회원 탈퇴 버튼을 클릭하던 것.
        """
        return self._request("DELETE", path, **kwargs)

    # ── 세션 정리 ──────────────────────────────────────────────────

    def close(self):
        """
        HTTP 세션을 닫고 연결을 반환한다.

        [1차 Selenium 대응]
            Selenium conftest 의 driver.quit() 과 동일한 역할.
            conftest의 _provide_driver() 가 finally 블록에서 quit() 했듯이,
            API conftest 에서도 fixture 종료 시 이 메서드를 호출해야 한다.
        """
        self.session.close()
        logger.debug("HTTP 세션 종료")
