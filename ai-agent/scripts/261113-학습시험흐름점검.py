#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-13 - smart-voca - 학습 → 시험(출제 범위 ①②③·동의어 채점·자동 발음) 브라우저 점검 (Playwright + Edge)
# 파일 위치: ai-agent/scripts/261113-학습시험흐름점검.py
"""사용법 (프로젝트 루트에서):
    python ai-agent/scripts/261113-학습시험흐름점검.py [스크린샷_폴더]

임시 폴더에 시연 데이터를 만들고 5099 포트에 서버를 따로 띄운다. 실서버(5000)와 실DB(data/)는 건드리지 않는다.
소리는 headless 라 들을 수 없으므로 speechSynthesis.speak 호출 횟수를 가로채서 센다.
점검 항목이 하나라도 실패하면 종료 코드 1."""
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PORT = 5099
BASE = f'http://127.0.0.1:{PORT}'
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
SHOTS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix='smartvoca_shots_'))
SHOTS.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8')

# speechSynthesis.speak 를 가로채 호출된 문장을 모은다 (실제 소리는 내지 않음)
SPEAK_STUB = """
(() => {
  window.__speak = [];
  const ss = window.speechSynthesis;
  if (ss) {
    Object.defineProperty(ss, 'speak', { value: (u) => { window.__speak.push(u.text); }, configurable: true });
    Object.defineProperty(ss, 'cancel', { value: () => {}, configurable: true });
    Object.defineProperty(ss, 'getVoices', { value: () => [], configurable: true });
  }
})();
"""

results = []


def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))
    print(('  PASS ' if ok else '  FAIL ') + name + (f'  [{detail}]' if detail else ''))


def section(title):
    print(f'\n== {title}')


