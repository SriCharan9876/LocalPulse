from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    credential: Optional[str] = Field(None, description="Google ID Token (JWT) from Google Identity Services")
    id_token: Optional[str] = Field(None, description="Alternative field for Google ID Token")
    access_token: Optional[str] = Field(None, description="Google OAuth access token")
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    business_name: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class SendOtpRequest(BaseModel):
    phone_or_email: str = Field(..., min_length=3, max_length=100)

class VerifyOtpRequest(BaseModel):
    phone_or_email: str = Field(..., min_length=3, max_length=100)
    otp: str = Field(..., min_length=4, max_length=8)

class OtpResponse(BaseModel):
    status: str
    message: str
    phone_or_email: str
    demo_otp: Optional[str] = None
    expires_in_seconds: int = 300

class SignupRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=100)
    owner_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    category: str = Field(..., min_length=2, max_length=50)  # e.g., Grocery, Cafe, Bakery, Apparel
    address: str = Field(..., min_length=3)
    phone: str = Field(..., min_length=10, max_length=15)
    latitude: Optional[float] = Field(None, description="GPS Latitude")
    longitude: Optional[float] = Field(None, description="GPS Longitude")

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

class MerchantProfileUpdate(BaseModel):
    business_name: Optional[str] = Field(None, min_length=2, max_length=100)
    owner_name: Optional[str] = Field(None, min_length=2, max_length=100)
    category: Optional[str] = Field(None, min_length=2, max_length=50)
    address: Optional[str] = Field(None, min_length=3)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    merchant: MerchantProfile

class SwitchDemoMerchantRequest(BaseModel):
    merchant_id: str
