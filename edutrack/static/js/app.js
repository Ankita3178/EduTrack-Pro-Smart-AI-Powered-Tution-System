// ==================== STATE ====================
let currentRole = null;
let currentStudent = null;
let currentLoginTab = 'tutor';
let allStudents = [];
let allAttendance = [];
let allMarks = [];
let allNotes = [];
let allAnnouncements = [];
let chatHistory = [];
let noteFileData = null;
let currentAttDate = '';

// ==================== UTILS ====================
function toast(msg, color = 'var(--accent2)', dur = 4000) {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = 'toast';
  t.style.borderLeftColor = color;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), dur);
}

async function api(path, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  return res.json();
}

function fmtPct(p) {
  return `<span style="color:${p >= 60 ? 'var(--green)' : 'var(--red)'};font-weight:700;">${p}%</span>`;
}

function annClass(type) {
  return type === 'Test Reminder' ? 'test' : type === 'Fee Reminder' ? 'fee' : 'general';
}

// ==================== LOGIN ====================
function switchLoginTab(tab, el) {
  currentLoginTab = tab;
  document.querySelectorAll('.login-tab').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
}

async function doLogin() {
  const username = document.getElementById('login-user').value.trim();
  const password = document.getElementById('login-pass').value.trim();
  const res = await api('/api/login', 'POST', { role: currentLoginTab, username, password });
  if (!res.ok) { toast(res.error, 'var(--red)'); return; }

  currentRole = res.role;
  document.getElementById('login-page').style.display = 'none';
  document.getElementById('app').style.display = 'flex';
  document.getElementById('role-badge').textContent = res.role === 'tutor' ? 'Tutor' : 'Student';
  document.getElementById('sidebar-role-name').textContent = res.username;

  if (res.role === 'tutor') {
    document.getElementById('tutor-nav').style.display = 'block';
    document.getElementById('student-nav').style.display = 'none';
    document.getElementById('sidebar-role-sub').textContent = 'Tutor Account';
    await loadAllData();
    showPage('dashboard');
    runStartupChecks();
  } else {
    currentStudent = res.username;
    document.getElementById('tutor-nav').style.display = 'none';
    document.getElementById('student-nav').style.display = 'block';
    document.getElementById('sidebar-role-sub').textContent = 'Student Portal';
    await loadAllData();
    showPage('s-dashboard');
    renderStudentDashboard();
  }
}

async function doLogout() {
  await api('/api/logout', 'POST');
  currentRole = null; currentStudent = null;
  document.getElementById('app').style.display = 'none';
  document.getElementById('login-page').style.display = 'flex';
  document.getElementById('login-user').value = '';
  document.getElementById('login-pass').value = '';
  chatHistory = [];
}

// ==================== FORGOT PASSWORD ====================
async function showForgot() {
  const modal = document.getElementById('forgot-modal');
  const form = document.getElementById('forgot-form');
  modal.classList.remove('hidden');

  if (currentLoginTab === 'tutor') {
    const sqRes = await api('/api/tutor_secret_question');
    form.innerHTML = `
      <p style="color:var(--text2);font-size:13px;margin-bottom:12px;">Answer the security question to reset your password.</p>
      <div class="form-group"><label>${sqRes.question}</label><input type="text" id="fp-ans" placeholder="Your answer"/></div>
      <div class="form-group"><label>New Password</label><input type="password" id="fp-new"/></div>
      <div class="form-group"><label>Confirm Password</label><input type="password" id="fp-con"/></div>
      <button class="btn btn-primary" onclick="resetTutorPwd()">Reset Password</button>`;
  } else {
    form.innerHTML = `
      <div class="form-group"><label>Your Name</label><input type="text" id="fp-name"/></div>
      <div class="form-group"><label>Parent's Name</label><input type="text" id="fp-parent"/></div>
      <div class="form-group"><label>New Password</label><input type="password" id="fp-new"/></div>
      <div class="form-group"><label>Confirm Password</label><input type="password" id="fp-con"/></div>
      <button class="btn btn-success" onclick="resetStudentPwd()">Reset Password</button>`;
  }
}

async function resetTutorPwd() {
  const res = await api('/api/forgot_password', 'POST', {
    role: 'tutor',
    answer: document.getElementById('fp-ans').value.trim(),
    new_password: document.getElementById('fp-new').value.trim(),
    confirm_password: document.getElementById('fp-con').value.trim()
  });
  if (res.ok) { toast('Password reset! Login again.', 'var(--green)'); document.getElementById('forgot-modal').classList.add('hidden'); }
  else toast(res.error, 'var(--red)');
}

