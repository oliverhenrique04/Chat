import { api, uploadImage, getToken, setToken, API_ROOT_URL } from './api.js';

const token = getToken();
if (!token) window.location.href = './auth.html';

const userNameEl = document.getElementById('userName');
const activeCountEl = document.getElementById('activeCount');
const logoutBtn = document.getElementById('logoutBtn');

const newRoomBtn = document.getElementById('newRoomBtn');
const createModalEl = document.getElementById('createModal');
const createForm = document.getElementById('createForm');
const createError = document.getElementById('createError');

const roomList = document.getElementById('roomList');
const userList = document.getElementById('userList');
const activeTitle = document.getElementById('activeTitle');
const leaveBtn = document.getElementById('leaveBtn');

const messageList = document.getElementById('messageList');
const msgInput = document.getElementById('msgInput');
const sendBtn = document.getElementById('sendBtn');
const emojiBtn = document.getElementById('emojiBtn');
const fileInput = document.getElementById('fileInput');
const imgPreview = document.getElementById('imgPreview');
const imgPreviewTag = document.getElementById('imgPreviewTag');
const clearImgBtn = document.getElementById('clearImgBtn');

let rooms = [];
let dms = []; // {id, name, email}
let active = null; // {type:'room'|'dm', id, name}
let socket = null;
let pendingFile = null;

// ===== Emoji picker simples (sem CDN) =====
(function setupEmoji() {
  const fallback = ['😀','😁','😂','🤣','😊','😍','😘','😎','🤔','👍','🙏','👏','🎉','🔥','💯','✅','❌','💡','📌','🧠','🕐','😉','😢','😮','😴','🤯','😇','😤','🤝','🙌','🥳','🤩','😅','😌','🤗','😏'];
  let pop = null;

  function insertAtCursor(txt) {
    const start = msgInput.selectionStart ?? msgInput.value.length;
    const end = msgInput.selectionEnd ?? msgInput.value.length;
    msgInput.value = msgInput.value.slice(0, start) + txt + msgInput.value.slice(end);
    msgInput.focus();
    msgInput.selectionStart = msgInput.selectionEnd = start + txt.length;
  }

  emojiBtn.addEventListener('click', () => {
    if (pop) { pop.remove(); pop = null; return; }
    pop = document.createElement('div');
    pop.className = 'card p-2 emoji-pop';
    pop.innerHTML = `<div style="display:grid;grid-template-columns:repeat(8,1fr);gap:6px;font-size:20px;"></div>`;
    const grid = pop.firstChild;
    fallback.forEach(e => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'btn btn-light p-0';
      b.style.lineHeight = '1.2'; b.textContent = e;
      b.onclick = () => { insertAtCursor(e); pop.remove(); pop = null; };
      grid.appendChild(b);
    });
    emojiBtn.parentElement.style.position = 'relative';
    emojiBtn.parentElement.appendChild(pop);
  });
})();

// ===== Sidebar =====
function renderRooms() {
  roomList.innerHTML = '';
  rooms.forEach(r => {
    const li = document.createElement('li');
    li.className = 'list-group-item list-group-item-action';
    if (active?.type === 'room' && active?.id === r.id) li.classList.add('active');
    li.textContent = `# ${r.name}`;
    li.style.cursor = 'pointer';
    li.onclick = () => selectRoom(r);
    roomList.appendChild(li);
  });
}

function renderDMs() {
  userList.innerHTML = '';
  dms.forEach(u => {
    const li = document.createElement('li');
    li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
    if (active?.type === 'dm' && active?.id === u.id) li.classList.add('active');
    const span = document.createElement('span');
    span.textContent = u.name;
    span.style.cursor = 'pointer';
    span.onclick = () => selectDM(u);
    li.appendChild(span);

    const del = document.createElement('button');
    del.className = 'btn btn-sm btn-outline-danger';
    del.textContent = 'remover';
    del.onclick = async (ev) => {
      ev.stopPropagation();
      try {
        await api.dmRemove(u.id);
        dms = dms.filter(x => x.id !== u.id);
        renderDMs();
        if (active?.type === 'dm' && active?.id === u.id) {
          active = null; setActiveTitle(); messageList.innerHTML = '';
        }
      } catch (e) { alert(e?.message || 'Falha ao remover DM'); }
    };
    li.appendChild(del);

    userList.appendChild(li);
  });
}

function setActiveTitle() {
  activeTitle.textContent = active ? (active.type === 'room' ? `# ${active.name}` : active.name) : 'Selecione uma conversa';
  if (active?.type === 'room') leaveBtn.classList.remove('d-none');
  else leaveBtn.classList.add('d-none');
}

function renderMessages(msgs) {
  messageList.innerHTML = '';
  msgs.forEach(m => appendMessage(m));
  messageList.scrollTop = messageList.scrollHeight;
}

function appendMessage(m) {
  const wrap = document.createElement('div');
  wrap.className = 'mb-3';
  const meta = document.createElement('div');
  meta.className = 'small text-muted';
  const timeStr = m.created_at ? new Date(m.created_at).toLocaleTimeString() : '';
  meta.innerHTML = `${m.sender_name} · <span title="${m.created_at || ''}">${timeStr}</span>`;
  wrap.appendChild(meta);

  if (m.content) {
    const bubble = document.createElement('div');
    bubble.className = 'px-3 py-2 bg-white border rounded-3';
    bubble.textContent = m.content;
    wrap.appendChild(bubble);
  }
  if (m.attachment_type === 'image' && m.attachment_url) {
    const img = document.createElement('img');
    // usa a raiz da API no seu IP (10.9.1.53)
    img.src = `${API_ROOT_URL}${m.attachment_url}`;
    img.alt = 'imagem';
    img.className = 'img-thumb mt-2';
    img.style.maxWidth = '280px';
    img.style.maxHeight = '220px';
    img.loading = 'lazy';
    wrap.appendChild(img);
  }
  messageList.appendChild(wrap);
  messageList.scrollTop = messageList.scrollHeight;
}

