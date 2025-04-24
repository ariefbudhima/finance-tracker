# app/domains/transactions/models.py

from pydantic import BaseModel
from typing import List, Optional

class Item(BaseModel):
    name: str
    price: int
    quantity: int
    discount: Optional[int] = None

class Transaction(BaseModel):
    type: str
    amount: int
    date: str
    time: Optional[str] = None
    category: str
    note: Optional[str] = None
    source: Optional[str] = None
    items: List[Item]