async function resetStudentPwd() {
  const res = await api('/api/forgot_password', 'POST', {
    role: 'student',
    student_name: document.getElementById('fp-name').value.trim(),
    parent_name: document.getElementById('fp-parent').value.trim(),
    new_password: document.getElementById('fp-new').value.trim(),
    confirm_password: document.getElementById('fp-con').value.trim()
  });
  if (res.ok) { toast('Password reset!', 'var(--green)'); document.getElementById('forgot-modal').classList.add('hidden'); }
  else toast(res.error, 'var(--red)');
}

// ==================== DATA LOAD ====================
async function loadAllData() {
  const [s, a, m, n, ann] = await Promise.all([
    api('/api/students'), api('/api/attendance'), api('/api/marks'),
    api('/api/notes'), api('/api/announcements')
  ]);
  allStudents = s;
  allAttendance = a;
  allMarks = m;
  allNotes = n;
  allAnnouncements = ann;
}

// ==================== STARTUP ====================
function runStartupChecks() {
  const today = new Date(); today.setHours(0,0,0,0);
  for (const s of allStudents) {
    if (!s.fees_due_date) continue;
    const due = new Date(s.fees_due_date); due.setHours(0,0,0,0);
    const diff = Math.round((due - today) / 86400000);
    if (diff === 3) setTimeout(() => toast(`💰 FEES REMINDER: ${s.name}'s fees due in 3 days!`, 'var(--yellow)'), 1000);
    else if (diff === 0) setTimeout(() => toast(`⚠️ FEES DUE TODAY: ${s.name}!`, 'var(--red)'), 1000);
    else if (diff < 0) setTimeout(() => toast(`❗ OVERDUE: ${s.name}'s fees ${Math.abs(diff)} day(s) overdue!`, '#c0392b'), 1000);
  }
}

// ==================== SIDEBAR ====================
function showPage(id) {
  document.querySelectorAll('.page').forEach(p => { p.classList.remove('active'); p.style.display = ''; });
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));

  const chatPage = document.getElementById('chat-page');
  if (id === 'chat') {
    chatPage.style.display = 'flex';
    chatPage.classList.add('active');
    document.getElementById('chat-nav-btn').classList.add('active');
    initChat();
  } else {
    chatPage.style.display = 'none';
    chatPage.classList.remove('active');
    const page = document.getElementById('page-' + id);
    if (page) { page.style.display = 'block'; page.classList.add('active'); }
    document.querySelectorAll('.nav-item').forEach(b => {
      if (b.getAttribute('onclick') && b.getAttribute('onclick').includes(`'${id}'`)) b.classList.add('active');
    });
    if (id === 'dashboard') renderDashboard();
    if (id === 'students') renderStudentTable();
    if (id === 'attendance') { document.getElementById('att-date').value = new Date().toISOString().slice(0,10); loadAttendanceTable(); }
    if (id === 'marks') { populateDropdown('marks-student'); renderMarksTable(); setDefaultWeek(); }
    if (id === 'performance') populateDropdown('perf-student');
    if (id === 'notes') { renderNotes(); populateNoteList(); }
    if (id === 'announcements') renderAnnouncements();
    if (id === 'fees') { populateDropdown('fees-student'); renderFeesDue(); }
    if (id === 'ml') { populateDropdown('ml-pred-student'); populateDropdown('ml-risk-student'); }
    if (id === 'settings') { const k = localStorage.getItem('et_api_key') || ''; document.getElementById('api-key-input').value = k; }
    if (id === 's-notes') renderStudentNotes();
    if (id === 's-attendance') renderStudentAtt();
    if (id === 's-marks') renderStudentMarks();
    if (id === 's-performance') renderStudentPerf();
    if (id === 's-announcements') renderStudentAnns();
  }
  closeSidebar();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('backdrop').classList.toggle('show');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('backdrop').classList.remove('show');
}

function populateDropdown(id) {
  const sel = document.getElementById(id);
  if (!sel) return;
  sel.innerHTML = allStudents.map(s => `<option value="${s.name}">${s.name}</option>`).join('');
}

function setDefaultWeek() {
  const d = new Date();
  const w = Math.ceil((((d - new Date(d.getFullYear(), 0, 1)) / 86400000) + new Date(d.getFullYear(), 0, 1).getDay() + 1) / 7);
  document.getElementById('marks-week').value = `${d.getFullYear()}-W${String(w).padStart(2,'0')}`;
}

