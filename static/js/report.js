// 2026-11-02 - smart-voca - 사용자 통계 화면

(function () {
    'use strict';
    let charts = null;

    function draw() {
        if (!charts) return;
        const accent = themeColor('--accent'), success = themeColor('--success'), danger = themeColor('--danger');
        const s = charts.study_trend, t = charts.test_scores, w = charts.weak_words;

        drawChart('c-study', 'e-study', {
            type: 'line',
            data: { labels: s.labels, datasets: [{ data: s.rates, borderColor: accent, backgroundColor: accent + '22',
                    fill: true, tension: .35, pointRadius: 4, pointBackgroundColor: accent }] },
            options: { scales: { y: { min: 0, max: 100, ticks: { callback: (v) => v + '%' } } } },
        }, s.labels.length > 0);

        drawChart('c-test', 'e-test', {
            type: 'bar',
            data: { labels: t.labels, datasets: [{ data: t.scores, backgroundColor: success + 'cc', borderRadius: 8 }] },
            options: { scales: { y: { min: 0, max: 100 } } },
        }, t.labels.length > 0);

        drawChart('c-weak', 'e-weak', {
            type: 'bar',
            data: { labels: w.labels, datasets: [{ data: w.values, backgroundColor: danger + 'cc', borderRadius: 8 }] },
            options: { indexAxis: 'y', scales: { x: { ticks: { precision: 0 } } } },
        }, w.labels.length > 0);
    }
    window.redrawCharts = draw;

    async function init() {
        try {
            const [stats, c] = await Promise.all([api('/api/report/statistics'), api('/api/report/charts')]);
            document.getElementById('k-days').textContent = stats.total_study_days + '일';
            document.getElementById('k-rate').textContent = stats.average_study_success_rate + '%';
            document.getElementById('k-tests').textContent = stats.total_test_attempts + '회';
            document.getElementById('k-score').textContent = `${stats.average_test_score} / ${stats.best_test_score}`;
            charts = c;
            draw();
        } catch (e) { toast(e.message, 'error'); }
    }
    init();
})();
