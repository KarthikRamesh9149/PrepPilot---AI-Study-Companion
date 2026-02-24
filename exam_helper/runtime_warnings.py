from __future__ import annotations

import warnings


def suppress_runtime_warnings() -> None:
    warnings.filterwarnings(
        "ignore",
        message=r"Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater\.",
        category=UserWarning,
        module=r"langchain_core\._api\.deprecation",
    )
