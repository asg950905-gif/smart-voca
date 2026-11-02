// 2026-11-02 - smart-voca - 주간 리그 화면

(function () {
    'use strict';
    const MEDALS = ['🥇', '🥈', '🥉'];

    async function init() {
        try {
            const d = await api('/api/league');
            const withXp = d.board.filter((r) => r.xp > 0);
            document.getElementById('league-empty').classList.toggle('hidden', withXp.length > 0);
            if (d.my_rank) {
                document.getElementById('league-sub').textContent = `${d.total}명 중 내 순위는 ${d.my_rank}위예요. (${d.since} ~ 오늘)`;
            }
            const top = d.board.filter((r) => r.rank <= 3 && r.xp > 0);
            const podium = document.getElementById('podium');
            podium.classList.toggle('hidden', top.length === 0);
            // 시상대 배치: 2위 - 1위 - 3위
            const order = [top.find((r) => r.rank === 2), top.find((r) => r.rank === 1), top.find((r) => r.rank === 3)];
            podium.innerHTML = order.map((r, i) => {
                if (!r) return '<div></div>';
                const cls = ['s2', 's1', 's3'][i];
                return `<div class="step ${cls}"><span class="medal">${MEDALS[r.rank - 1]}</span>${esc(r.name)}${r.me ? ' (나)' : ''}<span class="xp">${r.xp} XP</span></div>`;
            }).join('');
            document.getElementById('board').innerHTML = d.board.map((r) =>
                `<div class="rank-row${r.me ? ' me' : ''}"><span class="rk">${r.rank}</span>` +
                `<span class="nm">${esc(r.name)}${r.me ? ' <span class="pill admin">나</span>' : ''}</span>` +
                `<span class="pts">${r.xp} XP</span></div>`).join('');
        } catch (e) { toast(e.message, 'error'); }
    }
    init();
})();
