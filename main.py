"""
Maciej's OnePass — v0 (email only)
Najprostsze możliwe: podajesz email → system sprawdza czy to Maciej → token.
Zabezpieczenia dodamy potem warstwami.
"""
import os, uuid
import httpx
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI(title="OnePass v0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SUPABASE_URL   = os.getenv("SUPABASE_URL", "https://blgdhfcosqjzrutncbbr.supabase.co")
SUPABASE_KEY   = os.getenv("SUPABASE_SERVICE_KEY", "")
OWNER_EMAIL    = os.getenv("OWNER_EMAIL", "maciej@ofshore.dev")  # jedyny dozwolony email
GUARDIAN_TOKEN = "8394457153:AAFZQ4eMHaiAnmwejmTfWZHI_5KSqhXgCXg"
GUARDIAN_CHAT  = "8149345223"

SB = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
security = HTTPBearer(auto_error=False)

# In-memory tokens (wystarczy na v0)
active_tokens: dict[str, str] = {}  # token → email

class LoginRequest(BaseModel):
    email: str

async def require_owner(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds or creds.credentials not in active_tokens:
        raise HTTPException(401, "Nie jesteś właścicielem")
    return creds.credentials

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0", "auth": "email_only"}

@app.post("/login")
async def login(req: LoginRequest, request: Request):
    # Jedyna weryfikacja: czy to właściciel
    if req.email.lower().strip() != OWNER_EMAIL.lower():
        async with httpx.AsyncClient() as c:
            await c.get(f"https://api.telegram.org/bot{GUARDIAN_TOKEN}/sendMessage",
                params={"chat_id": GUARDIAN_CHAT,
                        "text": f"⚠️ OnePass: próba logowania z {req.email} ({request.client.host})"})
        raise HTTPException(403, "Brak dostępu")

    token = str(uuid.uuid4())
    active_tokens[token] = req.email

    async with httpx.AsyncClient() as c:
        await c.get(f"https://api.telegram.org/bot{GUARDIAN_TOKEN}/sendMessage",
            params={"chat_id": GUARDIAN_CHAT,
                    "text": f"🔑 OnePass: zalogowano {req.email} z {request.client.host}"})

    return {
        "token": token,
        "email": req.email,
        "access": "full",
        "resources": [
            "https://genspark.ofshore.dev",
            "https://sandbox.ofshore.dev",
            "https://clone.ofshore.dev"
        ]
    }

@app.get("/verify")
async def verify(token: str = Depends(require_owner)):
    return {"valid": True, "email": active_tokens.get(token)}

@app.post("/logout")
async def logout(token: str = Depends(require_owner)):
    active_tokens.pop(token, None)
    return {"status": "ok"}

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
