from dataclasses import dataclass
from pathlib import Path
import json

# データ保存先ディレクトリ
DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DiagnosisResult:
    emergency_level: str  # "low" | "moderate" | "high"
    summary: str


def run_web_diagnosis(symptoms: str) -> DiagnosisResult:
    """
    症状テキストから緊急度を推定する簡易ロジック。
    結果は DiagnosisResult として返すとともに、JSONL 形式で保存。

    Args:
        symptoms (str): ユーザーからの症状記述

    Returns:
        DiagnosisResult: 緊急度と要約文
    """
    symptoms_l = symptoms.lower()
    level = "low"

    # high（緊急度が高い）判定キーワード
    if any(
        k in symptoms_l for k in ["severe", "chest pain", "意識", "激しい", "呼吸困難"]
    ):
        level = "high"
    # moderate（中程度）
    elif any(k in symptoms_l for k in ["fever", "38", "血", "めまい", "出血", "痛み"]):
        level = "moderate"

    result = DiagnosisResult(
        emergency_level=level,
        summary=f"症状の記述から推定される緊急度は「{level}」です。必要に応じて医療機関を受診してください。",
    )

    # ログ記録（JSONL）
    log_path = DATA_DIR / "diagnosis" / "reports.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps({"symptoms": symptoms, **result.__dict__}, ensure_ascii=False)
            + "\n"
        )

    return result
