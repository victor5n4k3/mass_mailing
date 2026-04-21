from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Contact(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    nombre: str = Field(default="Cliente", min_length=1, max_length=255)
    status: str = Field(default="pending", pattern="^(pending|processing|sent|failed|invalid)$")


class BatchResult(BaseModel):
    total: int = Field(default=0, ge=0)
    sent: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    invalid: int = Field(default=0, ge=0)