class Env:
    """임시 DB + 임시 서버"""

    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='smartvoca_e2e_'))
        self.proc = None

    def start(self):
        subprocess.run([sys.executable, str(ROOT / 'ai-agent/scripts/시연데이터생성.py'), '--reset', '--data-dir', str(self.tmp)],
                       check=True, capture_output=True, cwd=ROOT, env={**os.environ, 'PYTHONUTF8': '1'})
        env = {**os.environ, 'PYTHONUTF8': '1', 'PORT': str(PORT), 'HOST': '127.0.0.1', 'DATA_DIR': str(self.tmp),
               'ADMIN_USERNAME': 'admin', 'ADMIN_PASSWORD': 'admin1234'}
        env.pop('FLASK_DEBUG', None)
        self.proc = subprocess.Popen([sys.executable, 'app.py'], cwd=ROOT, env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen(BASE + '/login', timeout=1)
                return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError('임시 서버가 뜨지 않았습니다')

    def stop(self):
        if self.proc:
            self.proc.terminate()          # 이 스크립트가 띄운 프로세스만 종료
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def db(self):
        conn = sqlite3.connect(self.tmp / 'smart_voca.db')
        conn.row_factory = sqlite3.Row
        return conn


def register(page, username):
    page.goto(BASE + '/register')
    page.fill('#username', username)
    page.fill('#display_name', username)
    page.fill('#password', 'pass1234')
    page.fill('#password_confirm', 'pass1234')
    page.click('button[type=submit]')
    page.wait_for_url(lambda url: '/register' not in url)


def pick(page, group, value):
    page.click(f'#{group} label:has(input[value="{value}"])')


def shot(page, name, full_page=False):
    """페이지 전환 애니메이션(페이드인)이 끝난 뒤 스크린샷을 찍는다."""
    page.wait_for_timeout(700)
    page.screenshot(path=str(SHOTS / name), full_page=full_page)


def speak_count(page):
    return page.evaluate('window.__speak.length')


def user_stats(env, username):
    with env.db() as conn:
        return [dict(r) for r in conn.execute(
            """SELECT w.english, w.korean, s.weight, s.last_studied FROM user_word_stats s
               JOIN words w ON w.id = s.word_id WHERE s.user_id = (SELECT id FROM users WHERE username = ?)""", (username,))]


def study_session(page, unknown_first=0, goto=True):
    """학습 화면의 카드를 끝까지 넘긴다. 앞에서 unknown_first 장은 '헷갈려요', 나머지는 '알아요'. (본 단어, 틀린 단어) 를 돌려준다."""
    if goto:
        page.goto(BASE + '/study')
    page.wait_for_selector('#card-area:not(.hidden)')
    total = int(page.inner_text('#progress-text').split('/')[1])
    seen, wrong = [], []
    for i in range(total):
        word = page.inner_text('#english')
        seen.append(word)
        if i < unknown_first:
            wrong.append(word)
            page.click('#btn-unknown')
        else:
            page.click('#btn-know')
        if i < total - 1:
            page.wait_for_function('(n) => document.querySelector("#progress-text").textContent.startsWith(n + " /")', arg=i + 2)
    page.wait_for_selector('#done-area:not(.hidden)')
    return seen, wrong


def asked_word(page):
    text = page.inner_text('#q-text')
    m = re.match(r"^'(.+)'의 (?:뜻은|영문은)\?$", text.strip())
    return m.group(1) if m else text


def solve(page, answer_for):
    """시험 문제를 끝까지 푼다. answer_for(질문 단어) 가 None 이면 첫 보기를 누르고, 문자열이면 단답으로 입력한다.
    [(질문 단어, 피드백 문장)] 을 돌려준다."""
    page.wait_for_selector('#quiz:not(.hidden)')
    log, number = [], 0
    while True:
        number += 1
        # k 번째 문제가 그려질 때까지 기다린다 ("k / 전체"). 직전 시험의 마지막 번호가 남아 있어도 헷갈리지 않는다.
        page.wait_for_function('(k) => document.getElementById("q-count").textContent.startsWith(k + " /")', arg=number)
        word = asked_word(page)
        answer = answer_for(word)
        if page.is_visible('#q-short'):
            page.fill('#q-input', answer)
            page.press('#q-input', 'Enter')
        else:
            page.click('#q-options .option >> nth=0')
        page.wait_for_selector('#btn-next:not(.hidden)')
        log.append((word, page.inner_text('#q-feedback').strip()))
        last = page.get_attribute('#btn-next', 'data-last') == '1'
        page.click('#btn-next')
        if last:
            break
    page.wait_for_selector('#result:not(.hidden)')
    return log


def run():
    env = Env()
    console_errors = []
    try:
        env.start()
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            ctx = browser.new_context(viewport={'width': 1100, 'height': 900})
            ctx.add_init_script(SPEAK_STUB)
            page = ctx.new_page()
            page.on('pageerror', lambda e: console_errors.append(str(e)))
            page.on('console', lambda m: console_errors.append(m.text) if m.type == 'error' else None)

            # ---------------------------------------------------------------- A. 새 사용자: 학습 전 시험 화면
            section('A. 새 사용자 — 학습하기 전 시험 시작 화면')
            register(page, 'e2e_user')
            page.goto(BASE + '/test')
            page.wait_for_selector('[data-scope-count="today"]:not(:empty)')
            check('출제 범위 3택이 보이고 기본값은 ① 오늘 공부한 단어',
                  page.is_checked('input[name=scope][value=today]') and
                  all(t in page.inner_text('#scope') for t in ('오늘 공부한 단어', '지금까지 공부한 단어', '전체 단어')))
            check('①②에만 "학습·시험에서 본 단어 기준" 안내', page.inner_text('#scope').count('학습·시험에서 본 단어 기준') == 2)
            notice = page.inner_text('#scope-notice')
            check('① 범위가 비면 "먼저 학습을 해주세요" 안내 + 시작 버튼 비활성',
                  '먼저 학습을 해주세요' in notice and page.is_disabled('#btn-start') and page.is_visible('#scope-notice a'), notice)
            pick(page, 'scope', 'studied')
            check('② 도 비어 있으면 같은 안내', '먼저 학습을 해주세요' in page.inner_text('#scope-notice') and page.is_disabled('#btn-start'))
            shot(page, '01_시험시작_범위비어있음.png', True)
            pick(page, 'scope', 'all')
            check('③ 전체 단어는 바로 시작할 수 있다', page.is_enabled('#btn-start') and not page.is_visible('#scope-notice'))

            # ---------------------------------------------------------------- B. 학습: 자동 발음 없음 (기본 꺼짐)
            section('B. 학습 화면 — 설정이 꺼져 있을 때')
            page.goto(BASE + '/study')
            page.wait_for_selector('#card-area:not(.hidden)')
            check('카드가 나타나도 자동 재생이 없다 (speak 호출 0회)', speak_count(page) == 0, f'{speak_count(page)}회')
            shot(page, '02_학습카드_자동발음없음.png')
            page.click('#tts-word')
            check('발음 버튼을 누르면 재생된다 (1회)', speak_count(page) == 1, f'{speak_count(page)}회')
            page.keyboard.press('p')
            check('P 단축키를 누르면 재생된다 (2회)', speak_count(page) == 2, f'{speak_count(page)}회')
            before = speak_count(page)
            seen1, wrong1 = study_session(page, unknown_first=3, goto=False)   # 같은 페이지에서 계속 (이동하면 호출 횟수가 초기화됨)
            check('카드 10장을 넘기는 동안 자동 재생이 늘지 않는다', speak_count(page) == before, f'{before}회 -> {speak_count(page)}회')
            check('학습 1회차 기록이 저장됐다 (10단어)', len(user_stats(env, 'e2e_user')) == 10)

            # ---------------------------------------------------------------- C. 설정 스위치
            section('C. 설정 화면 — "카드 넘길 때 자동 발음" 스위치')
            page.goto(BASE + '/settings')
            page.wait_for_selector('#auto_speak')
            page.wait_for_function('() => document.getElementById("daily_target").value !== ""')
            check('스위치 기본값은 꺼짐', not page.is_checked('#auto_speak'))
            shot(page, '03_설정_스위치꺼짐.png', True)
            page.locator('.switch-row').screenshot(path=str(SHOTS / '03b_스위치_꺼짐_확대.png'))
            page.click('label[for=auto_speak]')
            page.click('#settings-form button[type=submit]')
            page.wait_for_selector('.toast', timeout=3000)
            page.reload()
            page.wait_for_function('() => document.getElementById("daily_target").value !== ""')
            check('켜고 저장하면 새로고침해도 유지된다', page.is_checked('#auto_speak'))
            shot(page, '04_설정_스위치켜짐.png', True)
            page.locator('.switch-row').screenshot(path=str(SHOTS / '04b_스위치_켜짐_확대.png'))

            # ---------------------------------------------------------------- D. 스위치를 켜면 자동 재생
            section('D. 학습 화면 — 스위치를 켠 뒤')
            page.goto(BASE + '/study')
            page.wait_for_selector('#card-area:not(.hidden)')
            check('첫 카드가 나타날 때 자동 재생 (1회)', speak_count(page) == 1, f'{speak_count(page)}회')
            before = speak_count(page)
            seen2, wrong2 = [], []
            for i in range(10):                                  # 앞의 3장(이전에 틀린 단어)은 다시 '헷갈려요'
                word = page.inner_text('#english')
                seen2.append(word)
                if i < 3:
                    wrong2.append(word)
                    page.click('#btn-unknown')
                else:
                    page.click('#btn-know')
                if i == 2:
                    check('카드를 넘길 때마다 자동 재생된다', speak_count(page) == before + 3, f'3장 넘긴 뒤 {speak_count(page)}회')
            page.wait_for_selector('#done-area:not(.hidden)')
            check('이전에 틀린 단어가 학습 맨 앞에 다시 나온다', set(wrong2) == set(wrong1), f'{sorted(wrong2)}')
            check('10장 모두 자동 재생됐다 (카드 수 = 재생 횟수)', speak_count(page) == before + 9, f'{speak_count(page)}회')
            stats = user_stats(env, 'e2e_user')
            n_studied = len(stats)
            check('학습 2회차까지 단어 17개가 기록됐다', n_studied == 17, f'{n_studied}개')

            # ---------------------------------------------------------------- E. 틀린 단어 우선 (① 오늘 / 5문제)
            section('E. 시험 ① 오늘 공부한 단어 — 틀린 단어 우선')
            korean = {r['english']: r['korean'] for r in env.db().execute('SELECT english, korean FROM words')}
            page.goto(BASE + '/test')
            page.wait_for_selector('[data-scope-count="today"]:not(:empty)')
            check('범위별 단어 수가 보인다 (오늘 17 / 지금까지 17)',
                  page.inner_text('[data-scope-count="today"]') == '(17)' and page.inner_text('[data-scope-count="studied"]') == '(17)')
            pick(page, 'mode', '영->한')
            pick(page, 'format', '단답형')
            page.select_option('#num', '5')
            page.click('#btn-start')
            log = solve(page, lambda w: korean[w])
            asked = {w for w, _ in log}
            check('① 5문제 모두 오늘 공부한 단어에서 출제', asked <= {r['english'] for r in stats}, f'{sorted(asked)}')
            check('오답이 많은 단어(weight 높은 순) 3개가 반드시 포함', set(wrong2) <= asked, f'틀린 단어 {sorted(wrong2)}')
            page.click('#btn-retry')

            # ---------------------------------------------------------------- F. ① 오늘 / 어제 공부한 단어 6개 만들기
            section('F. 시험 ① 오늘 — 단어가 요청보다 적을 때')
            with env.db() as conn:                                # 오늘 본 단어 중 6개를 '어제' 본 것으로 바꿔 ①과 ②를 구분한다
                rows = conn.execute(
                    """SELECT s.word_id, w.english FROM user_word_stats s JOIN words w ON w.id = s.word_id
                       WHERE s.user_id = (SELECT id FROM users WHERE username = 'e2e_user') AND s.weight = 0
                       ORDER BY s.word_id LIMIT 6""").fetchall()
                for r in rows:
                    conn.execute("UPDATE user_word_stats SET last_studied = ? WHERE word_id = ? AND user_id = "
                                 "(SELECT id FROM users WHERE username = 'e2e_user')", (YESTERDAY, r['word_id']))
                conn.commit()
            old_words = {r['english'] for r in rows}
            page.goto(BASE + '/test')
            page.wait_for_selector('[data-scope-count="today"]:not(:empty)')
            check('범위 숫자가 ① 11 / ② 17 로 구분된다',
                  page.inner_text('[data-scope-count="today"]') == '(11)' and page.inner_text('[data-scope-count="studied"]') == '(17)',
                  f"① {page.inner_text('[data-scope-count=today]')} ② {page.inner_text('[data-scope-count=studied]')}")
            pick(page, 'mode', '영->한')
            pick(page, 'format', '4지선다형')
            page.select_option('#num', '20')
            notice = page.inner_text('#scope-notice')
            check('문제 수보다 단어가 적으면 안내', '11개뿐' in notice and '11문제만' in notice, notice)
            shot(page, '05_시험시작_범위선택_부족안내.png', True)
            page.click('#btn-start')
            page.wait_for_selector('#quiz:not(.hidden)')
            check('시작할 때 "단어가 부족해서 11문제만" 알림', '11문제만' in ' '.join(page.locator('.toast').all_inner_texts()))
            shot(page, '06_시험문제_4지선다.png')
            log = solve(page, lambda w: None)
            asked = [w for w, _ in log]
            today_words = {r['english'] for r in stats} - old_words
            check('① 11문제만 출제되고 모두 오늘 공부한 단어', len(asked) == 11 and set(asked) <= today_words, f'{len(asked)}문제')
            check('어제 공부한 단어는 ① 에 나오지 않는다', not (set(asked) & old_words))
            shot(page, '07_시험결과_오늘범위.png', True)
            page.click('#btn-retry')

            # ---------------------------------------------------------------- G. ② 지금까지 공부한 단어
            section('G. 시험 ② 지금까지 공부한 단어')
            page.wait_for_selector('[data-scope-count="today"]:not(:empty)')
            pick(page, 'scope', 'studied')
            pick(page, 'mode', '영->한')
            pick(page, 'format', '4지선다형')
            page.select_option('#num', '20')
            page.click('#btn-start')
            log = solve(page, lambda w: None)
            asked = [w for w, _ in log]
            studied_all = {r['english'] for r in stats}
            check('② 17문제 출제, 모두 학습·시험에서 본 단어', len(asked) == 17 and set(asked) <= studied_all, f'{len(asked)}문제')
            check('어제 공부한 단어 6개도 ② 에는 나온다', old_words <= set(asked))
            options_ok = True
            page.click('#btn-retry')

            # ---------------------------------------------------------------- H. ③ 전체 단어
            section('H. 시험 ③ 전체 단어')
            page.wait_for_selector('[data-scope-count="today"]:not(:empty)')
            pick(page, 'scope', 'all')
            pick(page, 'mode', '영->한')
            pick(page, 'format', '4지선다형')
            page.select_option('#num', '30')              # ③ 도 오답이 많은 단어를 먼저 뽑으므로, 공부한 17개보다 많이 요청해 안 본 단어가 섞이는지 본다
            check('③ 전체 단어 수가 2283 으로 보인다', page.inner_text('[data-scope-count="all"]') == '(2283)')
            shot(page, '08_시험시작_전체단어선택.png', True)
            page.click('#btn-start')
            log = solve(page, lambda w: None)
            asked = [w for w, _ in log]
            outside = [w for w in asked if w not in studied_all]
            check('③ 30문제 출제 — 공부한 단어(최대 17개) 외에 아직 안 본 단어가 13개 이상',
                  len(asked) == 30 and len(outside) >= 13, f'공부 안 한 단어 {len(outside)}개')

            # ---------------------------------------------------------------- I. 동의어 채점
            section('I. 한→영 단답형 — 동의어 정답 처리')
            ctx2 = browser.new_context(viewport={'width': 1100, 'height': 900})
            ctx2.add_init_script(SPEAK_STUB)
            page2 = ctx2.new_page()
            register(page2, 'e2e_syn')
            with env.db() as conn:                                # 뜻이 같은 두 단어(evident/obvious)만 오늘 공부한 것으로 만든다
                uid = conn.execute("SELECT id FROM users WHERE username = 'e2e_syn'").fetchone()[0]
                for en in ('evident', 'obvious'):
                    wid = conn.execute("SELECT id FROM words WHERE english = ?", (en,)).fetchone()[0]
                    conn.execute("INSERT INTO user_word_stats(user_id, word_id, weight, success_count, fail_count, last_studied) "
                                 "VALUES(?,?,0,1,0,date('now','localtime'))", (uid, wid))
                conn.commit()
            page2.goto(BASE + '/test')
            page2.wait_for_selector('[data-scope-count="today"]:not(:empty)')
            check('① 범위는 2단어 (evident, obvious)', page2.inner_text('[data-scope-count="today"]') == '(2)')
            pick(page2, 'mode', '한->영')
            pick(page2, 'format', '단답형')
            page2.select_option('#num', '5')
            page2.click('#btn-start')
            page2.wait_for_selector('#quiz:not(.hidden)')
            feedbacks, shot_taken = [], False
            while True:
                page2.wait_for_selector('#q-count')
                check_q = page2.inner_text('#q-text')
                page2.fill('#q-input', 'evident')              # 두 문제 모두 evident 를 입력 -> 하나는 정답, 하나는 동의어
                page2.press('#q-input', 'Enter')
                page2.wait_for_selector('#btn-next:not(.hidden)')
                fb = page2.inner_text('#q-feedback').strip()
                feedbacks.append(fb)
                if '정답 처리' in fb and not shot_taken:
                    shot(page2, '09_동의어_정답처리.png')
                    shot_taken = True
                last = page2.get_attribute('#btn-next', 'data-last') == '1'
                page2.click('#btn-next')
                if last:
                    break
            page2.wait_for_selector('#result:not(.hidden)')
            check('"명백한" 두 문제에 evident 를 입력 -> 모두 정답 (정답 1 + 동의어 정답 1)',
                  page2.inner_text('#r-summary').startswith('2문제 중 2문제'), page2.inner_text('#r-summary'))
            check('동의어로 맞힌 문제에 "정답 처리 (출제 단어: obvious)" 표시',
                  any('정답 처리 (출제 단어: obvious)' in f for f in feedbacks) and any('정답이에요' in f for f in feedbacks), str(feedbacks))
            result_text = page2.inner_text('#r-list')
            check('결과 화면에도 "정답 처리 (출제 단어: obvious) · 내 답: evident"', '정답 처리 (출제 단어: obvious) · 내 답: evident' in result_text)
            shot(page2, '10_동의어_결과화면.png', True)

            # ---------------------------------------------------------------- J. 모바일 화면
            section('J. 모바일(390px) 시험 시작 화면')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.goto(BASE + '/test')
            page.wait_for_selector('[data-scope-count="today"]:not(:empty)')
            shot(page, '11_모바일_시험시작.png', True)
            overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
            check('가로로 넘치지 않는다', not overflow)

            check('브라우저 콘솔 오류·예외가 없다', not console_errors, '; '.join(console_errors[:3]))
            browser.close()
    finally:
        env.stop()

    failed = [r for r in results if not r[1]]
    print(f'\n결과: {len(results) - len(failed)} / {len(results)} 통과')
    print(f'스크린샷: {SHOTS}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(run())
