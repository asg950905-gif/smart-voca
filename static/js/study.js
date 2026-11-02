// 2026-11-02 - smart-voca - 학습 화면: 플립카드, 단축키, 결과 저장

(function () {
    'use strict';
    const $ = (id) => document.getElementById(id);
    let words = [], index = 0, results = [], saving = false;

    function show(area) {
        ['card-area', 'empty-area', 'done-area'].forEach((id) => $(id).classList.toggle('hidden', id !== area));
    }

    function render() {
        const w = words[index];
        $('flip').classList.remove('flipped');
        $('english').textContent = w.english;
        $('korean').textContent = w.korean;
        $('pos').textContent = w.part_of_speech || '';
        $('pos').classList.toggle('hidden', !w.part_of_speech);
        $('example').textContent = w.example || '';
        $('progress-text').textContent = `${index + 1} / ${words.length}`;
        $('progress-bar').style.width = `${(index / words.length) * 100}%`;
    }

    function flip() { $('flip').classList.toggle('flipped'); }

    async function judge(isCorrect) {
        if (saving || !words.length) return;
        results.push({ word_id: words[index].id, is_correct: isCorrect });
        index += 1;
        if (index < words.length) { render(); return; }

        saving = true;
        $('progress-bar').style.width = '100%';
        try {
            const summary = await api('/api/study/record', { method: 'POST', body: { results } });
            $('done-summary').textContent =
                `${summary.words_count}개 중 ${summary.correct_count}개를 기억했어요 (${summary.success_rate}%)`;
            show('done-area');
        } catch (e) {
            toast(e.message, 'error');
            index -= 1; results.pop(); saving = false; // 저장 실패 시 마지막 카드로 되돌려 재시도할 수 있게 한다
            return;
        }
        saving = false;
    }

    async function init() {
        try {
            words = await api('/api/study/daily-words');
        } catch (e) { toast(e.message, 'error'); return; }
        if (!words.length) { $('progress-text').textContent = ''; show('empty-area'); return; }
        show('card-area');
        render();
    }

    $('flip').addEventListener('click', flip);
    $('btn-know').addEventListener('click', () => judge(true));
    $('btn-unknown').addEventListener('click', () => judge(false));
    document.addEventListener('keydown', (e) => {
        if ($('card-area').classList.contains('hidden')) return;
        if (e.code === 'Space') { e.preventDefault(); flip(); }
        else if (e.code === 'ArrowRight') judge(true);
        else if (e.code === 'ArrowLeft') judge(false);
    });
    init();
})();
