# Score Server

A&DのCTF用スコアサーバー。
ForcADのフラグ受付・スコア計算ロジックを FastAPI + SQLAlchemy(async)へ移植し、
スコア表示は CTFd の AWD プラグイン (`/plugins/awd/api/update`) へ連携する。

担当範囲: **スコア計算・フラグ受付のみ**（SLA チェック本体・フラグローテーションは別チーム）。

## 起動

```bash
docker compose up --build
```

起動時に `scripts/init_db.py` がスキーマ・ストアド関数・サンプルデータを投入する。

ローカル実行する場合:

```bash
pip install -r requirements.txt
python -m scripts.init_db
uvicorn app.main:app --reload
```

## エンドポイント

| エンドポイント | 呼び出し元 | 認証 |
| `PUT /flags/` | 参加チームPC | `X-Team-Token` |
| `POST /sla` | SLA チェッカー | `X-Internal-Key` |
| `GET /scoreboard` | 公開 | なし |
| `GET /attack_data` | 参加チームPC | `X-Team-Token` |
| `GET /health/` | 監視 | なし |

> フラグの取り込みは HTTP エンドポイントではなく、フラグローテーターが書き込む
> **MySQL `ctf_flags` のポーリング**で行う（下記「フラグローテーター連携」参照）。

### フラグ提出例

```bash
curl -X PUT http://localhost:8000/flags/ \
  -H "X-Team-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '["FLAG{...}", "FLAG{...}"]'
```

## フラグローテーター連携

フラグローテーター（`engineering-design-5th-grade`）は新フラグを各チームVMへ
SSH 配置すると同時に、**MySQL `ctf_flags.flags`**（`round, team, service, flag`）へ
直接書き込む。score-server はローテーターを一切変更せず、この MySQL を
`INGEST_POLL_SECONDS` ごとにポーリングして取り込む（[app/services/ingest.py](app/services/ingest.py)）。

- **名前→ID 解決**: ローテーターは team/service を**名前**で持つため、score-server の
  `teams.name` / `services.name` をローテーター `config.py` の `TEAMS[].name` /
  `services` キー（例: `team1`, `service-a`, `service-b`）と一致させておく。
- **ラウンド進行**: 取り込み時に `current_round`（Redis `real_round`）を進め、
  直前ラウンドの集計を CTFd へ反映する。
- ローテーター側 MySQL は docker-compose の `flagdb` サービスが提供する
  （ローテーター `config.py` の `host` をこのスコアサーバの IP に向ける）。

## 設計のポイント

- **二重提出防止**: `stolen_flags` の複合 PK (`flag_id`, `attacker_id`) を DB レベルで保証。
  ストアド関数 `handle_flag_stolen()` が `unique_violation` を捕捉して "Flag already stolen" を返す。
- **判定順序**: ForcAD `handle_attack()` を踏襲（Invalid → 自チーム → 期限切れ → サービスダウン → 加点）。
- **Redis キャッシュ**: フラグ・チームトークン・ゲーム設定をキャッシュし DB アクセスを削減。
- **CTFd 連携**: ラウンド切り替え時に直前ラウンドの集計を AWD プラグインへ POST。
- **フラグ取り込み**: ローテーター MySQL をポーリングして PostgreSQL に取り込む。

## ディレクトリ

```
app/
  api/        flags / sla / scoreboard / health の各ルーター
  models/     SQLAlchemy モデル・Pydantic スキーマ・TaskStatus Enum
  services/   handle_attack / フラグ生成 / 防御計算 / CTFd 連携
  storage/    Redis キー・キャッシュ・ラウンド管理
  core/       設定・DB/Redis 接続
scripts/      create_tables.sql / create_functions.sql / init_db.py
```
