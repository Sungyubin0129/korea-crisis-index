/**
 * 한국 경제 위기 지수 - 대시보드 스크립트
 */

// 데이터 파일 경로
const DATA_URL = 'data/indicators.json';

// 로컬 스토리지 키
const STORAGE_KEYS = {
    reaction: 'keci_reaction_voted',
    poll: 'keci_poll_voted'
};

// DOM 요소
const elements = {
    updateTime: document.getElementById('updateTime'),
    overallRiskCard: document.getElementById('overallRiskCard'),
    riskStatus: document.getElementById('riskStatus'),
    riskScore: document.getElementById('riskScore'),
    gaugeNeedle: document.getElementById('gaugeNeedle'),
    indicatorsGrid: document.getElementById('indicatorsGrid'),
    // 리액션
    btnWorried: document.getElementById('btnWorried'),
    btnNeutral: document.getElementById('btnNeutral'),
    btnOkay: document.getElementById('btnOkay'),
    countWorried: document.getElementById('countWorried'),
    countNeutral: document.getElementById('countNeutral'),
    countOkay: document.getElementById('countOkay'),
    reactionNote: document.getElementById('reactionNote'),
    // 투표
    pollQuestion: document.getElementById('pollQuestion'),
    pollOptions: document.getElementById('pollOptions'),
    pollTotal: document.getElementById('pollTotal'),
    pollNote: document.getElementById('pollNote')
};

// 현재 투표 데이터 (로컬 모드용 - 초기값 0)
let localReactions = { worried: 0, neutral: 0, okay: 0 };
let localPollVotes = [0, 0, 0, 0, 0];
let pollData = null;

/**
 * 데이터 로드
 */
async function loadData() {
    try {
        const response = await fetch(DATA_URL);
        if (!response.ok) throw new Error('데이터를 불러올 수 없습니다.');
        return await response.json();
    } catch (error) {
        console.error('데이터 로드 오류:', error);
        return null;
    }
}

/**
 * 숫자 포맷팅
 */
function formatValue(value, unit) {
    if (Math.abs(value) >= 1000) {
        return value.toLocaleString('ko-KR') + unit;
    }
    return value.toFixed(2) + unit;
}

/**
 * 게이지 바늘 각도 계산
 * score: 1 (안전) ~ 3 (위험)
 * 게이지: 왼쪽(초록, 안전) -> 오른쪽(빨강, 위험)
 * 각도: -90도 (왼쪽 끝) ~ 90도 (오른쪽 끝)
 */
function calculateNeedleAngle(score) {
    // score 1 -> -90도 (초록/안전)
    // score 2 -> 0도 (노랑/중간)
    // score 3 -> 90도 (빨강/위험)
    const normalized = (score - 1) / 2; // 0 ~ 1
    const angle = -90 + (normalized * 180); // -90 ~ 90
    return angle;
}

/**
 * 종합 위험도 업데이트
 */
function updateOverallRisk(overallRisk) {
    const { class: riskClass, text, score } = overallRisk;
    
    elements.overallRiskCard.className = `overall-risk-card ${riskClass}`;
    elements.riskStatus.textContent = text;
    elements.riskStatus.className = `risk-status ${riskClass}`;
    elements.riskScore.textContent = `위험 점수: ${score.toFixed(2)} / 3.0`;
    
    const angle = calculateNeedleAngle(score);
    elements.gaugeNeedle.style.transform = `rotate(${angle}deg)`;
}

/**
 * 바 너비 계산 (%)
 */
function calculateBarWidth(value, min, max) {
    const normalized = (value - min) / (max - min);
    return Math.max(0, Math.min(100, normalized * 100));
}

/**
 * 지표 카드 생성
 */
function createIndicatorCard(key, indicator) {
    const {
        name, unit, value, min, max,
        risk_class, risk_text, description, date
    } = indicator;
    
    const barWidth = calculateBarWidth(value, min, max);
    const formattedValue = formatValue(value, unit);
    
    return `
        <div class="indicator-card ${risk_class}">
            <div class="indicator-header">
                <span class="indicator-name">${name}</span>
                <span class="indicator-badge ${risk_class}">${risk_text}</span>
            </div>
            <div class="indicator-value ${risk_class}">${formattedValue}</div>
            <div class="indicator-bar-container">
                <div class="indicator-bar ${risk_class}" style="width: ${barWidth}%"></div>
            </div>
            <div class="indicator-footer">
                <span class="indicator-description">${description}</span>
                <span class="indicator-date">${date}</span>
            </div>
        </div>
    `;
}

