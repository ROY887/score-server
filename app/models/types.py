from enum import IntEnum


class TaskStatus(IntEnum):
    """ForcAD の models/types.py TaskStatus を移植。
    チェッカー終了コードと対応する。
    """

    UP = 101            # OK
    CORRUPT = 102       # 破損(接続できるが、期待したレスポンスが返ってこない)
    MUMBLE = 103        # Webサーバーは立ち上がっているが、internal server errorや無関係なデータが送られた時になる
    DOWN = 104          # 停止
    CHECKER_ERROR = 110 # チェッカー自身のバグ

    @classmethod
    def is_up(cls, status: int) -> bool:
        return status == cls.UP
