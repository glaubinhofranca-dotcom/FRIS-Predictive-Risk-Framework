from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    avatar_color: Optional[str] = "#4CAF50"

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3-50 characters")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    avatar_color: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    id: int
    username: str
    avatar_color: str
    duplicate_count: int = 0
    wanted_count: int = 0

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


class DuplicateStickerIn(BaseModel):
    sticker_number: int
    quantity: int = 1

    @field_validator("sticker_number")
    @classmethod
    def sticker_valid(cls, v):
        if v < 1 or v > 670:
            raise ValueError("Sticker number must be between 1 and 670")
        return v

    @field_validator("quantity")
    @classmethod
    def qty_valid(cls, v):
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class DuplicateStickerOut(BaseModel):
    id: int
    sticker_number: int
    quantity: int

    model_config = {"from_attributes": True}


class WantedStickerIn(BaseModel):
    sticker_number: int

    @field_validator("sticker_number")
    @classmethod
    def sticker_valid(cls, v):
        if v < 1 or v > 670:
            raise ValueError("Sticker number must be between 1 and 670")
        return v


class WantedStickerOut(BaseModel):
    id: int
    sticker_number: int

    model_config = {"from_attributes": True}


class TradeItem(BaseModel):
    sticker_number: int
    sticker_name: str
    section: str


class TradePair(BaseModel):
    from_user: UserPublic
    to_user: UserPublic
    stickers_given: List[TradeItem]
    stickers_received: List[TradeItem]
    score: float


class TradeSession(BaseModel):
    session_token: str
    trades: List[TradePair]
    total_exchanges: int
    generated_at: datetime


class BulkStickerUpdate(BaseModel):
    sticker_numbers: List[int]
    action: str

    @field_validator("action")
    @classmethod
    def action_valid(cls, v):
        if v not in ("add_duplicate", "remove_duplicate", "add_wanted", "remove_wanted"):
            raise ValueError("Invalid action")
        return v
