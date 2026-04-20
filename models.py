from pydantic import BaseModel, EmailStr, Field


class Contact(BaseModel):
    email: EmailStr
    nombre: str = Field(default="Cliente", min_length=1, max_length=255)
    status: str = "pending"
