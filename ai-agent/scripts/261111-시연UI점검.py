#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - smart-voca - Playwright 기반 UI 자동 점검 (시연 리허설용)
# 파일 위치: ai-agent/scripts/261111-시연UI점검.py
#
# 목적: 시연데이터생성.py --reset 으로 생성한 데이터를 기준으로
#      주요 페이지(랜딩·로그인·대시보드·학습·시험·통계·리그·관리자)의
#      HTTP 상태, URL 리다이렉트, 에러 페이지 여부를 자동 점검
#
# 사전 조건:
#   1. 서버 실행: python app.py (포트 5000)
#   2. 시연 데이터: python ai-agent/scripts/시연데이터생성.py --reset
#   3. Playwright 브라우저 설치:
#      - 미설치 시: playwright install
#      - 또는: pip install playwright && playwright install
#
# 사용법:
#   python ai-agent/scripts/261111-시연UI점검.py
#
# 테스트 계정:
#   - 관리자: admin / admin1234
#   - 사용자: minsu / demo1234

import sys
import asyncio
from playwright.async_api import async_playwright

# 색상 코드 (터미널)
GREEN = '\033[92m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'

# 테스트 결과
PASS = f'{GREEN}✅{RESET}'
FAIL = f'{RED}❌{RESET}'

# 테스트 데이터
BASE_URL = 'http://127.0.0.1:5000'
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin1234'
USER_USER = 'minsu'
USER_PASS = 'demo1234'