/**
 * 지표 그리드 렌더링
 */
function renderIndicators(indicators) {
    const cards = Object.entries(indicators)
        .map(([key, indicator]) => createIndicatorCard(key, indicator))
        .join('');
    
    elements.indicatorsGrid.innerHTML = cards;
}

/**
 * 업데이트 시간 표시
 */
function updateTimestamp(updatedDate) {
    elements.updateTime.textContent = updatedDate;
}

// ============================================
// 리액션 기능
// ============================================

/**
 * 리액션 카운트 업데이트
 */
function updateReactionCounts(reactions) {
    elements.countWorried.textContent = reactions.worried.toLocaleString();
    elements.countNeutral.textContent = reactions.neutral.toLocaleString();
    elements.countOkay.textContent = reactions.okay.toLocaleString();
}

/**
 * 리액션 로드 (Firebase 또는 로컬)
 */
async function loadReactions() {
    if (typeof firebaseInitialized !== 'undefined' && firebaseInitialized && db) {
        try {
            const doc = await db.collection('reactions').doc('counts').get();
            if (doc.exists) {
                const data = doc.data();
                updateReactionCounts(data);
                return data;
            }
        } catch (error) {
            console.error('리액션 로드 오류:', error);
        }
    }
    
    // 로컬 모드
    updateReactionCounts(localReactions);
    return localReactions;
}

/**
 * 리액션 저장
 */
async function saveReaction(type) {
    if (typeof firebaseInitialized !== 'undefined' && firebaseInitialized && db) {
        try {
            const docRef = db.collection('reactions').doc('counts');
            await db.runTransaction(async (transaction) => {
                const doc = await transaction.get(docRef);
                const newCount = (doc.exists ? doc.data()[type] : 0) + 1;
                transaction.set(docRef, { [type]: newCount }, { merge: true });
            });
            await loadReactions();
        } catch (error) {
            console.error('리액션 저장 오류:', error);
        }
    } else {
        // 로컬 모드
        localReactions[type]++;
        updateReactionCounts(localReactions);
    }
}

/**
 * 리액션 버튼 클릭 처리
 */
function handleReactionClick(type) {
    // 이미 투표했는지 확인
    const voted = localStorage.getItem(STORAGE_KEYS.reaction);
    if (voted) {
        elements.reactionNote.textContent = '이미 참여하셨습니다. 내일 다시 참여해주세요!';
        return;
    }
    
    // 투표 저장
    saveReaction(type);
    
    // 로컬 스토리지에 기록 (24시간 후 만료)
    const expiry = Date.now() + 24 * 60 * 60 * 1000;
    localStorage.setItem(STORAGE_KEYS.reaction, JSON.stringify({ type, expiry }));
    
    // UI 업데이트
    document.querySelectorAll('.reaction-btn').forEach(btn => {
        btn.classList.add('disabled');
        if (btn.dataset.reaction === type) {
            btn.classList.add('selected');
        }
    });
    
    elements.reactionNote.textContent = '참여해주셔서 감사합니다! 🙏';
}

/**
 * 리액션 초기화
 */
function initReactions() {
    // 만료 체크
    const stored = localStorage.getItem(STORAGE_KEYS.reaction);
    if (stored) {
        const { type, expiry } = JSON.parse(stored);
        if (Date.now() > expiry) {
            localStorage.removeItem(STORAGE_KEYS.reaction);
        } else {
            // 이미 투표함 표시
            document.querySelectorAll('.reaction-btn').forEach(btn => {
                btn.classList.add('disabled');
                if (btn.dataset.reaction === type) {
                    btn.classList.add('selected');
                }
            });
            elements.reactionNote.textContent = '오늘 이미 참여하셨습니다.';
        }
    }
    
    // 이벤트 리스너
    elements.btnWorried.addEventListener('click', () => handleReactionClick('worried'));
    elements.btnNeutral.addEventListener('click', () => handleReactionClick('neutral'));
    elements.btnOkay.addEventListener('click', () => handleReactionClick('okay'));
    
    // 카운트 로드
    loadReactions();
}

// ============================================
// 투표 기능
// ============================================

/**
 * 투표 옵션 렌더링
 */
