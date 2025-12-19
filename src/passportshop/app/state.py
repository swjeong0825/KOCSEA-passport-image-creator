from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from passportshop.core.models import ProcessingParams
from passportshop.validation.report import ValidationReport

if TYPE_CHECKING:  # avoid importing Pillow at module import time
    from PIL import Image


@dataclass
class AppState:
    """
    Mutable state for a single GUI session.

    The GUI should read/write this state, while the controller is responsible for
    orchestrating transitions (upload -> process -> validate -> save).
    """
    # Input
    input_path: Optional[str] = None
    original_pil: Optional["Image.Image"] = None

    # Output (preview)
    processed_pil: Optional["Image.Image"] = None
    processed_temp_path: Optional[str] = None

    # User params
    params: ProcessingParams = field(default_factory=ProcessingParams)

    # Validation
    validation_report: Optional[ValidationReport] = None

    def reset(self) -> None:
        """Clear all session state (used by a Reset button)."""
        self.input_path = None
        self.original_pil = None
        self.processed_pil = None
        self.processed_temp_path = None
        self.validation_report = None
        self.params = ProcessingParams()  # restore defaults
