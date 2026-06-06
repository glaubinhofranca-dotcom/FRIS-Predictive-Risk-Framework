from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])

MAX_USERS = 11

AVATAR_COLORS = [
    "#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6",
    "#1ABC9C", "#E67E22", "#34495E", "#E91E63", "#00BCD4", "#FF5722"
]


@router.post("/register", response_model=schemas.TokenResponse)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    count = db.query(models.User).count()
    if count >= MAX_USERS:
        raise HTTPException(400, "Grupo cheio! Máximo de 11 usuários.")

    if db.query(models.User).filter(models.User.username == user_in.username).first():
        raise HTTPException(400, "Nome de usuário já em uso.")
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(400, "E-mail já cadastrado.")

    color = AVATAR_COLORS[count % len(AVATAR_COLORS)]
    db_user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        avatar_color=color,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    token = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer", "user": db_user}


@router.post("/login", response_model=schemas.TokenResponse)
def login(creds: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(401, "Usuário ou senha incorretos.")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.get("/", response_model=list[schemas.UserPublic])
def list_users(db: Session = Depends(get_db), _=Depends(get_current_user)):
    users = db.query(models.User).all()
    result = []
    for u in users:
        dup_count = db.query(models.DuplicateSticker).filter(
            models.DuplicateSticker.user_id == u.id).count()
        want_count = db.query(models.WantedSticker).filter(
            models.WantedSticker.user_id == u.id).count()
        result.append(schemas.UserPublic(
            id=u.id, username=u.username, avatar_color=u.avatar_color,
            duplicate_count=dup_count, wanted_count=want_count
        ))
    return result
