import random
import secrets
from datetime import datetime
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from ..models import User, DuplicateSticker, WantedSticker
from ..data.stickers_catalog import get_sticker_info


def _build_user_maps(db: Session) -> Tuple[Dict, Dict]:
    duplicates: Dict[int, Dict[int, int]] = {}
    wanted: Dict[int, set] = {}
    users = db.query(User).all()
    for user in users:
        duplicates[user.id] = {}
        wanted[user.id] = set()
    for dup in db.query(DuplicateSticker).all():
        duplicates[dup.user_id][dup.sticker_number] = dup.quantity
    for w in db.query(WantedSticker).all():
        wanted[w.user_id].add(w.sticker_number)
    return duplicates, wanted


def _score_trade(given: List[int], received: List[int]) -> float:
    if not given or not received:
        return 0.0
    balance = 1 - abs(len(given) - len(received)) / max(len(given), len(received))
    volume = min(len(given), len(received))
    return round(balance * 0.6 + (volume / 10) * 0.4, 4)


def generate_trade_suggestions(db: Session, max_per_pair: int = 5) -> dict:
    duplicates, wanted = _build_user_maps(db)
    users = db.query(User).all()
    user_map = {u.id: u for u in users}

    if len(users) < 2:
        return {"session_token": secrets.token_hex(32), "trades": [],
                "total_exchanges": 0, "generated_at": datetime.utcnow().isoformat()}

    candidate_trades = []
    user_ids = list(user_map.keys())

    for i, uid_a in enumerate(user_ids):
        for uid_b in user_ids[i + 1:]:
            dups_a = duplicates.get(uid_a, {})
            dups_b = duplicates.get(uid_b, {})
            want_a = wanted.get(uid_a, set())
            want_b = wanted.get(uid_b, set())

            a_can_give_b = [s for s, qty in dups_a.items() if s in want_b and qty > 0]
            b_can_give_a = [s for s, qty in dups_b.items() if s in want_a and qty > 0]

            if not a_can_give_b and not b_can_give_a:
                continue

            random.shuffle(a_can_give_b)
            random.shuffle(b_can_give_a)

            given = a_can_give_b[:max_per_pair]
            received = b_can_give_a[:max_per_pair]

            if not given and not received:
                continue

            score = _score_trade(given, received)

            def sticker_items(nums):
                return [{"sticker_number": n, **get_sticker_info(n)} for n in nums]

            ua = user_map[uid_a]
            ub = user_map[uid_b]

            candidate_trades.append({
                "from_user": {
                    "id": ua.id, "username": ua.username, "avatar_color": ua.avatar_color,
                    "duplicate_count": len(dups_a), "wanted_count": len(want_a)
                },
                "to_user": {
                    "id": ub.id, "username": ub.username, "avatar_color": ub.avatar_color,
                    "duplicate_count": len(dups_b), "wanted_count": len(want_b)
                },
                "stickers_given": sticker_items(given),
                "stickers_received": sticker_items(received),
                "score": score,
            })

    candidate_trades.sort(key=lambda t: t["score"], reverse=True)

    participation: Dict[int, int] = {}
    final_trades = []
    for trade in candidate_trades:
        uid_a = trade["from_user"]["id"]
        uid_b = trade["to_user"]["id"]
        if participation.get(uid_a, 0) < 2 and participation.get(uid_b, 0) < 2:
            final_trades.append(trade)
            participation[uid_a] = participation.get(uid_a, 0) + 1
            participation[uid_b] = participation.get(uid_b, 0) + 1

    total = sum(
        min(len(t["stickers_given"]), len(t["stickers_received"]))
        for t in final_trades
    )

    return {
        "session_token": secrets.token_hex(32),
        "trades": final_trades,
        "total_exchanges": total,
        "generated_at": datetime.utcnow().isoformat(),
    }
