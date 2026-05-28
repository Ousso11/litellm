"""
Compresr guardrail — discovery shim.

The actual hook lives in the Compresr SDK at ``compresr.integrations.litellm``. This
package's only job is to make the LiteLLM proxy's guardrail discovery loop
find the right registries under the ``"compresr"`` identifier, by importing
them from the SDK.

If ``compresr[litellm]`` is not installed, the registries are empty so the
proxy starts cleanly; the operator gets a clear error only if they actually
enable the guardrail without the SDK installed.
"""

from typing import Any, Dict

try:
    from compresr.integrations.litellm import (
        CompresrGuardrail,
        CompresrGuardrailError,
        CompresrGuardrailMissingSecrets,
        guardrail_class_registry,
        guardrail_initializer_registry,
        initialize_guardrail,
    )

    __all__ = [
        "CompresrGuardrail",
        "CompresrGuardrailError",
        "CompresrGuardrailMissingSecrets",
        "guardrail_class_registry",
        "guardrail_initializer_registry",
        "initialize_guardrail",
    ]
except ImportError:
    # compresr[litellm] not installed -- no-op registries so proxy startup is clean.
    guardrail_initializer_registry: Dict[str, Any] = {}
    guardrail_class_registry: Dict[str, Any] = {}

    __all__ = ["guardrail_initializer_registry", "guardrail_class_registry"]
