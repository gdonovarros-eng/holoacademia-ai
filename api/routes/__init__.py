from .academic import router as academic_router
from .protocols import router as protocols_router
from .therapeutic import router as therapeutic_router

__all__ = ["academic_router", "protocols_router", "therapeutic_router"]