// ==================== DASHBOARD ====================
function renderDashboard() {
  const today = new Date(); today.setHours(0,0,0,0);
  const todayStr = today.toISOString().slice(0,10);
  const todayAtt = allAttendance.filter(r => r.date === todayStr);
  const todayPresent = todayAtt.filter(r => r.status === 'P').length;
  const todayAbsent = todayAtt.filter(r => r.status === 'A').length;
  const feeAlerts = allStudents.filter(s => {
    if (!s.fees_due_date) return false;
    const d = new Date(s.fees_due_date); d.setHours(0,0,0,0);
    return (d - today) / 86400000 <= 3;
  }).length;

  document.getElementById('stats-grid').innerHTML = `
    <div class="stat-card accent"><div class="stat-label">Total Students</div><div class="stat-value">${allStudents.length}</div><div class="stat-sub">enrolled</div></div>
    <div class="stat-card green"><div class="stat-label">Present Today</div><div class="stat-value">${todayPresent}</div><div class="stat-sub">out of ${allStudents.length}</div></div>
    <div class="stat-card blue"><div class="stat-label">Absent Today</div><div class="stat-value">${todayAbsent}</div><div class="stat-sub">today</div></div>
    <div class="stat-card purple"><div class="stat-label">Fee Alerts</div><div class="stat-value">${feeAlerts}</div><div class="stat-sub">due soon</div></div>`;

  const da = document.getElementById('dash-anns');
  const anns = allAnnouncements.slice(0, 3);
  da.innerHTML = anns.length ? anns.map(a => `<div class="ann-card ${annClass(a.type)}"><div class="ann-type">${a.type}</div><div class="ann-title">${a.title}</div><div class="ann-msg">${a.message}</div><div class="ann-date">${a.date}</div></div>`).join('') : '<div class="empty-state"><div class="icon">📢</div><p>No announcements</p></div>';

  const df = document.getElementById('dash-fees');
  const rows = allStudents.filter(s => s.fees_due_date).map(s => {
    const due = new Date(s.fees_due_date); due.setHours(0,0,0,0);
    const diff = Math.round((due - today) / 86400000);
    const badge = diff > 3 ? `<span class="badge-ok">✅ OK</span>` : diff > 0 ? `<span class="badge-warn">⚠️ Due Soon</span>` : diff === 0 ? `<span class="badge-danger">🔴 Today</span>` : `<span class="badge-danger">❗ Overdue</span>`;
    return `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);"><span style="font-size:13px;">${s.name}</span><span style="font-size:12px;color:var(--text2);">${s.fees_due_date}</span>${badge}</div>`;
  }).join('');
  df.innerHTML = rows || '<div class="empty-state"><div class="icon">💰</div><p>No fee records</p></div>';
}

