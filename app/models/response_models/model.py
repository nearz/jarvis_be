from pydantic import BaseModel
from ..model import Model


class SupportModelsResponse(BaseModel):
    success: bool = True
    supported_models: list[Model]
