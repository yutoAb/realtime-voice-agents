# Realtime Voice Agent - 医療予約システム

OpenAI Realtime APIを活用したリアルタイム音声対話型の医療予約エージェントです。PostgreSQLデータベースを使用して病院情報と予約を管理し、音声による自然な対話で医療機関の検索、予約作成、症状診断を行うことができます。

## 🎯 主な機能

- **リアルタイム音声対話**: OpenAI Realtime APIによる自然な音声会話インターフェース
- **病院検索**: 位置情報を基にした近隣医療機関の検索と空き枠確認
- **予約管理**: 音声コマンドによる医療機関予約の作成と管理
- **症状診断**: AI による症状の緊急度判定とアドバイス提供
- **データベース連携**: PostgreSQLによる堅牢な病院・予約データ管理
- **関数呼び出し**: 音声認識から直接システム機能を実行

## 🏗️ システム構成

```
realtime-voice-agent/
├── api/                         # FastAPIバックエンド
│   ├── main.py                 # APIエンドポイント & DB連携
│   ├── agent.py                # 症状診断ロジック
│   ├── requirements.txt        # Python依存関係
│   └── Dockerfile              # APIコンテナ設定
├── web/                        # フロントエンド
│   └── realtime_demo.html      # WebRTC音声UI
├── db/                         # データベース設定
│   └── init/                   # DB初期化スクリプト
│       ├── 01_schema.sql       # テーブル定義
│       └── 02_seed.sql         # 初期データ投入
├── data/                       # ログデータ保存
├── .env.example                # 環境変数テンプレート
└── docker-compose.yml          # サービス編成設定
```

## 🗄️ データベース設計

### テーブル構成

- **hospitals**: 医療機関情報（ID、名前、位置情報）
- **slots**: 予約可能時間枠（病院ID、開始時刻、予約状況）
- **visits**: 予約情報（病院ID、スロットID、患者名、作成日時）

### 主要な関係性

```sql
hospitals (1) ←→ (N) slots (1) ←→ (1) visits
```

## 🚀 セットアップ

### 1. 環境変数の設定

`.env`ファイルをプロジェクトルートに作成してください：

```bash
# OpenAI API設定
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview
OPENAI_REALTIME_VOICE=verse

# データベース接続
DATABASE_URL=postgresql+asyncpg://app:app@db:5432/app

# CORS設定
CORS_ORIGINS=http://localhost:5173
```

### 2. Docker Composeでの起動（推奨）

```bash
# 全サービスのビルドと起動
docker-compose up --build

# バックグラウンドで実行する場合
docker-compose up -d --build

# ログ確認
docker-compose logs -f api
```

### 3. ローカル開発環境での起動

#### PostgreSQLの準備

```bash
# PostgreSQLを起動
docker-compose up -d db

# または既存のPostgreSQLインスタンスを使用
# DATABASE_URLを適切に設定してください
```

#### APIサーバー（FastAPI）

```bash
cd api
pip install -r requirements.txt

# 環境変数を設定
export DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app
export OPENAI_API_KEY=your_key_here

# サーバー起動
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Webサーバー（静的ファイル）

```bash
cd web
python -m http.server 5173
```

## 🌐 アクセス方法

- **Web UI**: http://localhost:5173
- **API ドキュメント**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432 (app/app)

## 📖 使用方法

### 基本的な操作フロー

1. **接続**: Webページで「🎙 Connect & Talk」ボタンをクリック
2. **名前入力**: 予約用の名前を入力フィールドに入力（任意）
3. **音声対話**: マイクに向かって自然に話しかける
4. **自動処理**: AIが音声を理解し、必要に応じてシステム機能を実行

### 音声コマンド例

```
「東京駅の近くの病院を探してください」
→ 位置情報を基に近隣医療機関を検索し、空きスロットを表示

「明日の午後2時に早稲田クリニックの予約を取りたいです」
→ 指定の病院と日時で予約を作成

「頭痛と38度の発熱があります」
→ 症状の緊急度を判定し、適切なアドバイスを提供

