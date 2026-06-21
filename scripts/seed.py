"""初期投入データ（実構成に合わせてここだけ編集する）。

重要: `name` はフラグローテーター側 `config.py` と必ず一致させること。
  - TEAMS[].name      → ローテーター config.py の TEAMS[].name
  - SERVICES[].name   → ローテーター config.py の TEAMS[].services のキー
名前が一致しないと、取り込み (app/services/ingest.py) で
「未知の team/service」として警告ログを出してスキップされる。

ctfd_team_id / ctfd_challenge_id / ctfd_token は CTFd 側で
チーム・AWDChallenge を作成した際の値に置き換えること。
"""

# --- ゲーム設定 (game_config は 1 行のみ) ---
GAME = {
    "flag_lifetime": 5,       # フラグ有効ラウンド数
    "round_time": 60,         # 1 ラウンドの秒数 (ローテーターの周期に合わせる)
    "defense_point": 5,       # 防御成功時の付与ポイント
    "volga_attacks_mode": False,
}

# --- サービス (ローテーター config.py の services キーと一致させる) ---
SERVICES = [
    {"name": "service-a", "ctfd_challenge_id": 1, "ctfd_token": "ee261e1652af650d0bc48c456df3cac3"},
    {"name": "service-b", "ctfd_challenge_id": 2, "ctfd_token": "6046c4ffec5695c7847851694196f8bc"},
]

# --- チーム (ローテーター config.py の TEAMS[].name / host と一致させる) ---
#   name         : ローテーターと一致させる識別名
#   ip           : チームVMのゲームネットワーク側IP (ローテーター config の host)
#   ctfd_team_id : CTFd 上のチームID (AWD プラグインに渡す)
#   token        : 省略時は secrets.token_hex(8) で自動生成
TEAMS = [
    {"name": "team1", "ip": "127.0.0.1", "ctfd_team_id": 1},
]
