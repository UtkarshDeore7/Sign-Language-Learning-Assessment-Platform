from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role_id: int

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class LearnerProfileCreate(BaseModel):
    learning_level: str
    preferred_language: str
    learning_goals: str

class LearnerProfileResponse(BaseModel):
    id: int
    user_id: int
    learning_level: str
    preferred_language: str
    learning_goals: str
    created_at: datetime

    class Config:
        from_attributes = True

        from datetime import datetime
from typing import Any, Optional

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str = datetime.now().isoformat()