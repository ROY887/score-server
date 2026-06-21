-- ForcAD の create_tables.sql をベースに、CTFd AWD 連携カラムを追加して拡張

CREATE TABLE IF NOT EXISTS game_config (
    id                 SERIAL PRIMARY KEY,
    flag_lifetime      INTEGER NOT NULL DEFAULT 5,
    round_time         INTEGER NOT NULL DEFAULT 60,
    defense_point      INTEGER NOT NULL DEFAULT 5,
    volga_attacks_mode BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS teams (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    ip           INET NOT NULL,
    token        VARCHAR(16) NOT NULL UNIQUE,
    ctfd_team_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
    id                SERIAL PRIMARY KEY,
    name              TEXT NOT NULL,
    flag_prefix       CHAR(1) NOT NULL,
    ctfd_challenge_id INTEGER NOT NULL,
    ctfd_token        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS flags (
    id                SERIAL PRIMARY KEY,
    flag              VARCHAR(128) UNIQUE NOT NULL,
    team_id           INTEGER NOT NULL REFERENCES teams(id),
    service_id        INTEGER NOT NULL REFERENCES services(id),
    round             INTEGER NOT NULL,
    public_flag_data  TEXT NOT NULL DEFAULT '',
    private_flag_data TEXT NOT NULL DEFAULT '',
    expires_at        TIMESTAMPTZ NOT NULL,
    CONSTRAINT idx_flags_round_team UNIQUE (round, team_id, service_id)
);

CREATE INDEX IF NOT EXISTS idx_flags_round ON flags (round);
CREATE INDEX IF NOT EXISTS idx_flags_flag  ON flags (flag);

CREATE TABLE IF NOT EXISTS stolen_flags (
    flag_id     INTEGER NOT NULL REFERENCES flags(id),
    attacker_id INTEGER NOT NULL REFERENCES teams(id),
    submit_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (flag_id, attacker_id)
);

CREATE TABLE IF NOT EXISTS team_services (
    service_id    INTEGER NOT NULL REFERENCES services(id),
    team_id       INTEGER NOT NULL REFERENCES teams(id),
    round         INTEGER NOT NULL,
    stolen        INTEGER NOT NULL DEFAULT 0,
    lost          INTEGER NOT NULL DEFAULT 0,
    attack_pts    FLOAT   NOT NULL DEFAULT 0,
    defense_pts   FLOAT   NOT NULL DEFAULT 0,
    sla_status    INTEGER NOT NULL DEFAULT -1,
    checks        INTEGER NOT NULL DEFAULT 0,
    checks_passed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (team_id, service_id, round)
);

CREATE TABLE IF NOT EXISTS sla_results (
    id         BIGSERIAL PRIMARY KEY,
    team_id    INTEGER NOT NULL REFERENCES teams(id),
    service_id INTEGER NOT NULL REFERENCES services(id),
    round      INTEGER NOT NULL,
    status     INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
