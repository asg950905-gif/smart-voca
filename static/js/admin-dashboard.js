// 2026-11-02 - smart-voca - 관리자 대시보드

(function () {
    'use strict';
    const $ = (id) => document.getElementById(id);
    let charts = null;

    function draw() {
        if (!charts) return;
        const accent = themeColor('--accent'), success = themeColor('--success'), danger = themeColor('--danger');
        const a = charts.daily_activity, s = charts.test_scores, h = charts.hard_words;

        drawChart('c-activity', 'e-activity', {
            type: 'bar',
            data: { labels: a.labels, datasets: [
                { type: 'line', label: '학습 단어 수', data: a.words, borderColor: success, tension: .35, yAxisID: 'y1', pointRadius: 3 },
                { label: '활동 사용자', data: a.users, backgroundColor: accent + 'cc', borderRadius: 8, yAxisID: 'y' }] },
            options: { plugins: { legend: { display: true, labels: { color: themeColor('--text-muted') } } },
                       scales: { y: { ticks: { precision: 0 }, beginAtZero: true },
                                 y1: { position: 'right', grid: { drawOnChartArea: false }, beginAtZero: true } } },
        }, a.labels.length > 0);

        drawChart('c-score', 'e-score', {
            type: 'line',
            data: { labels: s.labels, datasets: [{ data: s.scores, borderColor: success, backgroundColor: success + '22',
                    fill: true, tension: .35, pointRadius: 4 }] },
            options: { scales: { y: { min: 0, max: 100 } } },
        }, s.labels.length > 0);

        drawChart('c-hard', 'e-hard', {
            type: 'bar',
            data: { labels: h.labels, datasets: [{ data: h.values, backgroundColor: danger + 'cc', borderRadius: 8 }] },
            options: { indexAxis: 'y', scales: { x: { ticks: { precision: 0 } } } },
        }, h.labels.length > 0);
    }
    window.redrawCharts = draw;

    async function init() {
        try {
            const [o, c] = await Promise.all([api('/api/admin/overview'), api('/api/admin/charts')]);
            $('k-users').textContent = o.total_users;
            $('k-users-sub').textContent = `오늘 ${o.active_today}명 · 최근 7일 ${o.active_week}명 활동`;
            $('k-words').textContent = o.total_words;
            $('k-tests').textContent = o.total_tests;
            $('k-tests-sub').textContent = o.total_tests ? `평균 ${o.avg_test_score}점` : '아직 없음';
            $('k-rate').textContent = o.avg_study_rate ? o.avg_study_rate + '%' : '–';
            charts = c;
            draw();
            $('ranking').innerHTML = c.ranking.length
                ? c.ranking.map((r, i) => `<tr><td>${i + 1}</td><td>${esc(r.name)}</td><td>${r.days}일</td><td>${r.words}개</td></tr>`).join('')
                : '<tr><td colspan="4" class="empty">사용자가 없어요.</td></tr>';
        } catch (e) { toast(e.message, 'error'); }
    }
    init();
})();
