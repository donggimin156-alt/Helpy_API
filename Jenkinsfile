// Jenkinsfile
// ============================================================
// Helpychat API 테스트 자동화 CI/CD 파이프라인 (Declarative Pipeline)
//
// 파이프라인 흐름:
//   Checkout → Install → Code Quality → 기능 테스트 → 성능 테스트
//
// 핵심 설계 결정:
//   1. 성능 테스트는 기능 테스트가 완전히 끝난 뒤 순차 실행
//      (부하가 기능 테스트를 방해하지 않도록. 동시 실행 금지)
//   2. 시크릿(토큰, URL)은 Jenkins Credentials 에 저장
//      → withCredentials 로 OS 환경변수 주입
//      → .env 는 gitignore, CI 에 절대 올라가지 않음
//   3. 기능 테스트는 Docker(helpychat-api-test 이미지)에서 실행
//   4. 성능 테스트는 Docker(justb4/jmeter 공개 이미지)에서 실행
//   5. Windows Jenkins → bat 명령 사용 (sh 대신)
//
// 필요한 Jenkins 플러그인:
//   - Allure Jenkins Plugin    : 기능 테스트 리포트 발행
//   - HTML Publisher Plugin    : JMeter 성능 리포트 발행
//   - Discord Notifier Plugin  : 빌드 결과 Discord 알림
//   - Docker Pipeline Plugin   : Docker 컨테이너 실행
//
// 필요한 Jenkins Credentials (Manage Jenkins → Credentials):
//   - HELPYCHAT_API_TOKEN    (Secret text) : Bearer 인증 토큰
//   - HELPYCHAT_ENVIRONMENT  (Secret text) : staging / production
//   - DISCORD_WEBHOOK_URL    (Secret text) : Discord Webhook URL
// ============================================================

pipeline {
    agent any

    options {
        disableConcurrentBuilds()   // 동시 빌드 방지 — 성능 테스트 부하 충돌 예방
        timestamps()                // 각 로그 줄에 타임스탬프 출력
        timeout(time: 30, unit: 'MINUTES')  // 전체 파이프라인 타임아웃
    }

    stages {

        // ── 1. Checkout ───────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // ── 2. Install ────────────────────────────────────────
        // Docker 이미지를 빌드한다.
        // Python 의존성(requirements.txt)은 이미지 레이어에 캐싱되므로
        // 의존성 변경이 없으면 빠르게 완료된다.
        stage('Install') {
            steps {
                bat 'docker build -t helpychat-api-test .'
            }
        }

        // ── 3. Code Quality ───────────────────────────────────
        // ruff format --check : 포맷 위반 파일 검출 (수정 없이 검사만)
        // ruff check          : 린트 오류 검출 (미사용 import, 미정의 변수 등)
        // 하나라도 실패하면 이후 스테이지는 실행되지 않는다.
        stage('Code Quality') {
            steps {
                bat 'docker run --rm helpychat-api-test ruff format --check .'
                bat 'docker run --rm helpychat-api-test ruff check .'
            }
        }

        // ── 4. 기능 테스트 ─────────────────────────────────────
        // pytest + requests 를 Docker 컨테이너 안에서 실행한다.
        // 인증 토큰과 실행 환경은 Jenkins Credentials → OS 환경변수로 주입한다.
        // Allure 결과 파일은 볼륨 마운트로 호스트에 저장 → post 에서 리포트 발행.
        stage('기능 테스트') {
            steps {
                withCredentials([
                    string(credentialsId: 'HELPYCHAT_API_TOKEN',   variable: 'API_TOKEN'),
                    string(credentialsId: 'HELPYCHAT_ENVIRONMENT',  variable: 'ENVIRONMENT')
                ]) {
                    bat '''
                        docker run --rm ^
                          -e API_TOKEN=%API_TOKEN% ^
                          -e ENVIRONMENT=%ENVIRONMENT% ^
                          -v "%WORKSPACE%\\allure-results:/app/allure-results" ^
                          helpychat-api-test ^
                          pytest -v -m "smoke and not destructive" --alluredir=allure-results
                    '''
                }
            }
        }

        // ── 5. 성능 테스트 ─────────────────────────────────────
        // JMeter 공개 이미지(justb4/jmeter)를 사용해 비GUI 모드로 실행한다.
        // -n        : 비GUI(Non-GUI) 모드
        // -t        : 테스트 플랜(.jmx) 경로
        // -l        : 결과 로그(.jtl) 저장 경로
        // -e -o     : 테스트 완료 후 HTML 리포트 즉시 생성
        //
        // ⚠️ 이 스테이지는 기능 테스트가 완료된 뒤에만 실행된다.
        //    성능 테스트 부하 강도는 이이측 확인 후 조정할 것.
        stage('성능 테스트') {
            steps {
                withCredentials([
                    string(credentialsId: 'HELPYCHAT_API_TOKEN', variable: 'API_TOKEN')
                ]) {
                    bat '''
                        docker run --rm ^
                          -e API_TOKEN=%API_TOKEN% ^
                          -v "%WORKSPACE%\\performance:/performance" ^
                          -v "%WORKSPACE%\\jmeter_report:/jmeter_report" ^
                          justb4/jmeter ^
                          -n -t /performance/test_plan.jmx ^
                          -l /performance/result.jtl ^
                          -e -o /jmeter_report
                    '''
                }
            }
        }

    }

    post {

        // ── always: 성공·실패 관계없이 항상 실행 ─────────────
        always {
            // 기능 테스트 Allure 리포트 발행
            allure([
                includeProperties: false,
                reportBuildPolicy: 'ALWAYS',
                results          : [[path: 'allure-results']]
            ])

            // 성능 테스트 JMeter HTML 리포트 발행
            publishHTML([
                allowMissing         : true,   // jmeter_report 없어도 오류 미발생
                alwaysLinkToLastBuild: true,
                keepAll              : true,
                reportDir            : 'jmeter_report',
                reportFiles          : 'index.html',
                reportName           : 'JMeter 성능 테스트 리포트'
            ])

            // 워크스페이스 정리 (리포트 발행 후 마지막에 실행)
            cleanWs()
        }

        // ── success: 빌드 성공 시 Discord 알림 ───────────────
        success {
            withCredentials([
                string(credentialsId: 'DISCORD_WEBHOOK_URL', variable: 'DISCORD_URL')
            ]) {
                discordSend(
                    webhookURL  : env.DISCORD_URL,
                    title       : "✅ [${env.JOB_NAME}] 빌드 #${env.BUILD_NUMBER} 성공",
                    description : "기능 테스트 + 성능 테스트 모두 통과",
                    link        : env.BUILD_URL,
                    result      : currentBuild.currentResult
                )
            }
        }

        // ── failure: 빌드 실패 시 Discord 알림 ───────────────
        failure {
            withCredentials([
                string(credentialsId: 'DISCORD_WEBHOOK_URL', variable: 'DISCORD_URL')
            ]) {
                discordSend(
                    webhookURL  : env.DISCORD_URL,
                    title       : "❌ [${env.JOB_NAME}] 빌드 #${env.BUILD_NUMBER} 실패",
                    description : "Allure 리포트에서 실패 원인을 확인하세요.",
                    link        : env.BUILD_URL,
                    result      : currentBuild.currentResult
                )
            }
        }

    }
}
