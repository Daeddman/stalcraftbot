"""
Утилиты парсинга лотов аукциона Stalcraft.
Используется в history_sync.py и discovery.py.
"""

from typing import Any


def _parse_additional(lot: dict[str, Any]) -> tuple[int, int]:
    """
    Извлечь quality и upgrade_level из additional полей лота.
    qlt: -1..5 (качество/редкость артефакта)
    ptn: 0..15 (заточка артефакта — potency)
    """
    add = lot.get("additional", {})
    if not add:
        return -1, 0

    qlt = add.get("qlt", -1)
    if qlt is None:
        qlt = -1

    ptn = add.get("ptn", 0)
    if ptn is None:
        ptn = 0
    upgrade_level = min(15, max(0, int(ptn)))

    return int(qlt), int(upgrade_level)
