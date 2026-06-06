from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import get_current_user
from ..services.trade_matcher import generate_trade_suggestions

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.post("/generate")
def generate_trades(db: Session = Depends(get_db), _=Depends(get_current_user)):
    result = generate_trade_suggestions(db)
    return result


@router.get("/generate")
def get_trades(db: Session = Depends(get_db), _=Depends(get_current_user)):
    result = generate_trade_suggestions(db)
    return result
