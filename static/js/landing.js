// 2026-11-04 - smart-voca - 랜딩 페이지: 스크롤 등장, 상단바 그림자, 빈칸 퀴즈 맛보기, 역할 탭, 수치 카운트업
// 파일 위치: static/js/landing.js

(function () {
    'use strict';
    const $ = (id) => document.getElementById(id);

    // 1) 스크롤하면 요소가 부드럽게 나타난다 (IntersectionObserver)
    const reveals = document.querySelectorAll('.reveal');
    if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('in');
                entry.target.querySelectorAll('[data-count]').forEach((el) => countUp(el, Number(el.dataset.count)));
                io.unobserve(entry.target);
            });
        }, { threshold: 0.18 });
        reveals.forEach((el) => io.observe(el));
    } else {
        reveals.forEach((el) => { el.classList.add('in'); el.querySelectorAll('[data-count]').forEach((n) => { n.textContent = n.dataset.count; }); });
    }

    // 2) 스크롤 위치에 따라 상단바에 그림자
    const nav = $('lp-nav');
    const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 8);
    window.addEventListener('scroll', onScroll, { passive: true }); onScroll();

    // 3) 빈칸 퀴즈 체험 (서버 호출 없이 브라우저에서만 동작하는 데모)
    const QUIZ = [
        { hint: '능력', parts: ['She has the ', ' to learn fast.'], options: ['ability', 'damage', 'habit', 'balance'], answer: 'ability' },
        { hint: '피하다', parts: ['You should ', ' sugary drinks.'], options: ['borrow', 'avoid', 'create', 'deliver'], answer: 'avoid' },
        { hint: '용기', parts: ['It takes ', ' to speak up.'], options: ['courage', 'journey', 'climate', 'effort'], answer: 'courage' },
    ];
    let step = 0, locked = false;

    function renderQuiz() {
        const q = QUIZ[step];
        locked = false;
        $('demo-card').classList.remove('ok');
        $('demo-card').querySelector('.demo-check')?.remove();
        $('demo-level').textContent = `${step + 1} / ${QUIZ.length}`;
        $('demo-hint').textContent = `뜻: ${q.hint}`;
        const s = $('demo-sentence');
        s.textContent = '';
        s.appendChild(document.createTextNode(q.parts[0]));
        const blank = document.createElement('span'); blank.className = 'blank'; blank.id = 'demo-blank'; blank.textContent = ' ';
        s.appendChild(blank);
        s.appendChild(document.createTextNode(q.parts[1]));
        const box = $('demo-options'); box.innerHTML = '';
        q.options.forEach((opt) => {
            const b = document.createElement('button');
            b.type = 'button'; b.className = 'option'; b.textContent = opt;
            b.addEventListener('click', () => pick(b, opt));
            box.appendChild(b);
        });
        $('demo-msg').textContent = '알맞은 단어를 골라 보세요';
    }

    function pick(btn, opt) {
        if (locked) return;
        const q = QUIZ[step];
        if (opt !== q.answer) {
            btn.classList.add('wrong'); btn.disabled = true;
            $('demo-msg').textContent = '앗, 다시 한번 골라 보세요!';
            return;
        }
        locked = true;
        btn.classList.add('correct');
        const blank = $('demo-blank'); blank.textContent = opt; blank.classList.add('filled');
        $('demo-card').classList.add('ok');
        const check = document.createElement('div'); check.className = 'demo-check'; check.innerHTML = icon('check');
        $('demo-card').appendChild(check);
        document.querySelectorAll('#demo-options .option').forEach((o) => { o.disabled = true; });
        confetti(26);
        const last = step === QUIZ.length - 1;
        $('demo-msg').textContent = last ? '다 풀었어요! 계정을 만들면 기록이 남아요.' : '정답이에요! 다음 문제로 넘어가요…';
        if (last) {
            const cta = document.createElement('a');
            cta.className = 'btn'; cta.href = '/register'; cta.textContent = '계정 만들기'; cta.style.marginTop = '14px';
            $('demo-msg').appendChild(document.createElement('br')); $('demo-msg').appendChild(cta);
        } else {
            setTimeout(() => { step += 1; renderQuiz(); }, 1300);
        }
    }
    renderQuiz();

    // 4) 학습자/관리자 탭 전환
    const tabs = document.querySelectorAll('.lp-tab');
    tabs.forEach((tab) => tab.addEventListener('click', () => {
        tabs.forEach((t) => {
            const on = t === tab;
            t.classList.toggle('active', on);
            t.setAttribute('aria-selected', on ? 'true' : 'false');
            $(t.getAttribute('aria-controls')).hidden = !on;
        });
    }));
})();
