"""
Compresr guardrail — config-model shim.

The canonical Pydantic config model lives in ``compresr.integrations.litellm.types``
(part of the Compresr SDK's ``[litellm]`` extra). The LiteLLM proxy admin UI
calls this module to render the configuration form.

Falls back to ``None`` if ``compresr[litellm]`` is not installed — the UI
gracefully hides the form in that case.
"""

try:
    from compresr.integrations.litellm.types import (
        CompresrGuardrailConfigModel,
        CompresrGuardrailConfigModelOptionalParams,
    )

    __all__ = [
        "CompresrGuardrailConfigModel",
        "CompresrGuardrailConfigModelOptionalParams",
    ]
except ImportError:
    CompresrGuardrailConfigModel = None  # type: ignore[assignment,misc]
    CompresrGuardrailConfigModelOptionalParams = None  # type: ignore[assignment,misc]

    __all__ = []
