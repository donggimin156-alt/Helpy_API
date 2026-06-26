# 성능 테스트 실행 가이드

JMeter 5.6.3 기준. `test_plan.jmx` 하나로 GUI/비GUI 모두 실행 가능하다.

---

## 테스트 시나리오

| 항목 | 값 |
|---|---|
| 대상 | GET /model, GET /chatroom (읽기 전용) |
| 가상 유저 수 | 10명 |
| Ramp-Up | 30초 (3초 간격으로 한 명씩 접속) |
| 반복 횟수 | 5회 |
| Think Time | 요청 사이 500~1500ms 랜덤 대기 |
| 응답시간 기준 | 3000ms 초과 시 Assertion 실패 |

> ⚠️ POST /chatroom/{id}/message/response (LLM 호출)는 부하 테스트 대상에서 제외.  
> 비용 발생 및 응답 지연으로 부하 측정 왜곡 가능.

---

## GUI 실행 (개발·디버깅용)

JMeter를 직접 열어 실시간으로 결과를 확인한다.

```
1. JMeter 실행
2. File → Open → performance/test_plan.jmx 선택
3. HTTP Header Manager 클릭
   → Authorization 값의 토큰 부분을 실제 토큰으로 교체
     (Bearer 실제토큰값 형태)
4. ▶ (Run) 버튼 클릭
5. View Results Tree / Summary Report 에서 실시간 확인
```

> ⚠️ JMeter 공식 권고: GUI 모드는 테스트 **개발·검증용**으로만 사용.  
> 실제 부하 측정은 GUI 렌더링 오버헤드가 없는 비GUI 모드로 실행할 것.

---

## 비GUI 실행 (Jenkins·정확한 부하 측정용)

창 없이 터미널에서 실행한다. 결과가 `.jtl` 파일로 저장된다.

### Windows (로컬)

```bat
:: 프로젝트 루트에서 실행
jmeter -n ^
  -t performance\test_plan.jmx ^
  -l performance\result.jtl ^
  -JAPI_TOKEN=실제토큰값
```

### Mac / Linux (로컬)

```bash
jmeter -n \
  -t performance/test_plan.jmx \
  -l performance/result.jtl \
  -JAPI_TOKEN=실제토큰값
```

### Docker (Jenkins 환경과 동일)

```bash
docker run --rm \
  -v "$(pwd)/performance:/performance" \
  -v "$(pwd)/jmeter_report:/jmeter_report" \
  -e API_TOKEN=실제토큰값 \
  justb4/jmeter \
  -n -t /performance/test_plan.jmx \
  -l /performance/result.jtl \
  -e -o /jmeter_report
```

---

## HTML 리포트 생성

비GUI 실행 후 생성된 `.jtl` 파일로 HTML 리포트를 만든다.

```bash
# 방법 1: 테스트 실행과 동시에 HTML 리포트 생성 (-e -o 플래그)
jmeter -n -t performance/test_plan.jmx -l performance/result.jtl -e -o jmeter_report/

# 방법 2: .jtl 파일이 이미 있는 경우 리포트만 별도 생성
jmeter -g performance/result.jtl -o jmeter_report/
```

리포트 확인: `jmeter_report/index.html` 을 브라우저로 열기

---

## GUI vs 비GUI 비교

| 항목 | GUI 실행 | 비GUI 실행 |
|---|---|---|
| 실행 방법 | JMeter 창 → ▶ 버튼 | 터미널 명령어 |
| 용도 | 개발·디버깅·시나리오 수정 | 실제 부하 측정·CI |
| 정확도 | GUI 렌더링 오버헤드 존재 | 정확한 측정 가능 |
| 결과 확인 | View Results Tree (실시간) | result.jtl → HTML 리포트 |
| 토큰 주입 | Header Manager 에 직접 입력 | `-JAPI_TOKEN=값` 플래그 |

---

## 토큰 주입 방식 (`${__P(API_TOKEN,)}`)

`test_plan.jmx`의 Header Manager에 `Bearer ${__P(API_TOKEN,)}`가 설정되어 있다.

- **GUI 실행**: `${__P(API_TOKEN,)}`가 빈 문자열로 치환된다 → Header Manager에서 직접 토큰 입력
- **비GUI 실행**: `-JAPI_TOKEN=실제토큰` 플래그로 JMeter 속성에 주입 → 자동 치환
- **Jenkins**: `withCredentials`로 `API_TOKEN` 환경변수 주입 → Docker run 시 `-JAPI_TOKEN` 전달
