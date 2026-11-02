// 2026-11-02 - smart-voca - 관리자 전역 설정

(function () {
    'use strict';
    const keys = ['total_days', 'max_test_problems', 'max_daily_target'];

    function fill(s) { keys.forEach((k) => { document.getElementById(k).value = s[k]; }); }

    document.getElementById('form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const body = Object.fromEntries(keys.map((k) => [k, Number(document.getElementById(k).value)]));
        try { fill(await api('/api/admin/settings', { method: 'POST', body })); toast('저장했어요'); }
        catch (err) { toast(err.message, 'error'); }
    });

    api('/api/admin/settings').then(fill).catch((e) => toast(e.message, 'error'));
})();
