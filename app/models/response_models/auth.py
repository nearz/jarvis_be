from pydantic import BaseModel


class RegisterResponse(BaseModel):
    success: bool = True
    message: str

    class Config:
        json_schema = {"example": {"success": True, "message": "User registered"}}


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"

    class Config:
        json_schema = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
