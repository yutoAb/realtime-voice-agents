import os
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from agent import run_web_diagnosis

# 環境変数
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REALTIME_MODEL = os.environ.get("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")
VOICE = os.environ.get("OPENAI_REALTIME_VOICE", "verse")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://app:app@db:5432/app"
)

# DBエンジン作成
engine: AsyncEngine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

# FastAPI アプリ初期化
app = FastAPI()

# CORS設定
origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------
# 1. エフェメラルトークン発行
# --------------------------
class TokenRequest(BaseModel):
    user_id: Optional[str] = None


@app.post("/realtime/token")
async def create_ephemeral_token(_: TokenRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

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
    return {"client_secret": data.get("client_secret", {})}


# --------------------------
# 2. 病院一覧取得
# --------------------------
class HospitalOut(BaseModel):
    id: str
    name: str
    distance_km: float
    slots: List[str]


@app.get("/hospitals")
async def list_hospitals_api(lat: float, lon: float, distance_km: float = 5):
    async with engine.begin() as conn:
        hospitals = (
            (
                await conn.execute(
                    text("SELECT id, name, lat, lon FROM hospitals ORDER BY id")
                )
            )
            .mappings()
            .all()
        )

        out: List[HospitalOut] = []
        for h in hospitals:
            rows = (
                await conn.execute(
                    text(
                        """
                SELECT to_char(start_time, 'YYYY-MM-DD\"T\"HH24:MI:SSOF') AS iso
                FROM slots
                WHERE hospital_id = :hid AND reserved = false
                ORDER BY start_time LIMIT 10
            """
                    ),
                    {"hid": h["id"]},
                )
            ).all()

            slots = [r[0] for r in rows]
            out.append(
                HospitalOut(
                    id=h["id"],
                    name=h["name"],
                    distance_km=1.0,  # デモ用に固定
                    slots=slots,
                )
            )

        return {"hospitals": [h.model_dump() for h in out]}


# --------------------------
# 3. 予約作成
# --------------------------
class VisitRequest(BaseModel):
    hospital_id: str
    slot: str  # ISO8601文字列
    name: Optional[str] = None


@app.post("/visit")
async def create_visit_api(req: VisitRequest):
    async with engine.begin() as conn:
        # スロット存在確認＋ロック
        slot_row = (
            await conn.execute(
                text(
                    """
            SELECT id FROM slots
            WHERE hospital_id = :hid AND start_time = ($1)::timestamptz
            FOR UPDATE
        """
                ),
                {"hid": req.hospital_id, "$1": req.slot},
            )
        ).first()

        if not slot_row:
            raise HTTPException(status_code=404, detail="Slot not found")

        reserved = (
            await conn.execute(
                text(
                    """
            SELECT reserved FROM slots WHERE id = :sid
        """
                ),
                {"sid": slot_row[0]},
            )
        ).scalar_one()

        if reserved:
            raise HTTPException(status_code=409, detail="Slot already reserved")

        # visits に挿入
        visit = (
            await conn.execute(
                text(
                    """
            INSERT INTO visits(hospital_id, slot_id, name)
            VALUES (:hid, :sid, :name)
            RETURNING id
        """
                ),
                {
                    "hid": req.hospital_id,
                    "sid": slot_row[0],
                    "name": req.name or "匿名",
                },
            )
        ).first()

        # slots を更新
        await conn.execute(
            text(
                """
            UPDATE slots
            SET reserved = true, reserved_at = now(), visit_id = :vid
            WHERE id = :sid
        """
            ),
            {"vid": visit[0], "sid": slot_row[0]},
        )

    return {"status": "ok", "visit_id": visit[0]}


# --------------------------
# 4. 緊急度診断
# --------------------------
class DiagnoseRequest(BaseModel):
    symptoms: str


@app.post("/diagnose")
async def diagnose_api(req: DiagnoseRequest):
    result = run_web_diagnosis(req.symptoms)
    return {"emergency_level": result.emergency_level, "medical_report": result.summary}
