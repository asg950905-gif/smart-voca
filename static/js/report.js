// 2026-10-28 - smart-voca - 통계 페이지 JavaScript

document.addEventListener('DOMContentLoaded', () => {
    loadStatistics();
    loadCharts();
});

async function loadStatistics() {
    try {
        const stats = await apiCall('/api/report/statistics');

        document.getElementById('study-days').textContent = stats.total_study_days;
        document.getElementById('test-attempts').textContent = stats.total_test_attempts;
        document.getElementById('avg-success').textContent =
            stats.average_study_success_rate.toFixed(1) + '%';
        document.getElementById('avg-score').textContent =
            stats.average_test_score.toFixed(1) + '점';
    } catch (error) {
        showNotification('통계 로드 실패: ' + error.message, 'danger');
    }
}

async function loadCharts() {
    try {
        const charts = await apiCall('/api/report/charts');

        const ctx = document.getElementById('study-chart');
        if (ctx && charts.study_trend && charts.study_trend.labels.length > 0) {
            new Chart(ctx, {
                type: 'line',
                data: charts.study_trend,
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: '최근 7일 학습 성공률'
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('차트 로드 실패:', error);
    }
}

async function exportReport() {
    try {
        const response = await fetch('/report/export');
        const blob = await response.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'smart-voca-report.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);

        showNotification('보고서를 다운로드했습니다', 'success');
    } catch (error) {
        showNotification('다운로드 실패: ' + error.message, 'danger');
    }
}
