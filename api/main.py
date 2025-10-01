import os
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional


import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from agent import run_web_diagnosis

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REALTIME_MODEL = os.environ.get("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")
VOICE = os.environ.get("OPENAI_REALTIME_VOICE", "verse")

app = FastAPI()

origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==== 1) エフェメラル・セッション（client_secret）発行 ====
class TokenRequest(BaseModel):
    user_id: Optional[str] = None


@app.post("/realtime/token")
async def create_ephemeral_token(_: TokenRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

    # Sessions API: 短命キー発行（デフォルト TTL ~1分想定）
    payload = {
        "model": REALTIME_MODEL,
        "voice": VOICE,
        "modalities": ["text", "audio"],
        "instructions": (
            "あなたは医療予約エージェントです。必要に応じて `list_hospitals`, "
            "`create_visit`, `diagnose` を呼び出して、候補提示と予約確定、"
            "および緊急度の判断を行います。"
        ),
        "tools": [
            {
                "type": "function",
                "name": "list_hospitals",
                "description": "近隣の病院候補と空きスロットを取得",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "number"},
                        "lon": {"type": "number"},
                        "distance_km": {"type": "number", "default": 5},
                    },
                    "required": ["lat", "lon"],
                },
            },
            {
                "type": "function",
                "name": "create_visit",
                "description": "病院IDと日時で予約を作成",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hospital_id": {"type": "string"},
                        "slot": {"type": "string", "description": "ISO8601 日時"},
                        "name": {"type": "string"},
                    },
                    "required": ["hospital_id", "slot"],
                },
            },
            {
                "type": "function",
                "name": "diagnose",
                "description": "症状テキストから緊急度を推定",
                "parameters": {
                    "type": "object",
                    "properties": {"symptoms": {"type": "string"}},
                    "required": ["symptoms"],
                },
            },
        ],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {r.text}")

    data = r.json()
    # ブラウザに返すのは client_secret の value
    return {"client_secret": data.get("client_secret", {})}


# ==== 2) 業務API（ダミー実装） ====
class Hospital(BaseModel):
    id: str
    name: str
    distance_km: float
    slots: List[str]


@app.get("/hospitals")
async def list_hospitals_api(lat: float, lon: float, distance_km: float = 5):
    # デモ用ダミーデータ
    base = datetime.now().replace(minute=0, second=0, microsecond=0)
    slots = [
        (base).isoformat(),
        (base.replace(hour=(base.hour + 1) % 24)).isoformat(),
        (base.replace(hour=(base.hour + 2) % 24)).isoformat(),
    ]
    return {
        "hospitals": [
            Hospital(
                id="h_001", name="Waseda Clinic", distance_km=1.2, slots=slots
            ).model_dump(),
            Hospital(
                id="h_002", name="Takadanobaba Hospital", distance_km=2.8, slots=slots
            ).model_dump(),
        ]
    }


class VisitRequest(BaseModel):
    hospital_id: str
    slot: str
    name: Optional[str] = None


@app.post("/visit")
async def create_visit_api(req: VisitRequest):
    path = Path("/data/visits")
    path.mkdir(parents=True, exist_ok=True)
    filename = path / f"visit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filename.write_text(req.model_dump_json(), encoding="utf-8")
    return {"status": "ok", "file": str(filename)}


class DiagnoseRequest(BaseModel):
    symptoms: str


@app.post("/diagnose")
async def diagnose_api(req: DiagnoseRequest):
    res = run_web_diagnosis(req.symptoms)
    return {"emergency_level": res.emergency_level, "medical_report": res.summary}
