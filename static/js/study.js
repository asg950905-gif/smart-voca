// 2026-10-28 - smart-voca - 학습 페이지 JavaScript

let dailyWords = [];
let currentWordIdx = 0;
let results = [];

// 페이지 로드 시 단어 로드
document.addEventListener('DOMContentLoaded', () => {
    loadDailyWords();
});

async function loadDailyWords() {
    try {
        dailyWords = await apiCall('/api/study/daily-words');

        if (dailyWords.length === 0) {
            showNotification('오늘의 단어가 없습니다', 'info');
            return;
        }

        currentWordIdx = 0;
        results = [];
        displayWord();
    } catch (error) {
        showNotification('단어 로드 실패: ' + error.message, 'danger');
    }
}

function displayWord() {
    if (currentWordIdx < dailyWords.length) {
        const word = dailyWords[currentWordIdx];
        document.getElementById('word-english').textContent = word.english;
        document.getElementById('word-korean').textContent = word.korean;

        const progress = currentWordIdx + 1;
        const total = dailyWords.length;
        document.getElementById('word-progress').textContent = `${progress}/${total} 완료`;

        const percent = (progress / total) * 100;
        document.getElementById('study-progress-fill').style.width = percent + '%';

        updateSuccessRate();
    }
}

function recordAnswer(isCorrect) {
    const word = dailyWords[currentWordIdx];

    results.push({
        word_id: word.id,
        is_correct: isCorrect
    });

    currentWordIdx++;

    if (currentWordIdx < dailyWords.length) {
        displayWord();
    } else {
        finishStudy();
    }
}

function updateSuccessRate() {
    const correct = results.filter(r => r.is_correct).length;
    const total = results.length;
    const rate = total > 0 ? (correct / total * 100).toFixed(1) : 0;
    document.getElementById('today-success-rate').textContent = rate + '%';
}

async function finishStudy() {
    try {
        const response = await apiCall('/api/study/record', 'POST', {
            results: results
        });

        showNotification('오늘의 학습이 완료되었습니다! 🎉', 'success');

        setTimeout(() => {
            location.href = '/';
        }, 2000);
    } catch (error) {
        showNotification('학습 저장 실패: ' + error.message, 'danger');
    }
}
