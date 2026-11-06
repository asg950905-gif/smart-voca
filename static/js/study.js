// 2026-11-02 - smart-voca - 학습 화면: 플립카드, 발음 듣기(TTS), 단축키, 결과 저장, 완료 축하

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
        $('tts-word').dataset.speak = w.english;
        $('tts-example').dataset.speak = w.example || w.english;
        bindSpeakButtons();
        $('progress-text').textContent = `${index + 1} / ${words.length}`;
        $('progress-bar').style.width = `${(index / words.length) * 100}%`;
        if (window.ttsSupported) speak(w.english, $('tts-word'));   // 카드가 바뀔 때 자동으로 한 번 읽어 준다
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
            const r = await api('/api/study/record', { method: 'POST', body: { results } });
            $('done-summary').textContent = `${r.words_count}개 중 ${r.correct_count}개를 기억했어요 (${r.success_rate}%)`;
            $('done-xp').innerHTML = `<span class="xp-pop">${icon('star')} +${r.xp_gained} XP</span>` +
                (r.level_up ? `<div class="levelup">${icon('circle-arrow-up')} 레벨 업! 이제 LEVEL ${r.level}이에요</div>` : '');
            show('done-area');
            confetti(r.level_up ? 70 : 40);
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
        else if (e.code === 'KeyP') speak(words[index].english, $('tts-word'));
    });
    init();
})();
