from pydantic import BaseModel, Field, EmailStr, model_validator
from enum import Enum

class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=72)
    password_confirm: str = Field(min_length=8, max_length=72)
    
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

class UserRole(str, Enum):
    reader = "reader"
    librarian = "librarian"

class UserOutMe(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    role: UserRole

class UserUpdateMe(BaseModel):
    name: None | str= Field(default=None, min_length=1, max_length=50)