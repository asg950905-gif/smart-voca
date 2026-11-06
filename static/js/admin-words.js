// 2026-11-02 - smart-voca - 관리자 단어 관리 (목록·검색·페이징, 추가/수정/삭제 모달, CSV 가져오기)

(function () {
    'use strict';
    const $ = (id) => document.getElementById(id);
    let page = 1, pages = 1, query = '', timer = null;

    async function load() {
        try {
            const d = await api(`/api/admin/words?page=${page}&q=${encodeURIComponent(query)}`);
            pages = d.pages;
            $('total').textContent = `총 ${d.total}개`;
            $('page-info').textContent = `${d.page} / ${d.pages}`;
            $('prev').disabled = d.page <= 1;
            $('next').disabled = d.page >= d.pages;
            $('rows').innerHTML = d.items.length ? d.items.map((w) =>
                `<tr><td><strong>${esc(w.english)}</strong></td><td>${esc(w.korean)}</td>` +
                `<td>${w.part_of_speech ? `<span class="pill neutral">${esc(w.part_of_speech)}</span>` : ''}</td>` +
                `<td class="muted small">${esc(w.example)}</td>` +
                `<td class="row" style="flex-wrap:nowrap"><button class="btn secondary small" data-edit="${w.id}">수정</button>` +
                `<button class="btn danger outline small" data-del="${w.id}" data-name="${esc(w.english)}">삭제</button></td></tr>`
            ).join('') : '<tr><td colspan="5" class="empty">' + icon('inbox', 'ico-lg') + '단어가 없어요. 추가하거나 CSV로 가져오세요.</td></tr>';
            window._words = Object.fromEntries(d.items.map((w) => [w.id, w]));
        } catch (e) { toast(e.message, 'error'); }
    }

    // 추가/수정 모달
    function openForm(word) {
        const back = document.createElement('div');
        back.className = 'modal-back';
        back.innerHTML = `<form class="modal" role="dialog" aria-modal="true"><h2>${word ? '단어 수정' : '단어 추가'}</h2>
            <div class="field"><label for="f-en">영단어</label><input id="f-en" required maxlength="100"></div>
            <div class="field"><label for="f-ko">뜻</label><input id="f-ko" required maxlength="200"></div>
            <div class="field"><label for="f-pos">품사 <span class="muted">(선택)</span></label><input id="f-pos" maxlength="20" placeholder="noun, verb …"></div>
            <div class="field"><label for="f-ex">예문 <span class="muted">(선택)</span></label><input id="f-ex" maxlength="300"></div>
            <div class="row" style="justify-content:flex-end"><button class="btn secondary" type="button" data-close>취소</button>
            <button class="btn" type="submit">저장</button></div></form>`;
        document.body.appendChild(back);
        const f = (id) => back.querySelector('#' + id);
        if (word) { f('f-en').value = word.english; f('f-ko').value = word.korean; f('f-pos').value = word.part_of_speech; f('f-ex').value = word.example; }
        f('f-en').focus();
        back.addEventListener('click', (e) => { if (e.target === back || e.target.hasAttribute('data-close')) back.remove(); });
        back.querySelector('form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const body = { english: f('f-en').value, korean: f('f-ko').value, part_of_speech: f('f-pos').value, example: f('f-ex').value };
            try {
                await api(word ? `/api/admin/words/${word.id}` : '/api/admin/words', { method: word ? 'PUT' : 'POST', body });
                back.remove(); toast(word ? '수정했어요' : '추가했어요'); load();
            } catch (err) { toast(err.message, 'error'); }
        });
    }

    $('btn-add').addEventListener('click', () => openForm(null));
    $('rows').addEventListener('click', async (e) => {
        const edit = e.target.dataset.edit, del = e.target.dataset.del;
        if (edit) openForm(window._words[edit]);
        if (del && await confirmDialog(`'${e.target.dataset.name}' 단어를 삭제할까요? 사용자들의 해당 단어 기록도 함께 삭제돼요.`, '삭제')) {
            try { await api(`/api/admin/words/${del}`, { method: 'DELETE' }); toast('삭제했어요'); load(); }
            catch (err) { toast(err.message, 'error'); }
        }
    });

    $('search').addEventListener('input', (e) => {
        clearTimeout(timer);
        timer = setTimeout(() => { query = e.target.value; page = 1; load(); }, 250); // 입력이 멈춘 뒤 검색
    });
    $('prev').addEventListener('click', () => { if (page > 1) { page -= 1; load(); } });
    $('next').addEventListener('click', () => { if (page < pages) { page += 1; load(); } });

    // CSV 가져오기
    $('btn-import').addEventListener('click', () => $('file').click());
    $('file').addEventListener('change', async () => {
        const file = $('file').files[0];
        if (!file) return;
        const fd = new FormData();
        fd.append('file', file);
        try {
            const r = await api('/api/admin/words/import', { method: 'POST', formData: fd });
            toast(`추가 ${r.added}개, 건너뜀 ${r.skipped}개` + (r.errors.length ? ` — ${r.errors[0]}` : ''));
            page = 1; load();
        } catch (e) { toast(e.message, 'error'); }
        $('file').value = '';
    });
    load();
})();
