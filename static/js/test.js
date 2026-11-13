// 2026-11-02 - smart-voca - 시험 화면: 시작/풀이/즉시 피드백/결과 (정답은 서버에만 있고 채점 후에만 받는다)

(function () {
    'use strict';
    const $ = (id) => document.getElementById(id);
    let answered = false, finished = false, current = null;

    function show(name) {
        ['setup', 'quiz', 'result'].forEach((id) => $(id).classList.toggle('hidden', id !== name));
    }
    const radio = (name) => document.querySelector(`input[name="${name}"]:checked`).value;

    async function start() {
        $('btn-start').disabled = true;
        try {
            await api('/api/test/start', { method: 'POST', body: {
                num_problems: Number($('num').value), mode: radio('mode'), format: radio('format') } });
            show('quiz');
            await loadProblem();
        } catch (e) { toast(e.message, 'error'); }
        $('btn-start').disabled = false;
    }

    // 빈칸 문장을 안전하게 그린다: 서버 문자열은 textContent 로만 넣는다 (XSS 방지)
    function renderSentence(sentence, filledWord) {
        const box = $('q-sentence');
        box.textContent = '';
        const parts = sentence.split('_____');
        parts.forEach((text, i) => {
            box.appendChild(document.createTextNode(text));
            if (i < parts.length - 1) {
                const blank = document.createElement('span');
                blank.className = 'blank' + (filledWord ? ' filled' : '');
                blank.textContent = filledWord || ' ';
                box.appendChild(blank);
            }
        });
    }

    async function loadProblem() {
        const p = await api('/api/test/current');
        if (p.finished) { await finish(); return; }
        current = p; answered = false;
        $('q-count').textContent = `${p.index} / ${p.total}`;
        $('q-format').textContent = p.format;
        $('q-bar').style.width = `${((p.index - 1) / p.total) * 100}%`;

        const isBlank = p.format === '빈칸형';
        $('sentence-card').classList.toggle('hidden', !isBlank);
        $('q-text').classList.toggle('hidden', isBlank);
        if (isBlank) {
            $('q-hint').textContent = `뜻: ${p.hint}`;
            renderSentence(p.question, '');
        } else {
            $('q-text').textContent = p.question;
        }
        $('q-feedback').classList.add('hidden');
        $('btn-next').classList.add('hidden');

        const box = $('q-options');
        box.innerHTML = '';
        box.classList.toggle('ox', p.format === 'OX형');
        $('q-short').classList.toggle('hidden', !!p.options);
        if (p.options) {
            p.options.forEach((opt) => {
                const b = document.createElement('button');
                b.type = 'button'; b.className = 'option'; b.textContent = opt;
                b.addEventListener('click', () => submit(opt, b));
                box.appendChild(b);
            });
            box.firstChild?.focus();
        } else {
            $('q-input').value = '';
            $('q-input').focus();
        }
        $('btn-next').dataset.last = p.index === p.total ? '1' : '0';
        $('btn-next').textContent = p.index === p.total ? '결과 보기' : '다음 문제';
    }

    async function submit(answer, clicked) {
        if (answered) return;
        answered = true;
        try {
            const r = await api('/api/test/answer', { method: 'POST', body: { answer } });
            document.querySelectorAll('#q-options .option').forEach((b) => {
                b.disabled = true;
                if (b.textContent === r.correct_answer) b.classList.add('correct');
            });
            if (clicked && !r.is_correct) clicked.classList.add('wrong');
            if (current && current.format === '빈칸형') {
                renderSentence(current.question, r.correct_answer);   // 정답을 빈칸에 채워 보여준다
            }
            const fb = $('q-feedback');
            fb.className = 'feedback ' + (r.is_correct ? 'ok' : 'no');
            fb.textContent = '';
            const badge = document.createElement('span');
            badge.className = 'check-badge' + (r.is_correct ? '' : ' cross');
            badge.innerHTML = icon(r.is_correct ? 'check' : 'x');
            fb.appendChild(badge);
            // 동의어로 맞힌 경우: 정답 처리하되 출제된 단어를 알려 준다
            const okText = r.synonym ? `정답 처리 (출제 단어: ${r.correct_answer})` : '정답이에요!';
            fb.appendChild(document.createTextNode(r.is_correct ? okText : `정답: ${r.correct_answer}`));
            const isWord = current && (current.format === '빈칸형' || current.mode === '한->영');
            if (window.ttsSupported && isWord) {   // 영어 정답은 발음을 들려준다
                const tts = document.createElement('button');
                tts.type = 'button'; tts.className = 'tts-btn sm'; tts.style.marginLeft = 'auto';
                tts.innerHTML = icon('volume-2'); tts.setAttribute('aria-label', '정답 발음 듣기');
                tts.dataset.speak = r.correct_answer;
                fb.appendChild(tts); bindSpeakButtons(fb);
            }
            if (r.is_correct && window.matchMedia('(prefers-reduced-motion: no-preference)').matches) confetti(14);
            $('q-short').classList.add('hidden');
            $('btn-next').classList.remove('hidden');
            $('btn-next').focus();
        } catch (e) { answered = false; toast(e.message, 'error'); }
    }

    async function finish() {
        if (finished) return;
        finished = true;
        try {
            const r = await api('/api/test/finish', { method: 'POST' });
            $('r-score').textContent = `${r.score}점`;
            $('r-summary').textContent = `${r.total_problems}문제 중 ${r.correct_answers}문제 정답`;
            $('r-xp').innerHTML = `<span class="xp-pop">${icon('star')} +${r.xp_gained} XP</span>` +
                (r.level_up ? `<div class="levelup">${icon('circle-arrow-up')} 레벨 업! 이제 LEVEL ${r.level}이에요</div>` : '');
            $('r-list').innerHTML = r.details.map((d) =>
                `<div class="result-item"><span>${icon(d.is_correct ? 'check' : 'x')} ${esc(d.question)}</span>` +
                `<span class="muted">${d.synonym
                    ? `정답 처리 (출제 단어: ${esc(d.correct_answer)}) · 내 답: ${esc(d.user_answer)}`
                    : `정답: ${esc(d.correct_answer)}${d.is_correct ? '' : ` · 내 답: ${esc(d.user_answer || '–')}`}`}</span></div>`).join('');
            show('result');
            if (r.score >= 80 || r.level_up) confetti(r.level_up ? 80 : 50);
        } catch (e) { toast(e.message, 'error'); }
        finished = false;
    }

    $('btn-start').addEventListener('click', start);
    $('btn-next').addEventListener('click', async () => {
        if ($('btn-next').dataset.last === '1') await finish(); else await loadProblem();
    });
    $('q-short').addEventListener('submit', (e) => { e.preventDefault(); if ($('q-input').value.trim()) submit($('q-input').value); });
    $('btn-retry').addEventListener('click', () => show('setup'));
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !$('btn-next').classList.contains('hidden') && document.activeElement !== $('btn-next')) {
            $('btn-next').click();
        }
    });
})();
