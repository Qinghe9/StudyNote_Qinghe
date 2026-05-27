/**
 * EduMesh 前端核心逻辑
 * - WebSocket实时通信
 * - 事件流可视化
 * - 5-Agent状态监控
 * - BKT掌握度可视化
 * - SM-2复习计划
 */

const API_BASE = 'http://localhost:8000';
let ws = null;
let studentId = null;
let studentName = '';
let currentQuestion = null;
let selectedOption = null;

// ===== 页面切换 =====
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');
}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('start-btn').addEventListener('click', startLearning);
    document.getElementById('student-name').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') startLearning();
    });
    document.getElementById('submit-btn').addEventListener('click', submitAnswer);
    document.getElementById('hint-btn').addEventListener('click', requestHint);
    document.getElementById('next-btn').addEventListener('click', loadNextQuestion);
});

// ===== 开始学习 =====
async function startLearning() {
    const nameInput = document.getElementById('student-name');
    studentName = nameInput.value.trim();

    if (!studentName) {
        shakeElement(nameInput);
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/students`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: studentName })
        });
        const data = await res.json();
        studentId = data.student_id;

        // 设置头像
        document.getElementById('student-avatar').textContent = studentName.charAt(0).toUpperCase();
        document.getElementById('student-name-display').textContent = studentName;

        showPage('learning-page');
        connectWebSocket();
        loadNextQuestion();

    } catch (err) {
        alert('连接服务器失败，请确保后端已启动 (python backend/main.py)');
        console.error(err);
    }
}

// ===== WebSocket连接 =====
function connectWebSocket() {
    ws = new WebSocket(`ws://localhost:8000/ws/${studentId}`);

    ws.onopen = () => {
        updateConnectionStatus(true);
        addSystemMessage('已连接到实时学习系统，5个Agent正在协同工作...');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onclose = () => {
        updateConnectionStatus(false);
        setTimeout(() => connectWebSocket(), 3000);
    };

    ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        updateConnectionStatus(false);
    };
}

function updateConnectionStatus(connected) {
    const dot = document.getElementById('ws-status');
    const text = document.getElementById('ws-text');
    if (connected) {
        dot.classList.add('connected');
        text.textContent = '实时连接中';
    } else {
        dot.classList.remove('connected');
        text.textContent = '连接断开';
    }
}

// ===== 处理WebSocket消息 =====
function handleWebSocketMessage(data) {
    // 添加到事件流
    addEventToStream(data);

    switch (data.type) {
        case 'TUTOR_RESPONSE':
            handleTutorResponse(data.payload);
            break;
        case 'MASTERY_UPDATED':
            handleMasteryUpdate(data.payload);
            break;
        case 'CURRICULUM_UPDATED':
            handleCurriculumUpdate(data.payload);
            break;
        case 'ENGAGEMENT_ALERT':
            handleEngagementAlert(data.payload);
            break;
        case 'HINT_RESPONSE':
            handleHintResponse(data.payload);
            break;
        case 'ASSESSMENT_COMPLETE':
            handleAssessmentComplete(data.payload);
            break;
        case 'SYSTEM_MESSAGE':
            addSystemMessage(data.payload.message);
            break;
    }

    // 更新Agent状态
    updateAgentStatus(data.source, data.type);
}

// ===== 加载下一题 =====
async function loadNextQuestion() {
    try {
        const res = await fetch(`${API_BASE}/api/questions/next?student_id=${studentId}`);
        if (!res.ok) throw new Error('No more questions');
        currentQuestion = await res.json();

        renderQuestion(currentQuestion);
        hideFeedback();
        selectedOption = null;

    } catch (err) {
        document.getElementById('question-content').innerHTML = 
            '<div style="text-align:center;padding:2rem;color:var(--text-secondary)">🎉 恭喜！你已完成了当前所有题目</div>';
        document.getElementById('options-list').innerHTML = '';
        document.getElementById('submit-btn').disabled = true;
    }
}

// ===== 渲染题目 =====
function renderQuestion(q) {
    document.getElementById('subject-tag').textContent = q.subject || '综合';
    document.getElementById('difficulty-tag').textContent = `难度: ${q.difficulty}`;
    document.getElementById('question-content').textContent = q.content;

    const optionsList = document.getElementById('options-list');
    const answerInput = document.getElementById('answer-input-area');

    if (q.options && q.options.length > 0) {
        optionsList.style.display = 'flex';
        answerInput.style.display = 'none';

        optionsList.innerHTML = q.options.map((opt, i) => `
            <div class="option-item" data-value="${opt}" onclick="selectOption(this, '${opt}')">
                <div class="option-label">${String.fromCharCode(65 + i)}</div>
                <div class="option-text">${opt}</div>
            </div>
        `).join('');
    } else {
        optionsList.style.display = 'none';
        answerInput.style.display = 'block';
        document.getElementById('text-answer').value = '';
    }

    document.getElementById('submit-btn').disabled = true;
}

// ===== 选择选项 =====
function selectOption(el, value) {
    document.querySelectorAll('.option-item').forEach(item => item.classList.remove('selected'));
    el.classList.add('selected');
    selectedOption = value;
    document.getElementById('submit-btn').disabled = false;
}

// 监听文本输入
document.addEventListener('input', (e) => {
    if (e.target.id === 'text-answer') {
        document.getElementById('submit-btn').disabled = e.target.value.trim() === '';
    }
});

// ===== 提交答案 =====
async function submitAnswer() {
    if (!currentQuestion) return;

    let answer;
    if (currentQuestion.options && currentQuestion.options.length > 0) {
        answer = selectedOption;
    } else {
        answer = document.getElementById('text-answer').value.trim();
    }

    if (!answer) return;

    document.getElementById('submit-btn').disabled = true;

    // 通过WebSocket提交
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'answer',
            question_id: currentQuestion.question_id,
            answer: answer
        }));
    }

    // 同时通过REST API获取正确性反馈
    try {
        const res = await fetch(`${API_BASE}/api/answers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: studentId,
                question_id: currentQuestion.question_id,
                answer: answer
            })
        });
        const result = await res.json();
        showAnswerResult(result, answer);
    } catch (err) {
        console.error(err);
    }

    // 刷新掌握度
    setTimeout(() => loadMastery(), 500);
}

// ===== 显示答案结果 =====
function showAnswerResult(result, userAnswer) {
    const feedbackArea = document.getElementById('feedback-area');
    const feedbackCard = document.getElementById('feedback-card');
    const icon = document.getElementById('feedback-icon');
    const title = document.getElementById('feedback-title');
    const message = document.getElementById('feedback-message');
    const masteryUpdate = document.getElementById('mastery-update');

    feedbackArea.style.display = 'block';

    if (result.correct) {
        icon.textContent = '🎉';
        title.textContent = '回答正确！';
        title.style.color = 'var(--secondary)';
        message.textContent = result.explanation;

        // 高亮正确选项
        document.querySelectorAll('.option-item').forEach(item => {
            if (item.dataset.value === userAnswer) {
                item.classList.add('correct');
            }
        });
    } else {
        icon.textContent = '🤔';
        title.textContent = '再想想看';
        title.style.color = 'var(--warning)';
        message.textContent = `正确答案是: ${result.correct_answer}。${result.explanation}`;

        document.querySelectorAll('.option-item').forEach(item => {
            if (item.dataset.value === userAnswer) {
                item.classList.add('wrong');
            }
            if (item.dataset.value === result.correct_answer) {
                item.classList.add('correct');
            }
        });
    }

    masteryUpdate.innerHTML = '等待Agent评估中...';
}

function hideFeedback() {
    document.getElementById('feedback-area').style.display = 'none';
}

// ===== 请求提示 =====
function requestHint() {
    if (!currentQuestion) return;

    addChatMessage('user', '我需要一点提示...');

    // 模拟触发Hint Agent
    if (ws && ws.readyState === WebSocket.OPEN) {
        // 连续错误2次触发提示
        ws.send(JSON.stringify({
            type: 'answer',
            question_id: currentQuestion.question_id,
            answer: 'WRONG_HINT_TRIGGER'
        }));
    }
}

// ===== 处理各Agent响应 =====
function handleTutorResponse(payload) {
    const msg = payload.message || '';
    addChatMessage('system', msg);

    // 朗读（可选）
    // speak(msg);
}

function handleMasteryUpdate(payload) {
    const masteryEl = document.getElementById('mastery-update');
    if (masteryEl) {
        const pKnown = (payload.p_known * 100).toFixed(1);
        const isCorrect = payload.is_correct;
        const arrow = isCorrect ? '↑' : '↓';
        const color = isCorrect ? 'var(--secondary)' : 'var(--danger)';
        masteryEl.innerHTML = `掌握度更新: <span class="arrow" style="color:${color}">${arrow}</span> ${pKnown}%`;
    }

    updateEngagementMeter();
}

function handleCurriculumUpdate(payload) {
    if (payload.next_review) {
        addReviewItem(payload.knowledge_point_id, payload.next_review, payload.interval_days);
    }
    if (payload.action === 'slow_down') {
        addSystemMessage('📉 Curriculum Agent: 已调整学习节奏，降低难度');
    }
}

function handleEngagementAlert(payload) {
    addSystemMessage(`⚠️ Engagement Alert: ${payload.message}`);
    updateEngagementMeter();

    // 视觉提示
    document.querySelector('.engagement-meter').style.animation = 'pulse 1s ease 3';
    setTimeout(() => {
        document.querySelector('.engagement-meter').style.animation = '';
    }, 3000);
}

function handleHintResponse(payload) {
    const level = payload.level;
    const hint = payload.hint;
    addChatMessage('system', `💡 [提示 Level ${level}] ${hint}`);
}

function handleAssessmentComplete(payload) {
    // 评估完成，更新UI
    console.log('Assessment complete:', payload);
}

// ===== 聊天消息 =====
function addChatMessage(type, text) {
    const container = document.getElementById('chat-messages');
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.innerHTML = `
        <div class="message-bubble">${escapeHtml(text)}</div>
        <span class="message-time">${time}</span>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addSystemMessage(text) {
    addChatMessage('system', text);
}

// ===== 事件流可视化 =====
function addEventToStream(data) {
    const list = document.getElementById('events-list');
    const time = new Date(data.timestamp || Date.now()).toLocaleTimeString('zh-CN', { 
        hour: '2-digit', minute: '2-digit', second: '2-digit' 
    });

    const sourceClass = (data.source || 'system').toLowerCase().replace('agent', '');
    const payloadStr = JSON.stringify(data.payload || {}).substring(0, 80);

    const div = document.createElement('div');
    div.className = `event-item ${sourceClass}`;
    div.innerHTML = `
        <span class="event-time">${time}</span>
        <div class="event-content">
            <div class="event-type">${data.type}</div>
            <div class="event-source">from ${data.source}</div>
            <div class="event-payload">${escapeHtml(payloadStr)}${payloadStr.length >= 80 ? '...' : ''}</div>
        </div>
    `;

    list.insertBefore(div, list.firstChild);

    // 限制数量
    while (list.children.length > 50) {
        list.removeChild(list.lastChild);
    }
}

// ===== Agent状态更新 =====
function updateAgentStatus(source, eventType) {
    const agentMap = {
        'AssessmentAgent': 'status-assessment',
        'CurriculumAgent': 'status-curriculum',
        'TutorAgent': 'status-tutor',
        'EngagementAgent': 'status-engagement',
        'HintAgent': 'status-hint'
    };

    const elId = agentMap[source];
    if (!elId) return;

    const el = document.getElementById(elId);
    el.classList.add('active');

    const statusText = el.querySelector('.status-text');
    statusText.textContent = '处理中...';

    clearTimeout(el._timeout);
    el._timeout = setTimeout(() => {
        el.classList.remove('active');
        statusText.textContent = source === 'EngagementAgent' ? '监测中' : '待命';
    }, 2000);
}

// ===== 掌握度加载 =====
async function loadMastery() {
    try {
        const res = await fetch(`${API_BASE}/api/students/${studentId}/mastery`);
        const data = await res.json();
        renderMastery(data);
    } catch (err) {
        console.error('Load mastery failed:', err);
    }
}

function renderMastery(data) {
    const container = document.getElementById('mastery-list');

    if (data.length === 0) {
        container.innerHTML = '<div class="empty-state">开始答题后将显示掌握度数据</div>';
        return;
    }

    container.innerHTML = data.map(item => {
        const pct = Math.round(item.p_known * 100);
        let color = 'var(--danger)';
        if (pct >= 70) color = 'var(--secondary)';
        else if (pct >= 40) color = 'var(--warning)';

        return `
            <div class="mastery-item">
                <div class="mastery-info">
                    <span class="mastery-name">${item.name}</span>
                    <span class="mastery-subject">${item.subject}</span>
                </div>
                <div class="mastery-bar-container">
                    <div class="mastery-bar">
                        <div class="mastery-bar-fill" style="width:${pct}%;background:${color}"></div>
                    </div>
                    <span class="mastery-value" style="color:${color}">${pct}%</span>
                </div>
            </div>
        `;
    }).join('');
}

// ===== 复习计划 =====
function addReviewItem(kpId, nextReview, intervalDays) {
    const container = document.getElementById('review-plan');

    // 移除空状态
    if (container.querySelector('.empty-state')) {
        container.innerHTML = '';
    }

    const date = new Date(nextReview);
    const dateStr = date.toLocaleDateString('zh-CN');
    const kpName = kpId; // 简化显示

    const div = document.createElement('div');
    div.className = 'review-item';
    div.innerHTML = `
        <span class="review-name">${kpName}</span>
        <span class="review-date">${dateStr} (间隔${intervalDays}天)</span>
    `;

    container.appendChild(div);
}

// ===== 参与度仪表 =====
async function updateEngagementMeter() {
    try {
        const res = await fetch(`${API_BASE}/api/students/${studentId}`);
        const data = await res.json();
        const score = Math.round(data.engagement_score * 100);

        document.getElementById('engagement-fill').style.width = `${score}%`;
        document.getElementById('engagement-value').textContent = `${score}%`;

        // 颜色变化
        const fill = document.getElementById('engagement-fill');
        if (score < 30) {
            fill.style.background = 'var(--danger)';
        } else if (score < 60) {
            fill.style.background = 'var(--warning)';
        } else {
            fill.style.background = 'linear-gradient(90deg, var(--danger), var(--warning), var(--secondary))';
        }
    } catch (err) {
        console.error(err);
    }
}

// ===== 工具函数 =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function shakeElement(el) {
    el.style.animation = 'shake 0.5s ease';
    setTimeout(() => el.style.animation = '', 500);
}

// 添加shake动画到CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
`;
document.head.appendChild(style);
