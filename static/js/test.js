// 2026-10-28 - smart-voca - 시험 페이지 JavaScript

let testConfig = {};
let testResults = [];
let currentProblemIdx = 0;

async function startTest() {
    testConfig = {
        num_problems: parseInt(document.getElementById('num-problems').value),
        mode: document.getElementById('test-mode').value,
        format: document.getElementById('test-format').value
    };

    try {
        await apiCall('/api/test/configure', 'POST', testConfig);

        document.getElementById('test-settings').style.display = 'none';
        document.getElementById('test-progress').style.display = 'block';
        document.getElementById('test-area').style.display = 'block';

        currentProblemIdx = 0;
        testResults = [];
        loadNextProblem();
    } catch (error) {
        showNotification('시험 설정 실패: ' + error.message, 'danger');
    }
}

async function loadNextProblem() {
    try {
        const problem = await apiCall('/api/test/next-problem');

        document.getElementById('problem-text').textContent = problem.question;
        document.getElementById('problem-number').textContent =
            `${currentProblemIdx + 1}/${testConfig.num_problems}`;

        const percent = ((currentProblemIdx) / testConfig.num_problems) * 100;
        document.getElementById('test-progress-fill').style.width = percent + '%';

        // 답변 영역 생성
        const answerArea = document.getElementById('answer-area');
        answerArea.innerHTML = '';

        if (problem.format === '4지선다형') {
            problem.options.forEach(option => {
                const btn = document.createElement('button');
                btn.className = 'btn btn-primary';
                btn.textContent = option;
                btn.onclick = () => {
                    document.getElementById('user-answer').value = option;
                    submitAnswer();
                };
                answerArea.appendChild(btn);
            });
        } else {
            const input = document.createElement('input');
            input.id = 'user-answer';
            input.type = 'text';
            input.placeholder = '답을 입력하세요';
            answerArea.appendChild(input);
        }
    } catch (error) {
        showNotification('문제 로드 실패: ' + error.message, 'danger');
    }
}

async function submitAnswer() {
    const userAnswer = document.getElementById('user-answer').value;

    if (!userAnswer.trim()) {
        showNotification('답을 입력하세요', 'info');
        return;
    }

    try {
        const result = await apiCall('/api/test/submit-answer', 'POST', {
            answer: userAnswer
        });

        testResults.push({
            user_answer: userAnswer,
            is_correct: result.is_correct
        });

        // 정오답 표시
        const message = result.is_correct ? '✓ 정답입니다!' :
                        `✗ 오답입니다. 정답: ${result.correct_answer}`;
        showNotification(message, result.is_correct ? 'success' : 'danger');

        currentProblemIdx++;

        if (currentProblemIdx < testConfig.num_problems) {
            setTimeout(loadNextProblem, 1500);
        } else {
            finishTest();
        }
    } catch (error) {
        showNotification('채점 실패: ' + error.message, 'danger');
    }
}

async function finishTest() {
    try {
        const results = await apiCall('/api/test/finish', 'POST', {});

        document.getElementById('test-progress').style.display = 'none';
        document.getElementById('test-area').style.display = 'none';
        document.getElementById('test-result').style.display = 'block';

        const score = results.score.toFixed(1);
        document.getElementById('result-score').textContent =
            `${results.correct_answers}/${results.total_problems} (${score}점)`;

        showNotification('시험이 완료되었습니다!', 'success');
    } catch (error) {
        showNotification('시험 완료 실패: ' + error.message, 'danger');
    }
}
