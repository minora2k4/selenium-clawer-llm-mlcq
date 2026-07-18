(function(){
"use strict";

const DATA_URL = '../output/questions_translated.json';
const HIST_KEY = 'mlcq_history_v1';

const app = document.getElementById('app');

// Được gán sau khi tải xong dữ liệu (xem loadData() + init() ở cuối file)
let TOPICS = [];
let ALL_QUESTIONS = [];
let TOTAL_Q = 0;

/* ---------------- Data loading & normalization ---------------- */

// Với các câu Đúng/Sai chỉ còn 1 lựa chọn trong dữ liệu gốc, suy ra lựa chọn còn lại.
const BINARY_MAP = {
  'Đúng': 'Sai', 'Sai': 'Đúng',
  'True': 'False', 'False': 'True',
  'Có': 'Không', 'Không': 'Có',
};

/**
 * Chuyển dữ liệu thô { title: {...}, html: {...} } thành mảng chủ đề đã chuẩn hoá:
 * [{ index, title, questions: [{ id, topicIndex, question, options, answer, explanation }] }]
 *
 * Một số câu trong dữ liệu gốc có `answer` trỏ tới một lựa chọn không tồn tại
 * (ví dụ câu Đúng/Sai chỉ crawl được 1 lựa chọn, hoặc thiếu lựa chọn "Tất cả các
 * đáp án trên"). Hàm này tự bổ sung lựa chọn còn thiếu để quiz chấm điểm đúng.
 */
function normalizeData(raw){
  const titles = raw.title;
  const htmlMap = raw.html;
  const topicKeys = Object.keys(titles).sort((a, b) => Number(a) - Number(b));

  let qid = 0;
  const topics = topicKeys.map(tkey => {
    const qlist = htmlMap[tkey] || [];
    const questions = qlist.map(q => {
      let opts = Object.entries(q.options); // giữ nguyên thứ tự a,b,c,d
      const keys = opts.map(([k]) => k);
      const answer = q.answer;

      if(!keys.includes(answer)){
        if(opts.length === 1 && BINARY_MAP[opts[0][1]]){
          opts = opts.concat([[answer, BINARY_MAP[opts[0][1]]]]);
        } else {
          opts = opts.concat([[answer, 'Tất cả các đáp án trên đều đúng']]);
        }
      }
      opts.sort((a, b) => a[0].localeCompare(b[0]));

      return {
        id: qid++,
        topicIndex: Number(tkey),
        question: (q.question || '').trim(),
        options: opts.map(([key, text]) => ({key, text})),
        answer,
        explanation: (q.explanation || '').trim(),
      };
    });
    return { index: Number(tkey), title: titles[tkey].trim(), questions };
  });

  return topics;
}

async function loadData(){
  const res = await fetch(DATA_URL);
  if(!res.ok) throw new Error(`HTTP ${res.status}`);
  const raw = await res.json();
  return normalizeData(raw);
}

function renderBootError(err){
  app.innerHTML = `
    <div class="boot-error">
      <h2>Không tải được dữ liệu câu hỏi</h2>
      <p>Trình duyệt chặn việc đọc file JSON cục bộ (${escapeHtml(err.message || String(err))}).</p>
      <p>Cách khắc phục: chạy một local server ở thư mục gốc dự án rồi mở qua <code>http://</code> thay vì mở file trực tiếp:</p>
      <p><code>python3 -m http.server 8000</code></p>
      <p>Sau đó mở <code>http://localhost:8000/app/index.html</code></p>
    </div>
  `;
}


function loadHistory(){
  try{ return JSON.parse(localStorage.getItem(HIST_KEY) || '[]'); }catch(e){ return []; }
}
function saveHistoryEntry(entry){
  const h = loadHistory();
  h.unshift(entry);
  localStorage.setItem(HIST_KEY, JSON.stringify(h.slice(0,20)));
}

function shuffle(arr){
  const a = arr.slice();
  for(let i=a.length-1;i>0;i--){
    const j = Math.floor(Math.random()*(i+1));
    [a[i],a[j]]=[a[j],a[i]];
  }
  return a;
}

function escapeHtml(str){
  return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

/* ---------------- State ---------------- */
let session = null; // {title, questions:[...], answers:{qid:key}, order index}
let currentIndex = 0;
let resultFilter = 'all';

/* ---------------- Session builders ---------------- */
function startSession(title, questions, opts){
  opts = opts || {};
  let qs = questions.slice();
  if(opts.shuffleQuestions !== false) qs = shuffle(qs);
  if(opts.limit) qs = qs.slice(0, opts.limit);
  session = {
    title: title,
    questions: qs,
    answers: {},
  };
  currentIndex = 0;
  renderQuiz();
}

function startFullQuiz(){
  startSession('Quiz đầy đủ', ALL_QUESTIONS, {shuffleQuestions:true});
}
function startMiniQuiz(){
  let picked = [];
  TOPICS.forEach(t=>{
    if(t.questions.length===0) return;
    picked = picked.concat(shuffle(t.questions).slice(0,5));
  });
  startSession('Mini Quiz (5 câu / chủ đề)', shuffle(picked), {shuffleQuestions:false});
}
function startTopicQuiz(topicIndex){
  const t = TOPICS.find(x=>x.index===topicIndex);
  if(!t) return;
  startSession(t.title, t.questions, {shuffleQuestions:true});
}

/* ---------------- Home screen ---------------- */
function renderHome(){
  const hist = loadHistory();
  const histHtml = hist.length ? hist.slice(0,6).map(h=>{
    const pct = Math.round(h.score/h.total*100);
    const cls = pct>=80?'good':(pct>=50?'mid':'low');
    return `<div class="history-item">
      <div>
        <div class="h-name">${escapeHtml(h.title)}</div>
        <div class="h-date">${escapeHtml(h.date)}</div>
      </div>
      <div class="history-score ${cls}">${h.score}/${h.total}</div>
    </div>`;
  }).join('') : `<div class="empty-note">Chưa có lượt làm bài nào. Bắt đầu quiz đầu tiên nhé!</div>`;

  const topicCards = TOPICS.map(t=>`
    <div class="topic-card" data-topic="${t.index}" tabindex="0" role="button">
      <span class="num">#${String(t.index+1).padStart(2,'0')}</span>
      <h4>${escapeHtml(t.title)}</h4>
      <div class="meta">${t.questions.length} câu hỏi</div>
    </div>`).join('');

  app.innerHTML = `
    <div class="top-bar">
      <div class="brand">
        <span class="brand-mark">MLCQ</span>
        <span class="brand-title">Ôn tập trắc nghiệm</span>
      </div>
    </div>

    <div class="hero">
      <h1>Machine Learning MCQ</h1>
      <p>Ôn lại kiến thức Machine Learning qua ${TOTAL_Q} câu hỏi trắc nghiệm, chia theo ${TOPICS.length} chủ đề — từ Linear Regression đến SVM, Decision Tree, Ensemble Learning...</p>
      <div class="stat-row">
        <div class="stat-chip"><b>${TOTAL_Q}</b> câu hỏi</div>
        <div class="stat-chip"><b>${TOPICS.length}</b> chủ đề</div>
        <div class="stat-chip"><b>${hist.length}</b> lượt đã làm</div>
      </div>
    </div>

    <div class="section-title">Bắt đầu <small>chọn chế độ</small></div>
    <div class="mode-grid">
      <div class="mode-card full" id="btn-full">
        <span class="tag">Toàn bộ</span>
        <h3>Quiz đầy đủ</h3>
        <p>Làm hết tất cả câu hỏi, thứ tự xáo trộn.</p>
        <span class="count">${TOTAL_Q} câu · ~${Math.round(TOTAL_Q*25/60)} phút</span>
      </div>
      <div class="mode-card mini" id="btn-mini">
        <span class="tag">Nhanh</span>
        <h3>Mini Quiz</h3>
        <p>5 câu ngẫu nhiên mỗi chủ đề, phủ toàn bộ nội dung.</p>
        <span class="count">${TOPICS.length*5} câu · ~${Math.round(TOPICS.length*5*25/60)} phút</span>
      </div>
    </div>

    <div class="section-title">Ôn theo chủ đề <small>${TOPICS.length} mục</small></div>
    <div class="topic-grid">${topicCards}</div>

    <div class="section-title">Lịch sử <small>gần đây</small></div>
    <div class="history-list">${histHtml}</div>

    <div class="footer-note">Dữ liệu lưu cục bộ trên thiết bị của bạn · không gửi lên máy chủ</div>
  `;

  document.getElementById('btn-full').addEventListener('click', startFullQuiz);
  document.getElementById('btn-mini').addEventListener('click', startMiniQuiz);
  app.querySelectorAll('.topic-card').forEach(el=>{
    const go = ()=> startTopicQuiz(parseInt(el.dataset.topic,10));
    el.addEventListener('click', go);
    el.addEventListener('keydown', e=>{ if(e.key==='Enter' || e.key===' '){ e.preventDefault(); go(); }});
  });
}

/* ---------------- Quiz screen ---------------- */
function renderQuiz(){
  const total = session.questions.length;
  const q = session.questions[currentIndex];
  const answeredCount = Object.keys(session.answers).length;
  const selected = session.answers[q.id];
  const topicTitle = TOPICS.find(t=>t.index===q.topicIndex).title;

  const optionsHtml = q.options.map(o=>`
    <div class="option ${selected===o.key?'selected':''}" data-key="${o.key}">
      <span class="key">${o.key.toUpperCase()}</span>
      <span>${escapeHtml(o.text)}</span>
    </div>`).join('');

  const navDots = session.questions.map((qq,i)=>{
    const ans = session.answers[qq.id]!==undefined;
    return `<div class="qnav-dot ${ans?'answered':''} ${i===currentIndex?'current':''}" data-idx="${i}">${i+1}</div>`;
  }).join('');

  app.innerHTML = `
    <div class="quiz-topbar">
      <button class="icon-btn" id="btn-exit">← Thoát</button>
      <span class="q-counter">${session.title} · ${answeredCount}/${total} đã trả lời</span>
      <button class="icon-btn" id="btn-toggle-nav">Danh sách câu</button>
    </div>
    <div class="progress-track"><div class="progress-fill" style="width:${(currentIndex+1)/total*100}%"></div></div>

    <div class="qnav-panel" id="qnav-panel">
      <div class="qnav-grid">${navDots}</div>
    </div>

    <span class="q-topic-tag">${escapeHtml(topicTitle)}</span>
    <div class="q-card">
      <p class="q-text">${escapeHtml(q.question)}</p>
      <div class="options" id="options-wrap">${optionsHtml}</div>
    </div>

    <div class="quiz-nav">
      <div class="side">
        <button class="btn btn-secondary" id="btn-prev" ${currentIndex===0?'disabled':''}>Câu trước</button>
      </div>
      <span class="q-counter">Câu ${currentIndex+1} / ${total}</span>
      <div class="side">
        ${currentIndex===total-1
          ? `<button class="btn btn-submit" id="btn-submit">Nộp bài</button>`
          : `<button class="btn btn-primary" id="btn-next">Câu tiếp theo</button>`}
      </div>
    </div>
  `;

  app.querySelectorAll('#options-wrap .option').forEach(el=>{
    el.addEventListener('click', ()=>{
      session.answers[q.id] = el.dataset.key;
      renderQuiz();
    });
  });
  document.getElementById('btn-exit').addEventListener('click', confirmExit);
  document.getElementById('btn-prev').addEventListener('click', ()=>{ currentIndex--; renderQuiz(); });
  const nextBtn = document.getElementById('btn-next');
  if(nextBtn) nextBtn.addEventListener('click', ()=>{ currentIndex++; renderQuiz(); });
  const submitBtn = document.getElementById('btn-submit');
  if(submitBtn) submitBtn.addEventListener('click', finishQuiz);

  const toggleBtn = document.getElementById('btn-toggle-nav');
  const panel = document.getElementById('qnav-panel');
  toggleBtn.addEventListener('click', ()=> panel.classList.toggle('open'));
  panel.querySelectorAll('.qnav-dot').forEach(d=>{
    d.addEventListener('click', ()=>{ currentIndex = parseInt(d.dataset.idx,10); renderQuiz(); });
  });

  window.scrollTo({top:0, behavior:'instant' in window ? 'instant':'auto'});
}

function confirmExit(){
  const answeredCount = Object.keys(session.answers).length;
  if(answeredCount>0){
    if(!confirm('Bạn có chắc muốn thoát? Kết quả làm bài hiện tại sẽ không được lưu.')) return;
  }
  session = null;
  renderHome();
}

function finishQuiz(){
  resultFilter = 'all';
  renderResult();
}

/* ---------------- Result screen ---------------- */
function renderResult(){
  const qs = session.questions;
  const total = qs.length;
  let correct = 0;
  const perTopic = {};

  qs.forEach(q=>{
    const userKey = session.answers[q.id];
    const isCorrect = userKey === q.answer;
    if(isCorrect) correct++;
    const tt = TOPICS.find(t=>t.index===q.topicIndex).title;
    if(!perTopic[tt]) perTopic[tt] = {correct:0, total:0};
    perTopic[tt].total++;
    if(isCorrect) perTopic[tt].correct++;
  });

  const pct = Math.round(correct/total*100);
  const ringColor = pct>=80 ? 'var(--success)' : (pct>=50 ? 'var(--accent-2)' : 'var(--danger)');
  const circumference = 2*Math.PI*40;
  const dash = circumference*pct/100;

  // save history once
  if(!session._saved){
    saveHistoryEntry({
      title: session.title,
      score: correct,
      total: total,
      date: new Date().toLocaleString('vi-VN'),
    });
    session._saved = true;
  }

  const topicRows = Object.entries(perTopic).map(([name,v])=>{
    const p = Math.round(v.correct/v.total*100);
    return `<div class="tb-row">
      <div class="tb-name">${escapeHtml(name)}</div>
      <div class="tb-bar-track"><div class="tb-bar-fill" style="width:${p}%"></div></div>
      <div class="tb-frac">${v.correct}/${v.total}</div>
    </div>`;
  }).join('');

  let filtered = qs;
  if(resultFilter==='wrong') filtered = qs.filter(q => session.answers[q.id] !== q.answer);
  if(resultFilter==='correct') filtered = qs.filter(q => session.answers[q.id] === q.answer);

  const reviewHtml = filtered.map((q,i)=>{
    const userKey = session.answers[q.id];
    const isCorrect = userKey === q.answer;
    const optsHtml = q.options.map(o=>{
      let cls = '';
      if(o.key === q.answer) cls = 'correct-answer';
      else if(o.key === userKey) cls = 'wrong-answer';
      return `<div class="option disabled ${cls}">
        <span class="key">${o.key.toUpperCase()}</span>
        <span>${escapeHtml(o.text)}</span>
      </div>`;
    }).join('');
    const topicTitle = TOPICS.find(t=>t.index===q.topicIndex).title;
    return `<div class="review-card">
      <div class="rc-head">
        <span class="rc-badge ${isCorrect?'ok':'bad'}">${isCorrect?'✓ ĐÚNG':'✗ SAI'}</span>
        <span class="rc-topic">${escapeHtml(topicTitle)}</span>
        ${userKey===undefined ? '<span class="rc-topic">(chưa trả lời)</span>' : ''}
      </div>
      <p class="q-text">${escapeHtml(q.question)}</p>
      <div class="options">${optsHtml}</div>
      <div class="rc-explain"><b>Giải thích:</b> ${escapeHtml(q.explanation || 'Không có giải thích.')}</div>
    </div>`;
  }).join('') || `<div class="empty-note">Không có câu nào trong mục này.</div>`;

  app.innerHTML = `
    <div class="top-bar">
      <div class="brand">
        <span class="brand-mark">MLCQ</span>
        <span class="brand-title">Kết quả</span>
      </div>
    </div>

    <div class="result-hero">
      <div class="score-ring">
        <svg width="96" height="96" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="40" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="8"/>
          <circle cx="48" cy="48" r="40" fill="none" stroke="${ringColor}" stroke-width="8"
            stroke-dasharray="${dash} ${circumference}" stroke-linecap="round"/>
        </svg>
        <div class="pct">${pct}%</div>
      </div>
      <div class="r-text">
        <h2>${correct}/${total} câu đúng</h2>
        <p>${escapeHtml(session.title)}</p>
      </div>
    </div>

    ${Object.keys(perTopic).length>1 ? `<div class="section-title">Theo chủ đề</div><div class="topic-breakdown">${topicRows}</div>` : ''}

    <div class="section-title">Xem lại câu hỏi</div>
    <div class="filter-tabs">
      <button class="filter-tab ${resultFilter==='all'?'active':''}" data-f="all">Tất cả (${total})</button>
      <button class="filter-tab ${resultFilter==='wrong'?'active':''}" data-f="wrong">Câu sai (${total-correct})</button>
      <button class="filter-tab ${resultFilter==='correct'?'active':''}" data-f="correct">Câu đúng (${correct})</button>
    </div>
    <div id="review-list">${reviewHtml}</div>

    <div class="result-actions">
      <button class="btn btn-primary" id="btn-retry">Làm lại quiz này</button>
      <button class="btn btn-secondary" id="btn-home">Về trang chủ</button>
    </div>
  `;

  app.querySelectorAll('.filter-tab').forEach(el=>{
    el.addEventListener('click', ()=>{ resultFilter = el.dataset.f; renderResult(); });
  });
  document.getElementById('btn-retry').addEventListener('click', ()=>{
    startSession(session.title, session.questions, {shuffleQuestions:true});
  });
  document.getElementById('btn-home').addEventListener('click', ()=>{ session=null; renderHome(); });

  window.scrollTo({top:0, behavior:'instant' in window ? 'instant':'auto'});
}

/* ---------------- Init ---------------- */
loadData()
  .then(topics => {
    TOPICS = topics;
    ALL_QUESTIONS = TOPICS.flatMap(t => t.questions);
    TOTAL_Q = ALL_QUESTIONS.length;
    renderHome();
  })
  .catch(renderBootError);

})();
