import re
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Self


class RegisterRequest(BaseModel):

    email: EmailStr = Field(
        ..., description="User's email address", examples=["user@example.com"]
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must be 8-128 characters with uppercase, lowercase, digit, and special character",
        examples=["SecurePass123!"],
    )

    password_confirm: str = Field(
        ...,
        description="Password confirmation must match password",
        examples=["SecurePass123!"],
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()

    # TODO: Add this back in
    # @field_validator('password')
    # @classmethod
    # def validate_password_strength(cls, v: str) -> str:
    #     """Validate password complexity requirements."""
    #     if not re.search(r'[A-Z]', v):
    #         raise ValueError('Password must contain at least one uppercase letter')
    #
    #     if not re.search(r'[a-z]', v):
    #         raise ValueError('Password must contain at least one lowercase letter')
    #
    #     if not re.search(r'\d', v):
    #         raise ValueError('Password must contain at least one digit')
    #
    #     if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~;]', v):
    #         raise ValueError('Password must contain at least one special character')
    #
    #     # Check for common weak passwords
    #     common_passwords = {
    #         'password', 'password123', '12345678', 'qwerty123',
    #         'admin123', 'letmein123', 'welcome123'
    #     }
    #     if v.lower() in common_passwords:
    #         raise ValueError('Password is too common. Please choose a stronger password')
    #
    #     # Check for whitespace
    #     if ' ' in v:
    #         raise ValueError('Password cannot contain spaces')
    #
    #     return v

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        """Validate that password and password_confirm match."""
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self

    # model_config = {
    #     "json_schema_extra": {
    #         "examples": [
    #             {
    #                 "email": "user@example.com",
    #                 "password": "SecurePass123!",
    #                 "password_confirm": "SecurePass123!"
    #             }
    #         ]
    #     }
    # }
