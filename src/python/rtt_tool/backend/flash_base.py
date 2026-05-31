from abc import ABC, abstractmethod
from typing import Callable
from ..models.flash_params import FlashParams
from ..models.flash_result import FlashResult


class BaseFlashBackend(ABC):

    @abstractmethod
    def flash(self, params: FlashParams, progress_callback: Callable[[str], None]) -> FlashResult:
        ...

    @property
    @abstractmethod
    def backend_type(self) -> str:
        ...