# app/models.py
from pydantic import BaseModel

class TradingSignal(BaseModel):
    symbol: str
    direction: str
    position_size: float
    comment: str