function renderPollOptions(options, votes, userVoted) {
    const total = votes.reduce((a, b) => a + b, 0);
    
    const optionsHtml = options.map((option, index) => {
        const count = votes[index] || 0;
        const percent = total > 0 ? Math.round((count / total) * 100) : 0;
        const isSelected = userVoted === index;
        const disabledClass = userVoted !== null ? 'disabled' : '';
        const selectedClass = isSelected ? 'selected' : '';
        
        return `
            <div class="poll-option ${disabledClass} ${selectedClass}" data-index="${index}">
                <div class="poll-option-bar" style="width: ${userVoted !== null ? percent : 0}%"></div>
                <div class="poll-option-content">
                    <span class="poll-option-text">${option}</span>
                    <span class="poll-option-percent">${userVoted !== null ? percent + '%' : ''}</span>
                </div>
            </div>
        `;
    }).join('');
    
    elements.pollOptions.innerHTML = optionsHtml;
    elements.pollTotal.textContent = total > 0 ? `총 ${total.toLocaleString()}명 참여` : '';
    
    // 이벤트 리스너 추가 (아직 투표 안 했으면)
    if (userVoted === null) {
        document.querySelectorAll('.poll-option').forEach(option => {
            option.addEventListener('click', () => handlePollVote(parseInt(option.dataset.index)));
        });
    }
}

/**
 * 투표 로드 (Firebase 또는 로컬)
 */
async function loadPoll() {
    let votes = localPollVotes;
    
    if (typeof firebaseInitialized !== 'undefined' && firebaseInitialized && db) {
        try {
            const doc = await db.collection('polls').doc('current').get();
            if (doc.exists) {
                votes = doc.data().votes || localPollVotes;
            }
        } catch (error) {
            console.error('투표 로드 오류:', error);
        }
    }
    
    // 사용자 투표 여부 확인
    let userVoted = null;
    const stored = localStorage.getItem(STORAGE_KEYS.poll);
    if (stored) {
        const { index, expiry } = JSON.parse(stored);
        if (Date.now() > expiry) {
            localStorage.removeItem(STORAGE_KEYS.poll);
        } else {
            userVoted = index;
            elements.pollNote.textContent = '이번 주 설문에 이미 참여하셨습니다.';
        }
    }
    
    if (pollData) {
        renderPollOptions(pollData.options, votes, userVoted);
    }
}

/**
 * 투표 저장
 */
async function savePollVote(index) {
    if (typeof firebaseInitialized !== 'undefined' && firebaseInitialized && db) {
        try {
            const docRef = db.collection('polls').doc('current');
            await db.runTransaction(async (transaction) => {
                const doc = await transaction.get(docRef);
                let votes = doc.exists ? (doc.data().votes || [...localPollVotes]) : [...localPollVotes];
                votes[index] = (votes[index] || 0) + 1;
                transaction.set(docRef, { votes }, { merge: true });
            });
        } catch (error) {
            console.error('투표 저장 오류:', error);
        }
    } else {
        localPollVotes[index]++;
    }
}

/**
 * 투표 클릭 처리
 */
async function handlePollVote(index) {
    // 이미 투표했는지 확인
    const voted = localStorage.getItem(STORAGE_KEYS.poll);
    if (voted) {
        return;
    }
    
    // 투표 저장
    await savePollVote(index);
    
    // 로컬 스토리지에 기록 (7일 후 만료)
    const expiry = Date.now() + 7 * 24 * 60 * 60 * 1000;
    localStorage.setItem(STORAGE_KEYS.poll, JSON.stringify({ index, expiry }));
    
    // UI 업데이트
    elements.pollNote.textContent = '참여해주셔서 감사합니다! 🙏';
    
    // 결과 다시 로드
    await loadPoll();
}

/**
 * 투표 초기화
 */
function initPoll(poll) {
    if (!poll || !poll.active) {
        document.querySelector('.poll-section').style.display = 'none';
        return;
    }
    
    pollData = poll;
    elements.pollQuestion.textContent = poll.question;
    loadPoll();
}

// ============================================
// 메인 초기화
// ============================================

async function init() {
    const data = await loadData();
    
    if (!data) {
        elements.indicatorsGrid.innerHTML = `
            <div class="error-message">
                데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.
            </div>
        `;
        return;
    }
    
    // 데이터 렌더링
    updateTimestamp(data.updated_date);
    updateOverallRisk(data.overall_risk);
    renderIndicators(data.indicators);
    
    // 리액션 초기화
    initReactions();
    
    // 투표 초기화
    if (data.poll) {
        initPoll(data.poll);
    }
}

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', init);
