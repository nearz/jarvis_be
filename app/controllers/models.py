from ..core.logging import get_logger
from ..agent.supported_models import supported_models
from ..models import Model
from ..models.controller_models import SupportModelsResult, ErrorType

logger = get_logger(__name__)


async def supported_models_controller() -> SupportModelsResult:
    models: list[Model] = []

    try:
        for model_name, config in supported_models.items():
            m = Model(
                provider=config.provider,
                provider_display_name=config.provider_display_name,
                model=config.model,
                display_name=config.display_name,
            )
            models.append(m)
        return SupportModelsResult(success=True, supported_models=models)

    except ValueError:
        return SupportModelsResult(
            success=False,
            error_type=ErrorType.VALIDATION_ERROR,
            error_details="Database exception occurred",
        )

    except Exception:
        return SupportModelsResult(
            success=False,
            error_type=ErrorType.SYSTEM_ERROR,
            error_details="Unexpected system failure",
        )

    return models
