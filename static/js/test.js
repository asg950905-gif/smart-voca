// 2026-11-02 - smart-voca - 시험 화면: 시작/풀이/즉시 피드백/결과 (정답은 서버에만 있고 채점 후에만 받는다)

(function () {
    'use strict';
    const $ = (id) => document.getElementById(id);
    let answered = false, finished = false;

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

    async function loadProblem() {
        const p = await api('/api/test/current');
        if (p.finished) { await finish(); return; }
        answered = false;
        $('q-count').textContent = `${p.index} / ${p.total}`;
        $('q-format').textContent = p.format;
        $('q-bar').style.width = `${((p.index - 1) / p.total) * 100}%`;
        $('q-text').textContent = p.question;
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
            const fb = $('q-feedback');
            fb.className = 'feedback ' + (r.is_correct ? 'ok' : 'no');
            fb.textContent = r.is_correct ? '✅ 정답이에요!' : `❌ 정답: ${r.correct_answer}`;
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
            $('r-list').innerHTML = r.details.map((d) =>
                `<div class="result-item"><span>${d.is_correct ? '✅' : '❌'} ${esc(d.question)}</span>` +
                `<span class="muted">${esc(d.correct_answer)}</span></div>`).join('');
            show('result');
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
