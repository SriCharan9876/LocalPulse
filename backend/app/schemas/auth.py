from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=100)
    owner_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    category: str = Field(..., min_length=2, max_length=50)  # e.g., Grocery, Cafe, Bakery, Apparel
    address: str = Field(..., min_length=3)
    phone: str = Field(..., min_length=10, max_length=15)

class MerchantProfile(BaseModel):
    merchant_id: str
    business_name: str
    owner_name: str
    email: EmailStr
    category: str
    address: str
    phone: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    coordinates: Optional[dict] = None
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    merchant: MerchantProfile

class SwitchDemoMerchantRequest(BaseModel):
    merchant_id: str
