from dataclasses import dataclass
from pathlib import Path
import json


DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class DiagnosisResult:
    emergency_level: str # "low" | "moderate" | "high"
    summary: str

def run_web_diagnosis(symptoms: str) -> DiagnosisResult:
    symptoms_l = symptoms.lower()
    level = "low"
    if any(k in symptoms_l for k in ["severe", "chest pain", "激しい", "意識"]):
        level = "high"
    elif any(k in symptoms_l for k in ["fever", "38", "めまい", "血"]):
        level = "moderate"


    result = DiagnosisResult(
        emergency_level=level,
        summary=f"症状の記述から推定レベル: {level}. 受診を推奨します。"
    )


    # 記録（例）
    out = DATA_DIR / "diagnosis" / "reports.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"symptoms": symptoms, **result.__dict__}, ensure_ascii=False) + "\n")


    return result