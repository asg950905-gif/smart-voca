// 2026-11-02 - smart-voca - 공통 스크립트 (API 호출, 토스트, 테마, 모달, 이스케이프)

(function () {
    'use strict';

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    // XSS 방지: 서버 데이터를 innerHTML 에 넣을 때는 반드시 esc() 를 거친다
    window.esc = function (value) {
        const div = document.createElement('div');
        div.textContent = value == null ? '' : String(value);
        return div.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    };

    // fetch 래퍼: CSRF 헤더 자동 추가, 오류 메시지를 Error 로 던진다
    window.api = async function (url, { method = 'GET', body, formData } = {}) {
        const options = { method, headers: { 'X-CSRF-Token': csrfToken }, credentials: 'same-origin' };
        if (formData) {
            options.body = formData;
        } else if (body !== undefined) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
        const response = await fetch(url, options);
        if (response.status === 401) { location.href = '/login'; throw new Error('로그인이 필요합니다.'); }
        let data = {};
        try { data = await response.json(); } catch (_) { /* 본문 없음 */ }
        if (!response.ok) throw new Error(data.error || '요청에 실패했습니다.');
        return data;
    };

    window.toast = function (message, type = 'info') {
        let wrap = document.querySelector('.toast-wrap');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'toast-wrap';
            wrap.setAttribute('aria-live', 'polite');
            document.body.appendChild(wrap);
        }
        const el = document.createElement('div');
        el.className = 'toast ' + (type === 'error' ? 'error' : '');
        el.textContent = message;
        wrap.appendChild(el);
        setTimeout(() => el.remove(), 3200);
    };

    // 확인 모달 (confirm() 대신 일관된 UI)
    window.confirmDialog = function (message, okLabel = '확인') {
        return new Promise((resolve) => {
            const back = document.createElement('div');
            back.className = 'modal-back';
            back.innerHTML = '<div class="modal" role="dialog" aria-modal="true"><h2></h2>' +
                '<div class="row" style="justify-content:flex-end"><button class="btn secondary" data-v="0">취소</button>' +
                '<button class="btn danger" data-v="1"></button></div></div>';
            back.querySelector('h2').textContent = message;
            back.querySelector('[data-v="1"]').textContent = okLabel;
            back.addEventListener('click', (e) => {
                const v = e.target.dataset?.v;
                if (v !== undefined || e.target === back) { back.remove(); resolve(v === '1'); }
            });
            document.body.appendChild(back);
            back.querySelector('[data-v="0"]').focus();
        });
    };

    // ---- 테마: system / light / dark ----
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    function applyTheme(pref) {
        const dark = pref === 'dark' || (pref === 'system' && media.matches);
        document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
        const btn = document.getElementById('theme-toggle');
        if (btn) btn.textContent = dark ? '☀️' : '🌙';
    }
    window.applyTheme = applyTheme;
    media.addEventListener?.('change', () => applyTheme(localStorage.getItem('theme') || 'system'));

    document.addEventListener('DOMContentLoaded', () => {
        applyTheme(document.documentElement.dataset.themePref || 'system');
        const toggle = document.getElementById('theme-toggle');
        if (toggle) {
            toggle.addEventListener('click', async () => {
                const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
                document.documentElement.dataset.themePref = next;
                try { localStorage.setItem('theme', next); } catch (_) { /* 저장 불가 환경 */ }
                applyTheme(next);
                if (document.body.dataset.loggedIn === '1') {
                    try { await api('/api/settings', { method: 'POST', body: { theme: next } }); } catch (_) { /* 로컬만 적용 */ }
                }
            });
        }
    });
})();
