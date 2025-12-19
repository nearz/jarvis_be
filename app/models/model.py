from pydantic import BaseModel


class Model(BaseModel):
    provider: str
    provider_display_name: str
    model: str
    display_name: str
