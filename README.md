# 💬 Chat App – FastAPI + Socket.IO + SQLite + HTML/JS

Um sistema de **chat em tempo real** com:

- ✅ Salas públicas (todos entram na sala **Geral**)  
- ✅ Conversas diretas (DM) criadas via e-mail  
- ✅ Lista de DMs salvas  
- ✅ Função para sair de salas (exceto Geral)  
- ✅ Contador de usuários ativos online  
- ✅ Envio de **mensagens, emojis e imagens**  
- ✅ Frontend estático (HTML + Bootstrap) sem React  

---

## 📸 Preview

- **Sidebar**: lista de salas e DMs salvas  
- **Mensagens em tempo real** com Socket.IO  
- **Upload de imagens** com pré-visualização  
- **Picker de emojis** embutido  

---

## ⚙️ Tecnologias

### Backend
- FastAPI  
- python-socketio  
- Uvicorn  
- passlib + bcrypt  
- python-jose  
- filetype  
- Banco **SQLite**

### Frontend
- Bootstrap 5 + Bootswatch Lux  
- JavaScript puro  
- Socket.IO client  

---

## 📂 Estrutura de pastas

```
chat-app/
├── server-py/          # Backend FastAPI
│   ├── app.py          # Entrypoint da API + Socket.IO
│   ├── db.py           # Banco SQLite + queries
│   ├── auth.py         # Hash de senha + JWT
│   ├── chat.db         # Banco SQLite (gerado automaticamente)
│   ├── uploads/        # Imagens enviadas
│   ├── .env            # Configurações (porta, CORS, segredo JWT)
│   └── requirements.txt
├── web/                # Frontend estático
│   ├── index.html      # Tela de login/cadastro
│   ├── chat.html       # Interface principal do chat
│   ├── auth.js         # Script de login/cadastro
│   ├── chat.js         # Script principal do chat
│   ├── api.js          # Conexão com a API
│   └── styles.css      # (opcional)
└── README.md
```

---

## 🚀 Como rodar

### 1. Clonar repositório
```bash
git clone <repo-url>
cd chat-app
```

---

### 2. Backend (Python)

> Requer **Python 3.11+** (testado no 3.13).

Crie e ative um ambiente virtual:
```bash
cd server-py
python -m venv .venv
.venv\Scripts\activate      # Windows PowerShell
source .venv/bin/activate   # Linux/Mac
```

Instale as dependências:
```bash
pip install -r requirements.txt
```

Crie o arquivo `.env` dentro de `server-py/`:
```env
PORT=3001
CORS_ORIGINS=http://10.9.1.53:8000,http://localhost:8000,http://127.0.0.1:8000
JWT_SECRET=troque-este-segredo
```

Inicie o servidor:
```bash
uvicorn app:socket_app --host 0.0.0.0 --port 3001 --reload
```

API disponível em:  
👉 http://10.9.1.53:3001  
Swagger: http://10.9.1.53:3001/docs

---

### 3. Frontend (HTML/JS)

Entre na pasta `web`:
```bash
cd web
python -m http.server 8000 --bind 0.0.0.0
```

Acesse no navegador:  
👉 http://10.9.1.53:8000

---

## 👤 Fluxo de uso

1. **Cadastro/Login** – criar usuário com nome, e-mail e senha.  
2. **Sala Geral** – todos já têm acesso automático.  
3. **Nova conversa**:
   - Informar **e-mail** → cria e salva uma **DM**.  
   - Informar **nome da sala** → cria uma nova **sala pública**.  
4. **Mensagens** – texto, emojis e upload de imagens.  
5. **Sair da sala** – botão no topo da conversa.  
6. **Remover DM** – botão “remover” ao lado do contato.  

---

## 🔧 Rede / Deploy

- Backend roda em `0.0.0.0:3001` (acessível em `10.9.1.53:3001`).  
- Frontend roda em `0.0.0.0:8000` (acessível em `10.9.1.53:8000`).  
- Libere as portas **3001** e **8000** no firewall.  
- Teste no celular/PC da mesma rede:  
  - API → http://10.9.1.53:3001/health  
  - Front → http://10.9.1.53:8000

---

## 📦 requirements.txt (backend)

```txt
fastapi
uvicorn
python-socketio[asgi]
python-jose
passlib[bcrypt]
python-dotenv
filetype
```

---

## 📌 Funcionalidades futuras

- ✅ Upload de imagens  
- 🔲 Upload de outros arquivos (PDF, DOC, etc.)  
- 🔲 Notificações push de novas mensagens  
- 🔲 Perfis com foto do usuário  

---

## 📝 Licença

Uso livre para **estudos, projetos acadêmicos e pessoais**.  
Contribuições são bem-vindas 🚀
