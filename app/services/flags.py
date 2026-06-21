"""フラグ生成 (ForcAD の lib/models/flag.py Flag.generate() を移植)。"""

import secrets
import string

ALPHABET = string.ascii_uppercase + string.digits


def generate_flag(service_name: str) -> str:
    """サービス名の先頭文字 + ランダム30文字 + '=' 形式のフラグを生成する。

    例: "W" + 30 文字 + "=" → "W4F...XYZ=" (全 32 文字)
    """
    service_letter = service_name[0].upper()
    rnd_data = "".join(secrets.choice(ALPHABET) for _ in range(30))
    return service_letter + rnd_data + "="