// ===== Ações =====
async function selectRoom(r) {
  active = { type: 'room', id: r.id, name: r.name };
  setActiveTitle();
  const msgs = await api.roomMessages(r.id);
  renderMessages(msgs);
}

async function selectDM(u) {
  active = { type: 'dm', id: u.id, name: u.name };
  setActiveTitle();
  const msgs = await api.dmMessages(u.id);
  renderMessages(msgs);
}

async function loadSidebar() {
  rooms = await api.rooms();
  dms = await api.dmList();
  renderRooms();
  renderDMs();
}

// ===== Socket =====
function connectSocket() {
  if (typeof io === 'undefined') {
    console.error('Socket.IO client não carregado.');
    return null;
  }

  // conecta direto no seu IP
  const s = io(API_ROOT_URL, {
    auth: { token },
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 500,
  });

  s.on('connect', () => console.log('socket connected', s.id));
  s.on('connect_error', (err) => console.error('connect_error:', err?.message || err));
  s.on('error', (err) => console.error('socket error:', err));

  s.on('presence:update', ({ active }) => { activeCountEl.textContent = String(active ?? 0); });

  s.on('message:new', (msg) => {
    if (active?.type === 'room' && msg.type === 'room' && msg.room_id === active.id) appendMessage(msg);
    if (active?.type === 'dm' && msg.type === 'dm') {
      const pair = (msg.sender_id === active.id || msg.recipient_id === active.id);
      if (pair) appendMessage(msg);
    }
  });

  s.on('room:left', ({ roomId }) => {
    if (active?.type === 'room' && active.id === roomId) {
      active = null; setActiveTitle(); messageList.innerHTML = '';
    }
    api.rooms().then(rs => { rooms = rs; renderRooms(); });
  });

  return s;
}
socket = connectSocket();

// ===== Envio de mensagem (texto + imagem) =====
fileInput.addEventListener('change', () => {
  const f = fileInput.files?.[0];
  if (!f) { pendingFile = null; imgPreview.classList.add('d-none'); return; }
  pendingFile = f;
  const url = URL.createObjectURL(f);
  imgPreviewTag.src = url;
  imgPreview.classList.remove('d-none');
});

clearImgBtn.addEventListener('click', () => {
  pendingFile = null; fileInput.value = '';
  imgPreview.classList.add('d-none'); imgPreviewTag.src = '';
});

sendBtn.onclick = async () => {
  if (!active) return;
  if (!socket || !socket.connected) {
    alert('Sem conexão com o servidor.');
    return;
  }
  let content = msgInput.value.trim();
  let attachmentUrl = null;
  let attachmentType = null;

  if (pendingFile) {
    try {
      const up = await uploadImage(pendingFile);
      attachmentUrl = up.url;
      attachmentType = up.type;
    } catch (e) {
      alert('Falha no upload da imagem: ' + (e?.message || e));
      return;
    }
  }
  if (!content && !attachmentUrl) return;

  if (active.type === 'room') {
    socket.emit('message:send', { type: 'room', roomId: active.id, content, attachmentUrl, attachmentType }, () => {});
  } else {
    socket.emit('message:send', { type: 'dm', toUserId: active.id, content, attachmentUrl, attachmentType }, () => {});
  }

  msgInput.value = '';
  if (pendingFile) { pendingFile = null; fileInput.value=''; imgPreview.classList.add('d-none'); imgPreviewTag.src=''; }
  msgInput.focus();
};

msgInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendBtn.click(); });

// ===== Modal criação (DM salva OU sala pública) =====
const bsModal = new bootstrap.Modal(createModalEl);
newRoomBtn.onclick = () => { createError.classList.add('d-none'); createForm.reset(); bsModal.show(); };

createForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  createError.classList.add('d-none');
  const data = new FormData(createForm);
  const email = (data.get('email') || '').trim();
  const roomName = (data.get('roomName') || '').trim();

  try {
    if (email) {
      const u = await api.dmAdd(email); // salva e retorna o contato
      dms = await api.dmList();
      renderDMs();
      await selectDM(u);
      bsModal.hide();
      return;
    }
    if (!roomName) throw new Error('Informe o e-mail (para DM) ou o nome da sala.');
    const room = await api.createRoom(roomName);
    rooms.push(room); renderRooms();
    await selectRoom(room);
    bsModal.hide();
  } catch (err) {
    createError.textContent = err?.message || 'Falha ao criar conversa.';
    createError.classList.remove('d-none');
  }
});

// ===== Sair da sala =====
leaveBtn.onclick = async () => {
  if (!(active && active.type === 'room')) return;
  const roomId = active.id;
  try {
    await api.leaveRoom(roomId);
    if (socket && socket.connected) socket.emit('room:leave', { roomId });
    rooms = await api.rooms();
    renderRooms();
    active = null; setActiveTitle(); messageList.innerHTML = '';
  } catch (e) {
    alert(e?.message || 'Não foi possível sair da sala.');
  }
};

// logout
logoutBtn.onclick = () => { setToken(null); window.location.href = './auth.html'; };

// boot
(async function init() {
  try {
    const me = await api.me();
    userNameEl.textContent = `Olá, ${me.name}`;
  } catch {
    setToken(null); window.location.href = './auth.html'; return;
  }
  try {
    const { active } = await api.activeCount();
    activeCountEl.textContent = String(active ?? 0);
  } catch {}
  await loadSidebar();
})();
