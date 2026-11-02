// 2026-11-02 - smart-voca - 차트 공통 헬퍼 (테마 색상 연동, 빈 데이터 처리)

(function () {
    'use strict';
    const instances = {};

    function cssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    // 캔버스에 차트를 그린다. 데이터가 없으면 canvas 를 숨기고 빈 상태 안내(#e-...)를 보여준다.
    window.drawChart = function (canvasId, emptyId, config, hasData) {
        const canvas = document.getElementById(canvasId);
        const empty = document.getElementById(emptyId);
        canvas.parentElement.classList.toggle('hidden', !hasData);
        if (empty) empty.classList.toggle('hidden', hasData);
        if (instances[canvasId]) instances[canvasId].destroy();
        if (!hasData) return;
        const text = cssVar('--text-muted'), grid = cssVar('--border');
        Chart.defaults.font.family = cssVar('--font');
        config.options = Object.assign({ responsive: true, maintainAspectRatio: false }, config.options || {});
        config.options.plugins = Object.assign({ legend: { display: false } }, config.options.plugins || {});
        config.options.scales = config.options.scales || {};
        Object.values(config.options.scales).forEach((s) => {
            s.ticks = Object.assign({ color: text }, s.ticks || {});
            s.grid = Object.assign({ color: grid }, s.grid || {});
        });
        instances[canvasId] = new Chart(canvas, config);
    };
    window.themeColor = cssVar;

    // 테마를 바꾸면 차트 색을 다시 입힌다
    new MutationObserver(() => { if (typeof window.redrawCharts === 'function') window.redrawCharts(); })
        .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
})();
