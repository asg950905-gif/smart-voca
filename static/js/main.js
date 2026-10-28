// 2026-10-28 - smart-voca - 메인 JavaScript

console.log('smart-voca 앱 초기화됨');

// API 기본 설정
const API_BASE = '/api';

// 공통 API 호출 함수
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(endpoint, options);
        const result = await response.json();

        if (!response.ok) {
            console.error('API 오류:', result.error);
            throw new Error(result.error || '요청 실패');
        }

        return result;
    } catch (error) {
        console.error('API 호출 오류:', error);
        throw error;
    }
}

// 알림 표시
function showNotification(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;

    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alert, container.firstChild);

        setTimeout(() => alert.remove(), 3000);
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    console.log('페이지 로드 완료');

    // 활성 탭 강조
    const currentPage = location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPage) {
            link.style.color = 'var(--primary-color)';
            link.style.fontWeight = 'bold';
        }
    });
});
