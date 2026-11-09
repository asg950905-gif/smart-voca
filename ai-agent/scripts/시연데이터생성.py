#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 시연용 샘플 데이터 생성 (계정·단어 100개·최근 14일 학습/시험 기록)
# 파일 위치: ai-agent/scripts/시연데이터생성.py
#
# 사용법:  python ai-agent/scripts/시연데이터생성.py --reset
#   --reset : 기존 DB(data/smart_voca.db)를 지우고 새로 만든다 (실제 사용 데이터가 있다면 사용 금지!)
# 주의: 시연 전용 비밀번호가 출력된다. 팀 테스트 배포(11/16) 전에는 반드시 --reset 없이 새 DB 로 시작하거나
#       관리자 비밀번호를 바꾼다.

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.database import Database  # noqa: E402
from src.business.auth_manager import AuthManager  # noqa: E402
from src.business.word_manager import WordManager  # noqa: E402

ADMIN = ('admin', 'admin1234', '관리자')
DEMO_USERS = [  # (아이디, 비밀번호, 표시이름, 학습 성향: 기본 정답률)
    ('minsu', 'demo1234', '김민수', 0.82),
    ('jiyoung', 'demo1234', '이지영', 0.68),
    ('hojun', 'demo1234', '박호준', 0.55),
    ('seoyun', 'demo1234', '정서윤', 0.74),   # 관리자 대시보드 '학습 랭킹 TOP 5' 가 꽉 차도록 2명 추가 (2026-11-09)
    ('taeho', 'demo1234', '최태호', 0.62),
]

WORDS = """abandon|버리다|verb|He had to abandon the car.
ability|능력|noun|She has the ability to learn fast.
achieve|성취하다|verb|You can achieve your goals.
adapt|적응하다|verb|Animals adapt to their environment.
admire|존경하다|verb|I admire her courage.
advantage|이점|noun|Speed is an advantage here.
afford|여유가 있다|verb|I can't afford a new phone.
agree|동의하다|verb|I agree with your opinion.
allow|허락하다|verb|They don't allow pets.
ancient|고대의|adj|Ancient Rome was powerful.
announce|발표하다|verb|They will announce the winner.
anxious|불안한|adj|He felt anxious before the exam.
appear|나타나다|verb|A rainbow appeared in the sky.
approach|접근하다|verb|Winter is approaching.
argue|논쟁하다|verb|They argue about everything.
arrange|정리하다|verb|Please arrange the books.
attempt|시도하다|verb|She attempted to climb the wall.
attract|끌어당기다|verb|Honey attracts bees.
avoid|피하다|verb|Avoid sugary drinks.
aware|알고 있는|adj|Are you aware of the risk?
balance|균형|noun|Keep your balance on the bike.
benefit|이익|noun|Exercise has many benefits.
borrow|빌리다|verb|Can I borrow your pen?
brilliant|훌륭한|adj|That's a brilliant idea.
calculate|계산하다|verb|Calculate the total cost.
canal|운하|noun|The canal connects two seas.
capable|~할 수 있는|adj|He is capable of doing it.
careful|조심하는|adj|Be careful on the stairs.
cause|원인|noun|What was the cause of the fire?
challenge|도전|noun|Learning is a challenge.
charge|요금|noun|There is no charge for kids.
cheerful|쾌활한|adj|She is a cheerful girl.
civil|시민의|adj|Civil rights matter.
climate|기후|noun|The climate is getting warmer.
collect|모으다|verb|He collects old coins.
combine|결합하다|verb|Combine flour and eggs.
comfortable|편안한|adj|This sofa is comfortable.
compare|비교하다|verb|Compare the two prices.
complete|완성하다|verb|Complete the form.
concentrate|집중하다|verb|Concentrate on your work.
confident|자신 있는|adj|She feels confident today.
consider|고려하다|verb|Consider all options.
continue|계속하다|verb|Please continue reading.
convenient|편리한|adj|The store is convenient.
courage|용기|noun|It takes courage to speak up.
create|창조하다|verb|Artists create beauty.
curious|호기심 많은|adj|Kids are curious.
damage|손상|noun|The storm caused damage.
decide|결정하다|verb|We must decide today.
delay|지연|noun|There was a delay at the airport.
deliver|배달하다|verb|They deliver food fast.
demand|요구|noun|Demand for masks rose.
describe|묘사하다|verb|Describe your best friend.
develop|개발하다|verb|They develop new apps.
discover|발견하다|verb|Columbus discovered America.
distance|거리|noun|The distance is ten miles.
divide|나누다|verb|Divide the cake in two.
effort|노력|noun|Great effort, team!
encourage|격려하다|verb|Teachers encourage students.
environment|환경|noun|Protect the environment.
escape|탈출하다|verb|The bird escaped.
essential|필수적인|adj|Water is essential.
expect|기대하다|verb|I expect good news.
experience|경험|noun|Travel is a great experience.
explain|설명하다|verb|Can you explain this rule?
familiar|친숙한|adj|His face looks familiar.
famous|유명한|adj|Paris is famous for art.
fortune|행운|noun|He made a fortune.
generous|관대한|adj|She is very generous.
gradually|점차|adv|Prices gradually increased.
habit|습관|noun|Reading is a good habit.
honest|정직한|adj|Be honest with me.
imagine|상상하다|verb|Imagine a world without cars.
improve|개선하다|verb|Practice improves skills.
include|포함하다|verb|The price includes tax.
increase|증가하다|verb|Sales increased by 10%.
independent|독립적인|adj|He is very independent.
influence|영향|noun|Parents influence children.
introduce|소개하다|verb|Let me introduce my friend.
journey|여행|noun|The journey took two days.
knowledge|지식|noun|Knowledge is power.
leisure|여가|noun|Golf is his leisure activity.
lonely|외로운|adj|She felt lonely.
manage|관리하다|verb|He manages a small shop.
measure|측정하다|verb|Measure the length.
necessary|필요한|adj|Is it necessary to go?
neglect|소홀히 하다|verb|Don't neglect your health.
obtain|얻다|verb|Obtain a visa first.
occur|발생하다|verb|Accidents occur daily.
opinion|의견|noun|What's your opinion?
patient|인내심 있는|adj|Be patient with kids.
polite|공손한|adj|He is always polite.
prepare|준비하다|verb|Prepare for the test.
protect|보호하다|verb|Helmets protect your head.
recognize|알아보다|verb|I recognize that song.
reduce|줄이다|verb|Reduce waste.
refuse|거절하다|verb|He refused the offer.
suggest|제안하다|verb|I suggest a break.
valuable|귀중한|adj|Time is valuable."""