「予約をキャンセルしたいです」
→ 予約管理機能（将来の拡張予定）
```

## 🔧 API エンドポイント

### 認証・セッション管理

- `POST /realtime/token` - OpenAI Realtime用の一時トークン発行
  - リクエスト: `{user_id: string?}`
  - レスポンス: `{client_secret: {value: string}}`

### 医療機関管理

- `GET /hospitals` - 近隣病院の検索と空きスロット取得
  - パラメータ: `lat`, `lon`, `distance_km`
  - レスポンス: 病院リスト（ID、名前、距離、利用可能スロット）
  - データソース: PostgreSQL `hospitals`, `slots` テーブル

### 予約管理

- `POST /visit` - 医療機関予約の作成
  - ボディ: `{hospital_id: string, slot: string, name?: string}`
  - 機能: トランザクション処理による安全な予約作成
  - レスポンス: `{status: "ok", visit_id: number}`

### 診断システム

- `POST /diagnose` - 症状に基づく緊急度判定
  - ボディ: `{symptoms: string}`
  - レスポンス: `{emergency_level: "low"|"moderate"|"high", medical_report: string}`
  - ログ: JSONLファイルに診断履歴を保存

## 🧪 技術スタック

### バックエンド
- **Python 3.12+**
- **FastAPI**: 高性能なWeb APIフレームワーク
- **SQLAlchemy**: ORM + 非同期対応
- **asyncpg**: PostgreSQL非同期ドライバー
- **uvicorn**: ASGI対応アプリケーションサーバー
- **httpx**: 非同期HTTPクライアント
- **Pydantic**: データバリデーション

### データベース
- **PostgreSQL 16**: メインデータストア
- **トランザクション制御**: 予約の競合状態を防止
- **外部キー制約**: データ整合性の保証

### フロントエンド
- **HTML5 + JavaScript**: シンプルなWebインターフェース
- **WebRTC API**: リアルタイム音声通信
- **Fetch API**: REST API通信
- **改良されたUI**: 名前入力フィールド、絵文字アイコン

### インフラ
- **Docker & Docker Compose**: コンテナ化とサービス編成
- **nginx**: Webサーバー（本番環境）
- **OpenAI Realtime API**: 音声AI処理

## 📊 データフロー

```mermaid
graph TD
    A[ユーザー音声] --> B[WebRTC]
    B --> C[OpenAI Realtime API]
    C --> D[Function Calling]
    D --> E[FastAPI Backend]
    E --> F[PostgreSQL Database]
    F --> G[病院/予約/スロット管理]
    G --> E
    E --> D
    D --> C
    C --> H[音声レスポンス]
    H --> I[ユーザー]
    
    E --> J[診断ログ]
    J --> K[JSONLファイル]
```

## 🔧 開発・カスタマイズ

### 新機能の追加

1. **API エンドポイント**: `api/main.py`に新しいルートを追加
2. **データベーススキーマ**: `db/init/01_schema.sql`でテーブル定義
3. **音声機能**: OpenAI function callingの定義を更新
4. **フロントエンド**: `web/realtime_demo.html`の関数ハンドラーを拡張

### 診断ロジックの改善

`api/agent.py`の`run_web_diagnosis`関数を編集して、より高度な症状分析を実装：

```python
def run_web_diagnosis(symptoms: str) -> DiagnosisResult:
    # 機械学習モデルやルールベースエンジンの統合
    # 医療データベースとの連携
    # より詳細な緊急度判定ロジック
```

### データベースの拡張

```sql
-- 新しいテーブルの例
CREATE TABLE doctors (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    specialty TEXT,
    hospital_id TEXT REFERENCES hospitals(id)
);

-- 予約に医師情報を追加
ALTER TABLE visits ADD COLUMN doctor_id BIGINT REFERENCES doctors(id);
```

## 🔍 トラブルシューティング

### よくある問題

1. **データベース接続エラー**
   ```bash
   # PostgreSQLの起動確認
   docker-compose logs db
   
   # 接続テスト
   docker-compose exec db psql -U app -d app -c "SELECT 1;"
   ```

2. **OpenAI API エラー**
   ```bash
   # API キーの確認
   echo $OPENAI_API_KEY
   
   # トークン生成テスト
   curl -X POST http://localhost:8000/realtime/token \
        -H "Content-Type: application/json" \
        -d '{"user_id": "test"}'
   ```

3. **音声接続の問題**
   - HTTPSが必要（WebRTC要件）
   - マイクアクセス許可の確認
   - ファイアウォール設定の確認

## 🚨 注意事項

- **API キー**: OpenAI API キーは適切に保護してください
- **HTTPS**: 本番環境ではHTTPS化が必要です（WebRTC要件）
- **データプライバシー**: 医療情報を含む音声・予約データの適切な保護
- **データベースバックアップ**: 定期的なPostgreSQLバックアップの実施
- **トランザクション**: 予約の競合状態を防ぐためのロック機構
- **エラーハンドリング**: ネットワーク障害時の適切な処理

## 📈 今後の拡張予定

- [ ] 多言語対応（英語、中国語等）
- [ ] 医師の専門分野別検索
- [ ] 予約キャンセル・変更機能
- [ ] SMS/メール通知機能
- [ ] 管理者ダッシュボード
- [ ] API レート制限とセキュリティ強化

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビューション

バグレポート、機能要求、プルリクエストを歓迎します。

---

**重要**: これは医療アドバイスを提供するものではありません。実際の医療判断には必ず医療従事者にご相談ください。
