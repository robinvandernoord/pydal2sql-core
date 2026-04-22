"""
Expose methods for the library.
"""

# SPDX-FileCopyrightText: 2023-present Robin van der Noord <robinvandernoord@gmail.com>
#
# SPDX-License-Identifier: MIT

from .cli_support import (
    RenderContext,
    core_alter,
    core_create,
    core_stub,
    handle_cli,
    render_schema_from_code,
)
from .core import generate_sql
from .helpers import get_typing_args
from .types import SUPPORTED_DATABASE_TYPES as _SUPPORTED_DATABASE_TYPES

SUPPORTED_DATABASE_TYPES = get_typing_args(_SUPPORTED_DATABASE_TYPES)

__all__ = [
    "SUPPORTED_DATABASE_TYPES",
    "RenderContext",
    "core_alter",
    "core_create",
    "core_stub",
    "generate_sql",
    "get_typing_args",
    "handle_cli",
    "render_schema_from_code",
]
