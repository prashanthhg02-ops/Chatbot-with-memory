const userKey = 'memo-user-id';
let userId = localStorage.getItem(userKey);
const messages = document.querySelector('#messages');
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message-input');

function addMessage(role, content) {
  const item = document.createElement('article');
  item.className = `message ${role}`;
  const label = role === 'user' ? 'You' : 'Memo';
  item.innerHTML = `<time>${label}</time><p></p>`;
  item.querySelector('p').textContent = content;
  messages.appendChild(item);
  messages.scrollTop = messages.scrollHeight;
}

function updateProfile(profile) {
  document.querySelector('#saved-name').textContent = profile.name || 'Not saved yet';
  document.querySelector('#saved-favorite').textContent = profile.favorite || 'Not saved yet';
}

async function loadHistory() {
  if (!userId) { addMessage('bot', 'Hello! I am Memo. Tell me your name or a favorite thing, and I will remember it.'); return; }
  const result = await fetch(`/api/history/${userId}`);
  const data = await result.json();
  data.messages.forEach(message => addMessage(message.role, message.content));
  updateProfile(data.profile);
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  addMessage('user', message);
  input.value = '';
  input.disabled = true;
  try {
    const result = await fetch('/api/chat', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message, user_id: userId}) });
    const data = await result.json();
    if (!result.ok) throw new Error(data.error || 'Something went wrong');
    userId = data.user_id;
    localStorage.setItem(userKey, userId);
    addMessage('bot', data.response);
    updateProfile(data.profile);
  } catch (error) {
    addMessage('bot', error.message);
  } finally { input.disabled = false; input.focus(); }
});

document.querySelector('#reset-button').addEventListener('click', async () => {
  if (!userId) return;
  await fetch(`/api/reset/${userId}`, {method: 'POST'});
  localStorage.removeItem(userKey);
  messages.replaceChildren();
  updateProfile({});
  addMessage('bot', 'Memory cleared. We can start fresh.');
});

loadHistory();