async def check_server():
    """서버 연결 확인"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            resp = await page.goto(BASE_URL)
            status = resp.status if resp else 0
            await browser.close()
            return status == 200
    except Exception as e:
        print(f'{RED}[서버 확인 실패]{RESET} {e}')
        return False


def is_error_page(title: str, url: str) -> bool:
    """에러 페이지 판별 (제목 또는 URL 기준)"""
    if '오류' in title or '/error' in url:
        return True
    return False


async def test_page(page, url: str, name: str, session_check=False) -> tuple[bool, str]:
    """페이지 점검"""
    try:
        # 페이지 이동
        resp = await page.goto(url, wait_until='networkidle', timeout=10000)

        # 1. HTTP 상태 코드 확인
        if not resp or resp.status != 200:
            status = resp.status if resp else 'No Response'
            return False, f'HTTP {status}'

        # 2. 현재 URL 확인 (예상 밖 리다이렉트)
        current_url = page.url
        if '/login' in current_url and '/login' not in url and session_check:
            return False, f'리다이렉트됨 → {current_url}'

        # 3. 페이지 제목/URL로 에러 판별
        title = await page.title()
        if is_error_page(title, current_url):
            return False, f'에러 페이지 (제목: {title})'

        return True, ''

    except asyncio.TimeoutError:
        return False, '타임아웃 (10초)'
    except Exception as e:
        return False, str(e)[:50]


async def login_admin_in_new_context(page, browser):
    """새 브라우저 컨텍스트에서 관리자 로그인"""
    try:
        # 새 컨텍스트에서 관리자 로그인 (세션 분리)
        ctx = await browser.new_context()
        admin_page = await ctx.new_page()

        # 로그인 페이지로 이동
        await admin_page.goto(f'{BASE_URL}/login')
        await admin_page.wait_for_selector('input[name="username"]', timeout=5000)

        # 관리자 로그인
        await admin_page.fill('input[name="username"]', ADMIN_USER)
        await admin_page.fill('input[name="password"]', ADMIN_PASS)
        await admin_page.click('button[type="submit"]')
        await admin_page.wait_for_load_state('networkidle')

        # 로그인 성공 확인
        admin_ok = '/login' not in admin_page.url

        return admin_page, admin_ok

    except Exception as e:
        raise Exception(f'관리자 로그인 실패: {str(e)[:50]}')


async def run_tests():
    """모든 테스트 실행"""

    print(f'{BOLD}=== 스마트 보카 UI 자동 점검 (시연 리허설) ==={RESET}\n')

    # 1. 서버 확인
    print(f'[사전 확인] 서버 연결 테스트...')
    if not await check_server():
        print(f'{FAIL} 서버 응답 없음')
        print(f'  실행: python app.py (포트 5000)')
        sys.exit(1)
    print(f'{PASS} 서버 정상\n')

    results = []
    expected_count = 15  # 기대 항목 수

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # ===== 비로그인 페이지 =====
            print(f'{BOLD}[비로그인]{RESET}')

            tests = [
                (f'{BASE_URL}/', '랜딩 페이지'),
                (f'{BASE_URL}/login', '로그인 페이지'),
                (f'{BASE_URL}/register', '회원가입 페이지'),
            ]

            for url, name in tests:
                success, reason = await test_page(page, url, name)
                status = PASS if success else f'{FAIL} ({reason})'
                print(f'  {status} {name}')
                results.append((name, success))

            # ===== 사용자 로그인 및 페이지 =====
            print(f'\n{BOLD}[사용자 로그인 & 페이지]{RESET}')

            # 로그인
            await page.goto(f'{BASE_URL}/login')
            await page.wait_for_selector('input[name="username"]', timeout=5000)
            await page.fill('input[name="username"]', USER_USER)
            await page.fill('input[name="password"]', USER_PASS)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')

            # 로그인 성공 확인
            login_ok = '/login' not in page.url
            print(f'  {PASS if login_ok else FAIL} 사용자 로그인 (minsu)')
            results.append(('사용자 로그인', login_ok))

            # 사용자 페이지들
            user_tests = [
                (f'{BASE_URL}/', '대시보드'),
                (f'{BASE_URL}/study', '학습'),
                (f'{BASE_URL}/test', '시험'),
                (f'{BASE_URL}/report', '통계'),
                (f'{BASE_URL}/league', '주간 리그'),
                (f'{BASE_URL}/settings', '설정'),
            ]

            for url, name in user_tests:
                success, reason = await test_page(page, url, name, session_check=True)
                status = PASS if success else f'{FAIL} ({reason})'
                print(f'  {status} {name}')
                results.append((name, success))

            # ===== 관리자 로그인 및 페이지 (새 컨텍스트) =====
            print(f'\n{BOLD}[관리자 로그인 & 페이지]{RESET}')

            try:
                admin_page, admin_ok = await login_admin_in_new_context(page, browser)
                print(f'  {PASS if admin_ok else FAIL} 관리자 로그인 (admin)')
                results.append(('관리자 로그인', admin_ok))

                # 관리자 페이지들
                admin_tests = [
                    (f'{BASE_URL}/admin', '관리자 대시보드'),
                    (f'{BASE_URL}/admin/words', '단어 관리'),
                    (f'{BASE_URL}/admin/users', '사용자 관리'),
                    (f'{BASE_URL}/admin/settings', '관리자 설정'),
                ]

                for url, name in admin_tests:
                    success, reason = await test_page(admin_page, url, name, session_check=True)
                    status = PASS if success else f'{FAIL} ({reason})'
                    print(f'  {status} {name}')
                    results.append((name, success))

            except Exception as e:
                print(f'  {FAIL} 관리자 로그인 실패: {str(e)[:50]}')
                results.append(('관리자 로그인', False))
                # 이후 관리자 페이지 4개를 모두 실패로 기록
                for name in ['관리자 대시보드', '단어 관리', '사용자 관리', '관리자 설정']:
                    results.append((name, False))

        except Exception as e:
            print(f'{FAIL} 예상 밖 에러: {str(e)[:80]}')

        finally:
            await browser.close()

    # ===== 결과 요약 =====
    print(f'\n{BOLD}=== 점검 결과 ==={RESET}')
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed

    print(f'총 {total}개 테스트 (기대: {expected_count}개): {PASS} {passed}개 통과, {FAIL} {failed}개 실패')

    # 기대 항목 수 검증
    if total != expected_count:
        print(f'{FAIL} 기대 항목 수({expected_count}개)와 실제 수({total}개)가 다름!')
        return 1

    if failed > 0:
        print(f'\n{BOLD}실패한 항목:{RESET}')
        for name, ok in results:
            if not ok:
                print(f'  {FAIL} {name}')
        return 1
    else:
        print(f'\n{GREEN}모든 테스트 통과! 시연 준비 완료.{RESET}')
        return 0


if __name__ == '__main__':
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
