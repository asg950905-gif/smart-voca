// 2026-11-02 - smart-voca - 관리자 사용자 관리

(function () {
    'use strict';
    const $ = (id) => document.getElementById(id);
    let users = {}, timer = null;

    async function load(q = '') {
        try {
            const list = await api('/api/admin/users?q=' + encodeURIComponent(q));
            users = Object.fromEntries(list.map((u) => [u.id, u]));
            $('total').textContent = `총 ${list.length}명`;
            $('rows').innerHTML = list.length ? list.map((u) => {
                const me = u.id === window.ME_ID;
                return `<tr><td><strong>${esc(u.display_name)}</strong><div class="muted small">@${esc(u.username)}</div></td>` +
                    `<td><span class="pill ${u.role === 'admin' ? 'admin' : 'neutral'}">${u.role === 'admin' ? '관리자' : '사용자'}</span></td>` +
                    `<td><span class="pill ${u.active ? 'ok' : 'off'}">${u.active ? '활성' : '비활성'}</span></td>` +
                    `<td>${u.study_days}일</td><td>${esc(u.last_study || '–')}</td><td>${u.avg_score == null ? '–' : u.avg_score + '점'}</td>` +
                    `<td>${me ? '<span class="muted small">나</span>' :
                        `<div class="row" style="flex-wrap:nowrap">` +
                        `<button class="btn secondary small" data-act="role" data-id="${u.id}">${u.role === 'admin' ? '사용자로' : '관리자로'}</button>` +
                        `<button class="btn secondary small" data-act="active" data-id="${u.id}">${u.active ? '비활성화' : '활성화'}</button>` +
                        `<button class="btn secondary small" data-act="pw" data-id="${u.id}">비번 재설정</button>` +
                        `<button class="btn danger outline small" data-act="del" data-id="${u.id}">삭제</button></div>`}</td></tr>`;
            }).join('') : '<tr><td colspan="7" class="empty">사용자가 없어요.</td></tr>';
        } catch (e) { toast(e.message, 'error'); }
    }

    function promptPassword(user) {
        const back = document.createElement('div');
        back.className = 'modal-back';
        back.innerHTML = `<form class="modal" role="dialog" aria-modal="true"><h2></h2>
            <div class="field"><label for="np">새 비밀번호</label><input id="np" type="text" minlength="6" required autocomplete="off">
            <p class="hint">6자 이상. 사용자에게 안전한 방법으로 전달하세요.</p></div>
            <div class="row" style="justify-content:flex-end"><button class="btn secondary" type="button" data-close>취소</button>
            <button class="btn" type="submit">변경</button></div></form>`;
        back.querySelector('h2').textContent = `${user.display_name} 비밀번호 재설정`;
        document.body.appendChild(back);
        back.querySelector('#np').focus();
        back.addEventListener('click', (e) => { if (e.target === back || e.target.hasAttribute('data-close')) back.remove(); });
        back.querySelector('form').addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                await api(`/api/admin/users/${user.id}/password`, { method: 'POST', body: { password: back.querySelector('#np').value } });
                back.remove(); toast('비밀번호를 변경했어요');
            } catch (err) { toast(err.message, 'error'); }
        });
    }

    $('rows').addEventListener('click', async (e) => {
        const { act, id } = e.target.dataset;
        if (!act) return;
        const u = users[id];
        try {
            if (act === 'role') {
                const role = u.role === 'admin' ? 'user' : 'admin';
                if (!(await confirmDialog(`${u.display_name}님을 ${role === 'admin' ? '관리자' : '일반 사용자'}로 변경할까요?`, '변경'))) return;
                await api(`/api/admin/users/${id}/role`, { method: 'POST', body: { role } });
            } else if (act === 'active') {
                await api(`/api/admin/users/${id}/active`, { method: 'POST', body: { active: !u.active } });
            } else if (act === 'pw') {
                promptPassword(u); return;
            } else if (act === 'del') {
                if (!(await confirmDialog(`${u.display_name}님과 모든 학습 기록을 삭제할까요?`, '삭제'))) return;
                await api(`/api/admin/users/${id}`, { method: 'DELETE' });
            }
            toast('처리했어요'); load($('search').value);
        } catch (err) { toast(err.message, 'error'); }
    });

    $('search').addEventListener('input', (e) => {
        clearTimeout(timer);
        timer = setTimeout(() => load(e.target.value), 250);
    });
    load();
})();
