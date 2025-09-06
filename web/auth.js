import { api, setToken } from './api.js';

const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const loginError = document.getElementById('loginError');
const registerError = document.getElementById('registerError');

function show(errBox, err) {
  const msg = (err && err.message) ? err.message : 'Erro inesperado';
  errBox.textContent = msg.replace(/^"|"$/g, '');
  errBox.classList.remove('d-none');
}

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  loginError.classList.add('d-none');
  const f = new FormData(loginForm);
  try {
    const { token } = await api.login(f.get('email'), f.get('password'));
    setToken(token);
    window.location.href = './chat.html';
  } catch (err) {
    show(loginError, err);
  }
});

registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  registerError.classList.add('d-none');
  const f = new FormData(registerForm);
  try {
    const { token } = await api.register(f.get('name'), f.get('email'), f.get('password'));
    setToken(token);
    window.location.href = './chat.html';
  } catch (err) {
    show(registerError, err);
  }
});
