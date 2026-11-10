from pydantic import BaseModel, Field, EmailStr, model_serializer, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)
    reader_card: int | None = None

    @model_serializer(mode="wrap")
    def serialize(self, handler):
        data = handler(self)
        if self.role != UserRole.reader:
            data.pop("reader_card", None)
        return data

    name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    role: UserRole

class UserUpdateMe(BaseModel):
    name: None | str= Field(default=None, min_length=1, max_length=50)