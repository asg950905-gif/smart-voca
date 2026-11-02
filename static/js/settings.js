// 2026-10-28 - smart-voca - 설정 페이지 JavaScript

document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
});

async function loadSettings() {
    try {
        const settings = await apiCall('/api/settings');

        document.getElementById('daily-target').value = settings.daily_target || 10;
        document.getElementById('dark-mode').checked = settings.dark_mode || false;
        document.getElementById('theme').value = settings.theme || 'default';
        document.getElementById('font-size').value = settings.font_size || 'medium';
    } catch (error) {
        showNotification('설정 로드 실패: ' + error.message, 'danger');
    }
}

async function saveSettings() {
    const settings = {
        daily_target: parseInt(document.getElementById('daily-target').value),
        dark_mode: document.getElementById('dark-mode').checked,
        theme: document.getElementById('theme').value,
        font_size: document.getElementById('font-size').value
    };

    try {
        await apiCall('/api/settings', 'POST', settings);
        showNotification('설정이 저장되었습니다', 'success');
    } catch (error) {
        showNotification('설정 저장 실패: ' + error.message, 'danger');
    }
}

function resetProgress() {
    if (confirm('진도를 초기화하시겠습니까?\n학습 이력은 유지됩니다.')) {
        // TODO: 진도 초기화 API 호출
        showNotification('진도가 초기화되었습니다', 'success');
    }
}

function resetAllData() {
    if (confirm('⚠️ 정말로 모든 데이터를 초기화하시겠습니까?\n이 작업은 되돌릴 수 없습니다!')) {
        if (confirm('다시 한 번 확인합니다. 정말 초기화하시겠습니까?')) {
            apiCall('/api/settings/reset', 'POST')
                .then(() => {
                    showNotification('모든 데이터가 초기화되었습니다', 'success');
                    setTimeout(() => location.href = '/', 2000);
                })
                .catch(error => {
                    showNotification('초기화 실패: ' + error.message, 'danger');
                });
        }
    }
}