def build_words(wm: WordManager) -> int:
    count = 0
    for line in WORDS.splitlines():
        english, korean, pos, example = line.split('|')
        wm.add_word(english, korean, pos, example)
        count += 1
    return count


def build_history(db: Database, user_id: int, accuracy: float, rng: random.Random) -> None:
    """최근 14일 중 일부 날짜에 학습·시험 기록을 만든다 (오늘 포함하여 연속 학습일이 보이게)."""
    word_ids = [r['id'] for r in db.query("SELECT id FROM words")]
    today = datetime.now().date()
    active_days = [d for d in range(14) if d < 4 or rng.random() < accuracy]  # 최근 4일은 반드시 학습
    with db.session() as conn:
        for offset in sorted(active_days, reverse=True):
            day = (today - timedelta(days=offset)).strftime('%Y-%m-%d')
            picked = rng.sample(word_ids, 10)
            correct = 0
            for wid in picked:
                ok = rng.random() < accuracy
                correct += ok
                conn.execute(
                    """INSERT INTO user_word_stats(user_id, word_id, weight, success_count, fail_count, last_studied)
                       VALUES(?,?,?,?,?,?) ON CONFLICT(user_id, word_id) DO UPDATE SET
                       weight = MAX(0, weight + ?), success_count = success_count + ?,
                       fail_count = fail_count + ?, last_studied = excluded.last_studied""",
                    (user_id, wid, 0 if ok else 1, 1 if ok else 0, 0 if ok else 1, day,
                     -1 if ok else 1, 1 if ok else 0, 0 if ok else 1))
            conn.execute("INSERT INTO study_logs(user_id, date, words_count, correct_count, success_rate) VALUES(?,?,?,?,?)",
                         (user_id, day, 10, correct, correct * 10.0))
            if rng.random() < 0.6:
                total = rng.choice([10, 10, 20])
                right = min(total, max(0, round(total * (accuracy + rng.uniform(-0.12, 0.12)))))
                conn.execute(
                    "INSERT INTO test_logs(user_id, date, mode, format, total_problems, correct_answers, score) VALUES(?,?,?,?,?,?,?)",
                    (user_id, day, '혼합', '혼합', total, right, round(right / total * 100, 1)))


def main() -> None:
    parser = argparse.ArgumentParser(description='smart-voca 시연 데이터 생성')
    parser.add_argument('--reset', action='store_true', help='기존 DB 를 삭제하고 새로 만든다')
    parser.add_argument('--data-dir', default=str(PROJECT_ROOT / 'data'))
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    db_file = data_dir / 'smart_voca.db'
    if db_file.exists():
        if not args.reset:
            sys.exit(f'이미 DB 가 있습니다: {db_file}\n덮어쓰려면 --reset 을 붙이세요 (기존 데이터가 삭제됩니다).')
        for suffix in ('', '-wal', '-shm'):
            Path(str(db_file) + suffix).unlink(missing_ok=True)

    db = Database(db_file)
    auth, words = AuthManager(db), WordManager(db)
    auth.register(ADMIN[0], ADMIN[1], display_name=ADMIN[2], role='admin')
    n_words = build_words(words)
    rng = random.Random(20261113)  # 고정 시드: 시연할 때마다 같은 화면이 나오도록
    for username, password, name, accuracy in DEMO_USERS:
        user = auth.register(username, password, display_name=name)
        build_history(db, user['id'], accuracy, rng)

    print(f'시연 데이터 생성 완료 (단어 {n_words}개, 사용자 {len(DEMO_USERS)}명)')
    print(f'  관리자  : {ADMIN[0]} / {ADMIN[1]}')
    for username, password, name, _ in DEMO_USERS:
        print(f'  사용자  : {username} / {password}  ({name})')


if __name__ == '__main__':
    main()
