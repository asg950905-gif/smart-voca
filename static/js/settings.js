// 2026-11-02 - smart-voca - 사용자 설정 화면

(function () {
    'use strict';
    const $ = (id) => document.getElementById(id);

    async function load() {
        try {
            const s = await api('/api/settings');
            $('daily_target').value = s.daily_target;
            $('daily_target').max = s.max_daily_target;
            $('target-hint').textContent = `1 ~ ${s.max_daily_target}개`;
            document.querySelector(`input[name="theme"][value="${s.theme}"]`).checked = true;
            $('auto_speak').checked = !!s.auto_speak;
        } catch (e) { toast(e.message, 'error'); }
    }

    $('settings-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const theme = document.querySelector('input[name="theme"]:checked').value;
        try {
            await api('/api/settings', { method: 'POST', body: {
                daily_target: Number($('daily_target').value), theme, auto_speak: $('auto_speak').checked } });
            document.documentElement.dataset.themePref = theme;
            try { localStorage.setItem('theme', theme); } catch (_) { /* 저장 불가 환경 */ }
            applyTheme(theme);
            toast('저장했어요');
        } catch (err) { toast(err.message, 'error'); }
    });

    $('btn-reset').addEventListener('click', async () => {
        if (!(await confirmDialog('내 학습 기록을 모두 삭제할까요?', '삭제'))) return;
        try { await api('/api/settings/reset', { method: 'POST' }); toast('기록을 초기화했어요'); }
        catch (e) { toast(e.message, 'error'); }
    });
    load();
})();
