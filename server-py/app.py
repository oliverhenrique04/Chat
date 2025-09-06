import os
from typing import Optional
from pathlib import Path
from sqlite3 import IntegrityError

from fastapi import FastAPI, Depends, HTTPException, Header, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
import socketio
import filetype
import uuid

from auth import hash_password, verify_password, sign_token, verify_token
import db

# =========================
# Config
# =========================
load_dotenv()

PORT = int(os.getenv("PORT", "3001"))
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:8000,http://127.0.0.1:8000"
).split(",")

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

db.init_db()

# =========================
# FastAPI
# =========================
app = FastAPI(title="Chat API (Python)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR), html=False), name="uploads")

# =========================
# Socket.IO
# =========================
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[o.strip() for o in CORS_ORIGINS],
    logger=False,
    engineio_logger=False
)
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

ONLINE: dict[int, int] = {}
SID_INDEX: dict[str, int] = {}  # sid -> user_id

def online_count() -> int:
    return sum(1 for v in ONLINE.values() if v > 0)

async def presence_broadcast():
    await sio.emit("presence:update", {"active": online_count()})

# =========================
# Schemas
# =========================
class RegisterIn(BaseModel):
    name: str
    email: str
    password: str

class LoginIn(BaseModel):
    email: str
    password: str

class CreateRoomIn(BaseModel):
    name: str

