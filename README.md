# Score Server

A&DのCTF用スコアサーバー。
ForcADのフラグ受付・スコア計算ロジックを FastAPI + SQLAlchemy(async)へ移植し、
スコア表示は CTFd の AWD プラグイン (`/plugins/awd/api/update`) へ連携する。

担当範囲: **スコア計算・フラグ受付のみ**（SLA チェック本体・フラグローテーションは別チーム）。

## 起動

```bash
docker compose up --build
```

起動時に `score-server` コンテナの `command` が `scripts/init_db.py` を実行し、
スキーマ・ストアド関数・サンプルデータを投入する。

### DB を手動で再投入する場合

`init_db` は Compose ネットワーク内のサービス名（db /redis / flagdb）へ
接続するため、**コンテナ内で実行する**。ホスト側で直接 `python -m scripts.init_db`
を実行すると db を名前解決できず失敗する。

```bash
docker compose exec score-server python -m scripts.init_db
```

## エンドポイント

| エンドポイント | 呼び出し元 | 認証 |
| `PUT /flags/` | 参加チームPC | `X-Team-Token` |
| `POST /sla` | SLA チェッカー | なし |
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

## CTFd（スコア表示）のセットアップ

スコア表示は CTFd + A&D プラグインが担う。score-server はラウンド切り替え時に
集計を `http://<CTFd>/plugins/awd/api/update` へ POST する（score-server の
`CTFD_URL` 既定は `http://host.docker.internal:8000`）。

CTFd は score-server とは**別の docker-compose スタック**として起動する
（本リポジトリ外。既定の設置先は `~/CTFd`）。

### 1. CTFd を clone

```bash
git clone https://github.com/CTFd/CTFd.git ~/CTFd
cd ~/CTFd
```

### 2. A&D プラグインを配置

[splitline/CTFd-Attack-and-Defense-Plugin](https://github.com/splitline/CTFd-Attack-and-Defense-Plugin)
を `CTFd/plugins/awd` へ clone する。CTFd は起動時に `plugins/` 直下を自動ロードする。

```bash
git clone https://github.com/splitline/CTFd-Attack-and-Defense-Plugin.git \
  ~/CTFd/CTFd/plugins/awd
```

### 3. 起動

```bash
cd ~/CTFd
# SECRET_KEY を用意（未設定なら生成して .env に書く）
# [ -f .env ] || echo "SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_hex(32))')" > .env
# docker compose up -d --build
```

- CTFd（アプリ直）: <http://localhost:8000>
- CTFd（nginx 経由）: <http://localhost:80>

初回は <http://localhost:8000/setup> で管理者・大会名を作成する。

### 4. AWD チャレンジ作成と連携設定

1. 管理画面で **AWD** タイプのチャレンジを作成する（例: `service-a`, `service-b`）。
2. 作成後に表示される **challenge id** と **token** を控える。
3. score-server 側の [scripts/seed.py](scripts/seed.py) の `SERVICES[].ctfd_challenge_id`
   / `ctfd_token`、および `TEAMS[].ctfd_team_id` を CTFd の値に合わせる。
4. score-server で再投入して反映する。

   ```bash
   docker compose exec score-server python -m scripts.init_db
   ```

> score-server は別 compose プロジェクト（別ネットワーク）のため、コンテナから
> CTFd へは `host.docker.internal:8000`（ホスト公開ポート）経由で到達する。
> CTFd が停止していても ingest は継続し、push 失敗は警告ログのみ（[docs/テスト手順.md](docs/テスト手順.md) 7-4）。

## 設計のポイント

- **二重提出防止**: `stolen_flags` の複合 PK (`flag_id`, `attacker_id`) を DB レベルで保証。
  ストアド関数 `handle_flag_stolen()` が `unique_violation` を捕捉して "Flag already stolen" を返す。
- **判定順序**: ForcAD `handle_attack()` を踏襲（Invalid → 自チーム → 期限切れ → サービスダウン → 加点）。
- **Redis キャッシュ**: フラグ・チームトークン・ゲーム設定をキャッシュし DB アクセスを削減。
- **CTFd 連携**: ラウンド切り替え時に直前ラウンドの集計を AWD プラグインへ POST。
- **フラグ取り込み**: ローテーター MySQL をポーリングして PostgreSQL に取り込む。

## ディレクトリ

```a
app/
  api/        flags / sla / scoreboard / health の各ルーター
  models/     SQLAlchemy モデル・Pydantic スキーマ・TaskStatus Enum
  services/   handle_attack / フラグ生成 / 防御計算 / CTFd 連携
  storage/    Redis キー・キャッシュ・ラウンド管理
  core/       設定・DB/Redis 接続
scripts/      create_tables.sql / create_functions.sql / init_db.py
```

## clear 

# ── ① score-server 側：チーム・フラグ・履歴を全消去（スキーマは維持） ──

```bash
cd ~/score-server
docker compose exec db psql -U score -d score -c "
TRUNCATE TABLE stolen_flags, team_services, flags, sla_results, teams RESTART IDENTITY CASCADE;
"
docker compose exec redis redis-cli FLUSHALL
```

# ── ② CTFd 側：team/user(adminを除く)とスコア履歴を全消去（チャレンジ設定は維持） ──

```bash
cd ~/CTFd
docker compose exec db mysql -uctfd -pctfd ctfd -e "
DELETE FROM notifications;
DELETE FROM users WHERE type != 'admin';
DELETE FROM teams;
"
```

