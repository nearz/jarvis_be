from pydantic import BaseModel, EmailStr


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


class UserResponse(BaseModel):
    id: str
    email: EmailStr

    class Config:
        json_schema = {
            "example": {
                "id": "uuid4",
                "email": "janedoe@example.com",
            }
        }