# =========================
# Auth dep
# =========================
def get_user_from_auth(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sem token")
    token = authorization[7:]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    return payload

# =========================
# Helpers
# =========================
def _ensure_join_global(user_id: int):
    room = db.get_room_by_name("Geral")
    if room:
        db.join_room(user_id, room["id"])

# =========================
# Routes
# =========================
@app.get("/")
def root():
    return {"service": "chat-api", "docs": "/docs"}

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/active-count")
def active_count():
    return {"active": online_count()}

@app.get("/api/users/find")
def find_user_by_email(email: str = Query(..., description="Email do usuário a localizar")):
    u = db.find_user_by_email((email or "").strip().lower())
    if not u:
        raise HTTPException(404, detail="Usuário não encontrado")
    return {"id": u["id"], "name": u["name"], "email": u["email"]}

# Upload de imagens (mensagens)
@app.post("/api/upload")
def upload_image(file: UploadFile = File(...), user=Depends(get_user_from_auth)):
    orig_name = file.filename or "upload"
    orig_ext = os.path.splitext(orig_name)[1].lower()
    if orig_ext not in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
        raise HTTPException(400, detail="Apenas imagens (png, jpg, jpeg, gif, webp)")

    tmp_name = f"{uuid.uuid4().hex}{orig_ext or ''}"
    dest = UPLOAD_DIR / tmp_name
    with open(dest, "wb") as f:
        f.write(file.file.read())

    kind = filetype.guess(str(dest))
    if not kind or not kind.mime.startswith("image/"):
        dest.unlink(missing_ok=True)
        raise HTTPException(400, detail="Arquivo não reconhecido como imagem")

    final_ext = f".{kind.extension}" if kind.extension else orig_ext
    final_name = f"{uuid.uuid4().hex}{final_ext}"
    final_path = UPLOAD_DIR / final_name
    dest.rename(final_path)

    return {"url": f"/uploads/{final_name}", "type": "image", "mime": kind.mime}

# Auth / dados
@app.post("/api/register")
def register(data: RegisterIn):
    name = (data.name or "").strip()
    email = (data.email or "").strip().lower()
    password = (data.password or "").strip()
    if not (name and email and password):
        raise HTTPException(400, detail="Dados obrigatórios")
    if len(password) < 4:
        raise HTTPException(400, detail="Senha muito curta")
    if db.find_user_by_email(email):
        raise HTTPException(409, detail="Email já cadastrado")

    try:
        uid = db.insert_user(name, email, hash_password(password))
        _ensure_join_global(uid)
    except IntegrityError:
        raise HTTPException(409, detail="Email já cadastrado")
    except Exception:
        raise HTTPException(500, detail="Erro inesperado no cadastro")

    user = {"id": uid, "name": name, "email": email}
    token = sign_token(user)
    return {"user": user, "token": token}

@app.post("/api/login")
def login(data: LoginIn):
    email = (data.email or "").strip().lower()
    password = (data.password or "").strip()
    u = db.find_user_by_email(email)
    if not u or not verify_password(password, u["password_hash"]):
        raise HTTPException(401, detail="Credenciais inválidas")

    _ensure_join_global(u["id"])
    user = {"id": u["id"], "name": u["name"], "email": u["email"]}
    token = sign_token(user)
    return {"user": user, "token": token}

@app.get("/api/me")
def me(user=Depends(get_user_from_auth)):
    return db.find_user_by_id(user["id"])

# Salas
@app.get("/api/rooms")
def my_rooms(user=Depends(get_user_from_auth)):
    return db.list_my_rooms(user["id"])

@app.post("/api/rooms")
def create_room(body: CreateRoomIn, user=Depends(get_user_from_auth)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, detail="Nome obrigatório")
    try:
        rid = db.create_room(name)
        db.join_room(user["id"], rid)
        return {"id": rid, "name": name}
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(409, detail="Sala já existe")
        raise HTTPException(500, detail="Erro ao criar sala")

@app.post("/api/rooms/{room_id}/join")
def join_room(room_id: int, user=Depends(get_user_from_auth)):
    if not db.room_exists(room_id):
        raise HTTPException(404, detail="Sala não encontrada")
    db.join_room(user["id"], room_id)
    return {"ok": True}

@app.post("/api/rooms/{room_id}/leave")
def leave_room(room_id: int, user=Depends(get_user_from_auth)):
    if not db.room_exists(room_id):
        raise HTTPException(404, detail="Sala não encontrada")
    db.leave_room(user["id"], room_id)
    return {"ok": True}

@app.get("/api/messages/room/{room_id}")
def room_messages(room_id: int, user=Depends(get_user_from_auth)):
    if not db.is_member(user["id"], room_id):
        raise HTTPException(403, detail="Não é membro da sala")
    return db.room_history(room_id)

@app.get("/api/messages/dm/{other_id}")
def dm_messages(other_id: int, user=Depends(get_user_from_auth)):
    return db.dm_history(user["id"], other_id)

# DMs salvas
@app.get("/api/dm/list")
def dm_list(user=Depends(get_user_from_auth)):
    return db.list_dm_contacts(user["id"])

@app.post("/api/dm/add")
def dm_add(email: str = Query(...), user=Depends(get_user_from_auth)):
    other = db.find_user_by_email((email or "").strip().lower())
    if not other:
        raise HTTPException(404, detail="Usuário não encontrado")
    if other["id"] == user["id"]:
        raise HTTPException(400, detail="Não é possível criar DM consigo mesmo")
    db.add_dm_contact(user["id"], other["id"])
    return {"id": other["id"], "name": other["name"], "email": other["email"]}

@app.post("/api/dm/remove/{other_id}")
def dm_remove(other_id: int, user=Depends(get_user_from_auth)):
    db.remove_dm_contact(user["id"], other_id)
    return {"ok": True}

# =========================
# Socket.IO events
# =========================
@sio.event
async def connect(sid, environ, auth):
    token = (auth or {}).get("token")
    payload = verify_token(token) if token else None
    if not payload:
        return False

    await sio.save_session(sid, payload)
    uid = payload["id"]
    SID_INDEX[sid] = uid

    ONLINE[uid] = ONLINE.get(uid, 0) + 1
    await presence_broadcast()

    await sio.enter_room(sid, f"user:{uid}")
    for r in db.list_my_rooms(uid):
        await sio.enter_room(sid, f"room:{r['id']}")

@sio.event
async def disconnect(sid):
    sess = await sio.get_session(sid)
    uid = SID_INDEX.pop(sid, None)
    if sess and uid is not None:
        ONLINE[uid] = max(0, ONLINE.get(uid, 0) - 1)
        if ONLINE[uid] == 0:
            ONLINE.pop(uid, None)
        await presence_broadcast()

@sio.on("message:send")
async def message_send(sid, payload):
    sess = await sio.get_session(sid)
    user_id = sess["id"]
    user_name = sess["name"]

    content = (payload or {}).get("content", "").strip()
    attachment_url = (payload or {}).get("attachmentUrl", None)
    attachment_type = (payload or {}).get("attachmentType", None)

    if not content and not attachment_url:
        return {"ok": False, "error": "Mensagem vazia"}

    if payload.get("type") == "room":
        room_id = int(payload.get("roomId", 0))
        if not db.is_member(user_id, room_id):
            return {"ok": False, "error": "Sem acesso à sala"}
        mid = db.insert_room_message(room_id, user_id, content or "", attachment_url, attachment_type)
        msg = next((m for m in db.room_history(room_id) if m["id"] == mid), None) or {
            "id": mid, "type": "room", "room_id": room_id,
            "sender_id": user_id, "recipient_id": None,
            "content": content or "", "created_at": "", "sender_name": user_name,
            "attachment_url": attachment_url, "attachment_type": attachment_type
        }
        await sio.emit("message:new", msg, room=f"room:{room_id}")
        return {"ok": True, "msg": msg}

    if payload.get("type") == "dm":
        to_user = int(payload.get("toUserId", 0))
        if not db.find_user_by_id(to_user):
            return {"ok": False, "error": "Usuário destino inexistente"}
        mid = db.insert_dm(user_id, to_user, content or "", attachment_url, attachment_type)
        history = db.dm_history(user_id, to_user)
        msg = next((m for m in history if m["id"] == mid), None) or {
            "id": mid, "type": "dm", "room_id": None,
            "sender_id": user_id, "recipient_id": to_user,
            "content": content or "", "created_at": "", "sender_name": user_name,
            "attachment_url": attachment_url, "attachment_type": attachment_type
        }
        await sio.emit("message:new", msg, room=f"user:{user_id}")
        await sio.emit("message:new", msg, room=f"user:{to_user}")
        return {"ok": True, "msg": msg}

    return {"ok": False, "error": "Tipo inválido"}

@sio.on("room:leave")
async def room_leave(sid, payload):
    """Cliente solicita sair de uma sala: remove do DB e tira este SID da sala Socket.IO."""
    sess = await sio.get_session(sid)
    user_id = sess["id"]
    room_id = int((payload or {}).get("roomId", 0))
    if not db.room_exists(room_id):
        return {"ok": False, "error": "Sala não encontrada"}
    db.leave_room(user_id, room_id)
    await sio.leave_room(sid, f"room:{room_id}")
    # opcional: avisar cliente que saiu
    await sio.emit("room:left", {"roomId": room_id}, to=sid)
    return {"ok": True}

# =========================
# Run
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:socket_app", host="0.0.0.0", port=PORT, reload=True)
