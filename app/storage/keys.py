"""Redis キー体系 (ForcAD の lib/storage/keys.py を移植)。"""


class CacheKeys:
    @staticmethod
    def team_by_token(token: str) -> str:
        return f"team:token:{token}"

    @staticmethod
    def flag_by_str(flag_str: str) -> str:
        return f"flag:str:{flag_str}"

    @staticmethod
    def flag_by_id(flag_id: int) -> str:
        return f"flag:id:{flag_id}"

    @staticmethod
    def team_stolen_flags(team_id: int) -> str:
        return f"team:{team_id}:stolen_flags"

    @staticmethod
    def current_round() -> str:
        return "real_round"

    @staticmethod
    def attack_data() -> str:
        return "attack_data"