// ==================== STUDENTS ====================
async function addStudent() {
  const name = document.getElementById('st-name').value.trim();
  if (!name) { toast('Name cannot be empty', 'var(--red)'); return; }
  const res = await api('/api/students', 'POST', {
    name, class: document.getElementById('st-class').value.trim(),
    parent: document.getElementById('st-parent').value.trim(),
    fees: document.getElementById('st-fees').value.trim(),
    password: document.getElementById('st-pwd').value.trim(),
    fees_due_date: document.getElementById('st-due').value.trim()
  });
  if (res.ok) {
    toast(`Student '${name}' added!`, 'var(--green)');
    ['st-name','st-class','st-parent','st-fees','st-pwd'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('st-due').value = '';
    await loadAllData(); renderStudentTable();
  }
}

function renderStudentTable() {
  const filter = (document.getElementById('search-name') || {value:''}).value.toLowerCase();
  const rows = allStudents.filter(s => !filter || s.name.toLowerCase().includes(filter));
  const tbody = document.getElementById('students-tbody');
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No students found</td></tr>'; return; }
  tbody.innerHTML = rows.map((s, i) => `
    <tr><td>${i+1}</td><td><strong>${s.name}</strong></td><td>${s.class||'—'}</td><td>${s.parent||'—'}</td>
    <td>${s.fees||'—'}</td><td>${s.fees_due_date||'—'}</td>
    <td><button class="btn btn-danger btn-sm" onclick="deleteStudent(${s.id},'${s.name}')">Delete</button></td></tr>`).join('');
}

async function deleteStudent(id, name) {
  if (!confirm(`Delete '${name}'?`)) return;
  await api(`/api/students/${id}`, 'DELETE');
  toast(`'${name}' removed`, 'var(--yellow)');
  await loadAllData(); renderStudentTable();
}

// ==================== ATTENDANCE ====================
function openAttModal() {
  const date = document.getElementById('att-date').value;
  if (!date) { toast('Select a date', 'var(--red)'); return; }
  if (!allStudents.length) { toast('No students added yet', 'var(--red)'); return; }
  currentAttDate = date;
  document.getElementById('att-modal-date').textContent = date;
  const existing = {};
  allAttendance.filter(r => r.date === date).forEach(r => existing[r.student_name] = r.status);
  document.getElementById('att-modal-list').innerHTML = allStudents.map(s => `
    <div class="att-mark-row">
      <span class="att-name">${s.name}</span>
      <button class="att-btn present ${existing[s.name]==='P'?'active':''}" data-student="${s.name}" data-status="P" onclick="toggleAtt(this)">P</button>
      <button class="att-btn absent ${existing[s.name]==='A'?'active':''}" data-student="${s.name}" data-status="A" onclick="toggleAtt(this)">A</button>
    </div>`).join('');
  document.getElementById('att-modal').classList.remove('hidden');
}

function toggleAtt(btn) {
  const row = btn.closest('.att-mark-row');
  row.querySelectorAll('.att-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

async function saveAttendance() {
  const records = [];
  document.querySelectorAll('.att-mark-row').forEach(row => {
    const active = row.querySelector('.att-btn.active');
    if (active) records.push({ student_name: active.dataset.student, date: currentAttDate, status: active.dataset.status });
  });
  await api('/api/attendance', 'POST', records);
  toast('Attendance saved!', 'var(--green)');
  document.getElementById('att-modal').classList.add('hidden');
  await loadAllData(); loadAttendanceTable();
}

function loadAttendanceTable() {
  const wrap = document.getElementById('att-table-wrap');
  if (!allStudents.length) { wrap.innerHTML = '<div class="empty-state"><div class="icon">📅</div><p>No students yet</p></div>'; return; }
  const dates = [...new Set(allAttendance.map(r => r.date))].sort().slice(-10);
  let html = `<table><thead><tr><th>Student</th>${dates.map(d => `<th>${d}</th>`).join('')}<th>Present</th><th>%</th></tr></thead><tbody>`;
  for (const s of allStudents) {
    const recs = allAttendance.filter(r => r.student_name === s.name);
    const byDate = {};
    recs.forEach(r => byDate[r.date] = r.status);
    const p = recs.filter(r => r.status === 'P').length;
    const t = recs.length;
    const pct = t ? Math.round(p / t * 100) : 0;
    html += `<tr><td><strong>${s.name}</strong></td>${dates.map(d => `<td>${byDate[d] === 'P' ? '<span class="badge-p">P</span>' : byDate[d] === 'A' ? '<span class="badge-a">A</span>' : '—'}</td>`).join('')}<td>${p}/${t}</td><td>${fmtPct(pct)}</td></tr>`;
  }
  html += '</tbody></table>';
  wrap.innerHTML = html;
}

// ==================== MARKS ====================
async function saveMarks() {
  const student_name = document.getElementById('marks-student').value;
  const subject = document.getElementById('marks-subject').value.trim();
  const week = document.getElementById('marks-week').value.trim();
  const marks = document.getElementById('marks-got').value.trim();
  const total = document.getElementById('marks-total').value.trim();
  if (!student_name || !subject || !week || !marks || !total) { toast('Fill all fields', 'var(--red)'); return; }
  await api('/api/marks', 'POST', { student_name, subject, week, marks: +marks, total: +total });
  toast('Marks saved!', 'var(--green)');
  await loadAllData(); renderMarksTable();
}

function renderMarksTable() {
  const tbody = document.getElementById('marks-tbody');
  if (!allMarks.length) { tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No marks yet</td></tr>'; return; }
  tbody.innerHTML = allMarks.map(m => `
    <tr><td>${m.student_name}</td><td>${m.week}</td><td>${m.subject}</td><td>${m.marks}</td><td>${m.total}</td>
    <td>${fmtPct(m.pct)}</td>
    <td><button class="btn btn-danger btn-sm" onclick="deleteMark(${m.id})">Del</button></td></tr>`).join('');
}

async function deleteMark(id) {
  await api(`/api/marks/${id}`, 'DELETE');
  await loadAllData(); renderMarksTable();
}

function loadPerformance() {
  const name = document.getElementById('perf-student').value;
  const marks = allMarks.filter(m => m.student_name === name).sort((a,b) => a.week.localeCompare(b.week));
  const cont = document.getElementById('perf-content');
  if (!marks.length) { cont.innerHTML = '<div class="empty-state"><div class="icon">📈</div><p>No data yet</p></div>'; return; }
  const weekData = {};
  marks.forEach(m => (weekData[m.week] = weekData[m.week] || []).push(m));
  let html = `<div class="card"><div class="table-wrap"><table><thead><tr><th>Week</th><th>Avg %</th><th>vs Last Week</th><th>Trend</th></tr></thead><tbody>`;
  let prev = null;
  for (const wk of Object.keys(weekData).sort()) {
    const e = weekData[wk];
    const avg = Math.round(e.reduce((s,x) => s + x.pct, 0) / e.length * 10) / 10;
    let vp = '—', tr = '—';
    if (prev !== null) { const d = Math.round((avg - prev) * 10) / 10; vp = d >= 0 ? `+${d}%` : `${d}%`; tr = d > 0 ? '⬆ Improved' : d < 0 ? '⬇ Dropped' : '➡ Same'; }
    html += `<tr><td>${wk}</td><td><strong>${avg}%</strong></td><td>${vp}</td><td>${tr}</td></tr>`;
    prev = avg;
  }
  cont.innerHTML = html + '</tbody></table></div></div>';
}

// ==================== NOTES ====================
function handleNoteFile(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    noteFileData = { name: file.name, type: file.type, dataUrl: e.target.result };
    document.getElementById('file-label').textContent = `📎 ${file.name}`;
  };
  reader.readAsDataURL(file);
}

async function saveNote() {
  const student_name = document.getElementById('note-student').value.trim();
  const note = document.getElementById('note-text').value.trim();
  if (!student_name || !note) { toast('Fill student name and note', 'var(--red)'); return; }
  const payload = { student_name, note };
  if (noteFileData) { payload.file_name = noteFileData.name; payload.file_type = noteFileData.type; payload.file_data = noteFileData.dataUrl; }
  await api('/api/notes', 'POST', payload);
  toast('Note saved!', 'var(--green)');
  document.getElementById('note-student').value = '';
  document.getElementById('note-text').value = '';
  document.getElementById('file-label').textContent = 'Click to attach PDF or image';
  noteFileData = null;
  document.getElementById('note-file-input').value = '';
  await loadAllData(); renderNotes();
}

function renderNotes() {
  const filter = (document.getElementById('note-filter') || {value:''}).value.toLowerCase();
  const list = document.getElementById('notes-list');
  const notes = allNotes.filter(n => !filter || n.student_name.toLowerCase().includes(filter));
  if (!notes.length) { list.innerHTML = '<div class="empty-state"><div class="icon">📝</div><p>No notes yet</p></div>'; return; }
  list.innerHTML = notes.map(n => {
    const fileHtml = n.file_name ? `<div style="margin-top:8px;"><a href="/api/notes/${n.id}/file" style="color:var(--accent2);font-size:13px;">📎 ${n.file_name}</a></div>` : '';
    return `<div class="note-card ${n.file_name ? 'has-file' : ''}">
      <div class="note-student">${n.student_name}</div>
      <div class="note-text">${n.note}</div>${fileHtml}
      <div class="note-meta"><span>${(n.created_at||'').slice(0,10)}</span>
      <button class="btn btn-danger btn-sm" onclick="deleteNote(${n.id})">Delete</button></div></div>`;
  }).join('');
}

function populateNoteList() {
  const dl = document.getElementById('note-student-list');
  dl.innerHTML = allStudents.map(s => `<option value="${s.name}">`).join('');
}

async function deleteNote(id) {
  await api(`/api/notes/${id}`, 'DELETE');
  await loadAllData(); renderNotes();
  toast('Note deleted', 'var(--yellow)');
}

// ==================== ANNOUNCEMENTS ====================
async function postAnnouncement() {
  const title = document.getElementById('ann-title').value.trim();
  const message = document.getElementById('ann-msg').value.trim();
  const type = document.getElementById('ann-type').value;
  if (!title || !message) { toast('Fill all fields', 'var(--red)'); return; }
  await api('/api/announcements', 'POST', { title, message, type });
  toast(`📢 ${title} posted!`, 'var(--purple)');
  document.getElementById('ann-title').value = '';
  document.getElementById('ann-msg').value = '';
  await loadAllData(); renderAnnouncements();
}

function renderAnnouncements() {
  const list = document.getElementById('ann-list');
  if (!allAnnouncements.length) { list.innerHTML = '<div class="empty-state"><div class="icon">📢</div><p>No announcements yet</p></div>'; return; }
  list.innerHTML = allAnnouncements.map(a => `
    <div class="ann-card ${annClass(a.type)}">
      <div style="display:flex;justify-content:space-between;">
        <div><div class="ann-type">${a.type}</div><div class="ann-title">${a.title}</div>
        <div class="ann-msg">${a.message}</div><div class="ann-date">${a.date}</div></div>
        <button class="btn btn-danger btn-sm" style="align-self:flex-start;" onclick="deleteAnn(${a.id})">Delete</button>
      </div></div>`).join('');
}

async function deleteAnn(id) {
  await api(`/api/announcements/${id}`, 'DELETE');
  await loadAllData(); renderAnnouncements();
  toast('Announcement deleted', 'var(--yellow)');
}

// ==================== FEES ====================
async function setFeesDue() {
  const s = allStudents.find(st => st.name === document.getElementById('fees-student').value);
  const due = document.getElementById('fees-due').value;
  if (!s || !due) { toast('Fill all fields', 'var(--red)'); return; }
  await api(`/api/students/${s.id}/due_date`, 'PUT', { fees_due_date: due });
  toast(`Due date set for ${s.name}!`, 'var(--green)');
  await loadAllData(); renderFeesDue();
}

function renderFeesDue() {
  const tbody = document.getElementById('fees-tbody');
  const today = new Date(); today.setHours(0,0,0,0);
  const rows = allStudents.filter(s => s.fees_due_date).map(s => {
    const due = new Date(s.fees_due_date); due.setHours(0,0,0,0);
    const diff = Math.round((due - today) / 86400000);
    const badge = diff > 3 ? '<span class="badge-ok">✅ OK</span>' : diff > 0 ? '<span class="badge-warn">⚠️ Due Soon</span>' : diff === 0 ? '<span class="badge-danger">🔴 Due Today</span>' : '<span class="badge-danger">❗ Overdue</span>';
    return `<tr><td><strong>${s.name}</strong></td><td>${s.fees_due_date}</td><td style="font-family:var(--mono);">${diff}</td><td>${badge}</td></tr>`;
  });
  tbody.innerHTML = rows.length ? rows.join('') : '<tr><td colspan="4" class="empty-state">No fees records</td></tr>';
}

// ==================== SETTINGS ====================
async function changePassword() {
  const res = await api('/api/change_password', 'POST', {
    current_password: document.getElementById('cur-pwd').value.trim(),
    new_password: document.getElementById('new-pwd').value.trim(),
    confirm_password: document.getElementById('con-pwd').value.trim()
  });
  if (res.ok) { toast('Password changed!', 'var(--green)'); ['cur-pwd','new-pwd','con-pwd'].forEach(id => document.getElementById(id).value = ''); }
  else toast(res.error, 'var(--red)');
}

function saveApiKey() {
  const key = document.getElementById('api-key-input').value.trim();
  localStorage.setItem('et_api_key', key);
  toast(key ? 'API key saved! Chatbot will use Anthropic AI.' : 'API key cleared. Using rule-based mode.', 'var(--green)');
}

// ==================== ML ANALYSIS ====================
async function runGradePrediction() {
  const student_name = document.getElementById('ml-pred-student').value;
  const subject = document.getElementById('ml-pred-subject').value.trim();
  const div = document.getElementById('ml-grade-result');
  div.innerHTML = '<div style="color:var(--text2);margin-top:12px;">⏳ Running ML model...</div>';
  const res = await api('/api/ml/predict_grade', 'POST', { student_name, subject });
  if (!res.ok) { div.innerHTML = `<div class="ml-result"><div class="ml-label">Error</div><div style="color:var(--red);">${res.error}</div></div>`; return; }
  div.innerHTML = `
    <div class="ml-result">
      <div class="ml-label">Predicted Next Grade</div>
      <div class="ml-value" style="color:${res.predicted_pct>=60?'var(--green)':'var(--red)'};">${res.predicted_pct}%</div>
      <div class="ml-sub">Trend: ${res.trend} · Recent Avg: ${res.recent_avg}%</div>
      <div class="ml-sub" style="margin-top:6px;">Model: ${res.method} · Confidence: ${res.confidence}</div>
      <div class="ml-sub" style="margin-top:6px;">History: ${(res.history||[]).map(p => `${p}%`).join(' → ')}</div>
    </div>`;
}

async function runAttendanceRisk() {
  const student_name = document.getElementById('ml-risk-student').value;
  const div = document.getElementById('ml-risk-result');
  div.innerHTML = '<div style="color:var(--text2);margin-top:12px;">⏳ Analysing risk...</div>';
  const res = await api('/api/ml/attendance_risk', 'POST', { student_name });
  if (!res.ok) { div.innerHTML = `<div class="ml-result"><div style="color:var(--red);">${res.error}</div></div>`; return; }
  div.innerHTML = `
    <div class="ml-result">
      <div class="ml-label">Attendance Risk Level</div>
      <div style="margin:8px 0;"><span class="ml-badge ${res.risk_level.toLowerCase()}">${res.risk_level} Risk</span></div>
      <div class="ml-value">${res.risk_pct}</div>
      <div class="ml-sub">Attendance Rate: ${res.attendance_rate} · Consecutive Absences: ${res.consecutive_absences}</div>
      <div class="ml-sub" style="margin-top:8px;color:var(--text);">💡 ${res.recommendation}</div>
      <div class="ml-sub" style="margin-top:6px;">Model: ${res.method}</div>
    </div>`;
}

async function loadClassInsights() {
  const div = document.getElementById('ml-insights-result');
  div.innerHTML = '<div style="color:var(--text2);">⏳ Loading ML insights...</div>';
  const data = await api('/api/ml/class_insights');
  if (!Array.isArray(data) || !data.length) { div.innerHTML = '<div class="empty-state"><p>No data available yet. Add students and attendance first.</p></div>'; return; }
  let html = `<div class="table-wrap"><table><thead><tr><th>Student</th><th>Attendance %</th><th>Avg Marks</th><th>Risk Level</th><th>Recommendation</th></tr></thead><tbody>`;
  for (const s of data) {
    const risk = s.risk;
    const riskBadge = risk ? `<span class="ml-badge ${risk.risk_level.toLowerCase()}">${risk.risk_level}</span>` : '—';
    const rec = risk ? risk.recommendation : '—';
    html += `<tr><td><strong>${s.name}</strong></td>
      <td>${fmtPct(s.attendance_pct)}</td>
      <td>${s.avg_marks !== null ? fmtPct(s.avg_marks) : '—'}</td>
      <td>${riskBadge}</td>
      <td style="font-size:12px;color:var(--text2);">${rec}</td></tr>`;
  }
  div.innerHTML = html + '</tbody></table></div>';
}

async function trainModels() {
  toast('Training ML models...', 'var(--purple)');
  const res = await api('/api/ml/train', 'POST');
  if (res.ok) {
    const g = res.grade_model; const a = res.attendance_model;
    toast(`✅ Models trained! Grade MAE: ${g.mae ? g.mae.toFixed(2) : 'N/A'} · Att Accuracy: ${a.accuracy ? (a.accuracy*100).toFixed(1)+'%' : 'N/A'}`, 'var(--green)', 7000);
  } else toast('Training failed', 'var(--red)');
}

// ==================== STUDENT PORTAL ====================
function renderStudentDashboard() {
  const name = currentStudent;
  document.getElementById('s-welcome-title').innerHTML = `Welcome, <span>${name}</span>`;
  const rec = allAttendance.filter(r => r.student_name === name);
  const p = rec.filter(r => r.status === 'P').length;
  const t = rec.length;
  const mlist = allMarks.filter(m => m.student_name === name);
  const lastM = mlist[mlist.length - 1];
  document.getElementById('s-stats-grid').innerHTML = `
    <div class="stat-card green"><div class="stat-label">Present Days</div><div class="stat-value">${p}</div><div class="stat-sub">out of ${t}</div></div>
    <div class="stat-card accent"><div class="stat-label">Attendance %</div><div class="stat-value">${t ? Math.round(p/t*100)+'%' : '—'}</div></div>
    <div class="stat-card blue"><div class="stat-label">Last Test</div><div class="stat-value">${lastM ? lastM.pct+'%' : '—'}</div><div class="stat-sub">${lastM ? lastM.subject : ''}</div></div>`;
}

function renderStudentNotes() {
  const list = document.getElementById('s-notes-list');
  const notes = allNotes.filter(n => n.student_name.toLowerCase() === currentStudent.toLowerCase());
  if (!notes.length) { list.innerHTML = '<div class="empty-state"><div class="icon">📝</div><p>No notes for you yet</p></div>'; return; }
  list.innerHTML = notes.map(n => {
    const fileHtml = n.file_name ? `<div style="margin-top:8px;"><a href="/api/notes/${n.id}/file" style="color:var(--accent2);">📎 ${n.file_name}</a></div>` : '';
    return `<div class="note-card ${n.file_name?'has-file':''}"><div class="note-text">${n.note}</div>${fileHtml}<div class="note-meta"><span>${(n.created_at||'').slice(0,10)}</span></div></div>`;
  }).join('');
}

function renderStudentAtt() {
  const tbody = document.getElementById('s-att-tbody');
  const rec = allAttendance.filter(r => r.student_name === currentStudent).sort((a,b) => a.date.localeCompare(b.date));
  tbody.innerHTML = rec.length ? rec.map(r => `<tr><td>${r.date}</td><td>${r.status==='P'?'<span class="badge-p">Present</span>':'<span class="badge-a">Absent</span>'}</td></tr>`).join('') : '<tr><td colspan="2" class="empty-state">No records</td></tr>';
}

function renderStudentMarks() {
  const tbody = document.getElementById('s-marks-tbody');
  const marks = allMarks.filter(m => m.student_name === currentStudent).sort((a,b) => a.week.localeCompare(b.week));
  tbody.innerHTML = marks.length ? marks.map(m => `<tr><td>${m.week}</td><td>${m.subject}</td><td>${m.marks}</td><td>${m.total}</td><td>${fmtPct(m.pct)}</td></tr>`).join('') : '<tr><td colspan="5" class="empty-state">No marks yet</td></tr>';
}

function renderStudentPerf() {
  const cont = document.getElementById('s-perf-content');
  const marks = allMarks.filter(m => m.student_name === currentStudent);
  if (!marks.length) { cont.innerHTML = '<div class="empty-state"><div class="icon">📈</div><p>No performance data yet</p></div>'; return; }
  const weekData = {};
  marks.forEach(m => (weekData[m.week] = weekData[m.week] || []).push(m));
  let html = `<div class="card"><div class="table-wrap"><table><thead><tr><th>Week</th><th>Avg %</th><th>vs Last Week</th><th>Trend</th></tr></thead><tbody>`;
  let prev = null;
  for (const wk of Object.keys(weekData).sort()) {
    const e = weekData[wk];
    const avg = Math.round(e.reduce((s,x) => s + x.pct, 0) / e.length * 10) / 10;
    let vp = '—', tr = '—';
    if (prev !== null) { const d = Math.round((avg - prev)*10)/10; vp = d>=0?`+${d}%`:`${d}%`; tr = d>0?'⬆ Improved':d<0?'⬇ Dropped':'➡ Same'; }
    html += `<tr><td>${wk}</td><td><strong>${avg}%</strong></td><td>${vp}</td><td>${tr}</td></tr>`;
    prev = avg;
  }
  cont.innerHTML = html + '</tbody></table></div></div>';
}

function renderStudentAnns() {
  const list = document.getElementById('s-ann-list');
  list.innerHTML = allAnnouncements.length ? allAnnouncements.map(a => `
    <div class="ann-card ${annClass(a.type)}">
      <div class="ann-type">${a.type}</div><div class="ann-title">${a.title}</div>
      <div class="ann-msg">${a.message}</div><div class="ann-date">${a.date}</div>
    </div>`).join('') : '<div class="empty-state"><div class="icon">📢</div><p>No announcements</p></div>';
}

// ==================== CHATBOT ====================
let chatInited = false;

function initChat() {
  if (!chatInited) {
    chatInited = true;
    addBubble("Hi! I'm EduTrack AI 👋\nI can answer questions about students, attendance, marks, and fees.\n\n💡 Add your Anthropic API key in ⚙️ Settings for full AI responses.", 'ai');
  }
}

function addBubble(text, role, id = null) {
  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `chat-bubble ${role === 'user' ? 'user' : 'ai'}`;
  div.textContent = text;
  if (id) div.id = id;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function chatKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  addBubble(msg, 'user');
  chatHistory.push({ role: 'user', content: msg });

  const thinkId = 'thinking-' + Date.now();
  const thinkEl = addBubble('⏳ Thinking...', 'ai', thinkId);
  thinkEl.classList.add('thinking');

  const api_key = localStorage.getItem('et_api_key') || '';
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, history: chatHistory.slice(-10), api_key })
    });
    const data = await res.json();
    document.getElementById(thinkId)?.remove();
    const reply = data.reply || '⚠️ No response received.';
    addBubble(reply, 'ai');
    chatHistory.push({ role: 'assistant', content: reply });
  } catch (err) {
    document.getElementById(thinkId)?.remove();
    addBubble(`⚠️ Error: ${String(err).slice(0,120)}`, 'ai');
  }
}

// ==================== KEYBOARD ====================
document.getElementById('login-pass').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
document.getElementById('login-user').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
