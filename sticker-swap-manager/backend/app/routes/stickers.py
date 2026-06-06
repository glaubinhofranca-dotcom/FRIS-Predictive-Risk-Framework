from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user
from ..data.stickers_catalog import get_all_stickers, SECTIONS

router = APIRouter(prefix="/api/stickers", tags=["stickers"])


@router.get("/catalog")
def get_catalog():
    return get_all_stickers()


@router.get("/sections")
def get_sections():
    return SECTIONS


@router.get("/my/duplicates", response_model=List[schemas.DuplicateStickerOut])
def my_duplicates(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.DuplicateSticker).filter(
        models.DuplicateSticker.user_id == user.id).all()


@router.get("/my/wanted", response_model=List[schemas.WantedStickerOut])
def my_wanted(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.WantedSticker).filter(
        models.WantedSticker.user_id == user.id).all()


@router.post("/my/duplicates", response_model=schemas.DuplicateStickerOut)
def add_duplicate(item: schemas.DuplicateStickerIn, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    existing = db.query(models.DuplicateSticker).filter(
        models.DuplicateSticker.user_id == user.id,
        models.DuplicateSticker.sticker_number == item.sticker_number
    ).first()
    if existing:
        existing.quantity = item.quantity
        db.commit()
        db.refresh(existing)
        return existing
    new = models.DuplicateSticker(user_id=user.id, sticker_number=item.sticker_number,
                                   quantity=item.quantity)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


@router.delete("/my/duplicates/{sticker_number}")
def remove_duplicate(sticker_number: int, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    row = db.query(models.DuplicateSticker).filter(
        models.DuplicateSticker.user_id == user.id,
        models.DuplicateSticker.sticker_number == sticker_number
    ).first()
    if not row:
        raise HTTPException(404, "Figurinha não encontrada.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/my/wanted", response_model=schemas.WantedStickerOut)
def add_wanted(item: schemas.WantedStickerIn, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    existing = db.query(models.WantedSticker).filter(
        models.WantedSticker.user_id == user.id,
        models.WantedSticker.sticker_number == item.sticker_number
    ).first()
    if existing:
        return existing
    new = models.WantedSticker(user_id=user.id, sticker_number=item.sticker_number)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


@router.delete("/my/wanted/{sticker_number}")
def remove_wanted(sticker_number: int, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    row = db.query(models.WantedSticker).filter(
        models.WantedSticker.user_id == user.id,
        models.WantedSticker.sticker_number == sticker_number
    ).first()
    if not row:
        raise HTTPException(404, "Figurinha não encontrada.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/group-overview")
def group_overview(db: Session = Depends(get_db), _=Depends(get_current_user)):
    users = db.query(models.User).all()
    overview = []
    for u in users:
        dups = db.query(models.DuplicateSticker).filter(
            models.DuplicateSticker.user_id == u.id).all()
        wants = db.query(models.WantedSticker).filter(
            models.WantedSticker.user_id == u.id).all()
        overview.append({
            "user": {"id": u.id, "username": u.username, "avatar_color": u.avatar_color},
            "duplicates": [{"sticker_number": d.sticker_number, "quantity": d.quantity} for d in dups],
            "wanted": [w.sticker_number for w in wants],
        })
    return overview


@router.post("/my/bulk")
def bulk_update(payload: schemas.BulkStickerUpdate, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    if payload.action == "add_duplicate":
        for n in payload.sticker_numbers:
            existing = db.query(models.DuplicateSticker).filter(
                models.DuplicateSticker.user_id == user.id,
                models.DuplicateSticker.sticker_number == n
            ).first()
            if existing:
                existing.quantity += 1
            else:
                db.add(models.DuplicateSticker(user_id=user.id, sticker_number=n, quantity=1))
    elif payload.action == "remove_duplicate":
        db.query(models.DuplicateSticker).filter(
            models.DuplicateSticker.user_id == user.id,
            models.DuplicateSticker.sticker_number.in_(payload.sticker_numbers)
        ).delete(synchronize_session=False)
    elif payload.action == "add_wanted":
        for n in payload.sticker_numbers:
            if not db.query(models.WantedSticker).filter(
                models.WantedSticker.user_id == user.id,
                models.WantedSticker.sticker_number == n
            ).first():
                db.add(models.WantedSticker(user_id=user.id, sticker_number=n))
    elif payload.action == "remove_wanted":
        db.query(models.WantedSticker).filter(
            models.WantedSticker.user_id == user.id,
            models.WantedSticker.sticker_number.in_(payload.sticker_numbers)
        ).delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "updated": len(payload.sticker_numbers)}
