-- フラグ提出時にアトミックに呼び出すストアド関数
-- ForcAD の recalculate_rating() を参考に、Elo を廃しシンプルな加算方式に変更

CREATE OR REPLACE FUNCTION handle_flag_stolen(
    _attacker_id   INTEGER,
    _flag_id       INTEGER,
    _current_round INTEGER
) RETURNS TABLE (
    success      BOOLEAN,
    message      TEXT,
    attack_delta FLOAT
) AS $$
DECLARE
    _flag  RECORD;
    _delta FLOAT := 10.0;  -- 攻撃ポイント単価
BEGIN
    SELECT * INTO _flag FROM flags WHERE id = _flag_id;

    -- StolenFlags へ INSERT。PRIMARY KEY 制約で二重提出を弾く
    BEGIN
        INSERT INTO stolen_flags (flag_id, attacker_id)
        VALUES (_flag_id, _attacker_id);
    EXCEPTION WHEN unique_violation THEN
        success := FALSE;
        message := 'Flag already stolen';
        attack_delta := 0;
        RETURN NEXT;
        RETURN;
    END;

    -- 被攻撃チームの lost を加算
    UPDATE team_services
    SET lost = lost + 1
    WHERE team_id = _flag.team_id
      AND service_id = _flag.service_id
      AND round = _current_round;

    -- 攻撃チームの stolen / attack_pts を加算
    UPDATE team_services
    SET stolen = stolen + 1,
        attack_pts = attack_pts + _delta
    WHERE team_id = _attacker_id
      AND service_id = _flag.service_id
      AND round = _current_round;

    success := TRUE;
    message := format('Flag accepted! Earned %s flag points!', _delta);
    attack_delta := _delta;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;
