# -*- coding: utf-8 -*-
# repo_guardian/core/module/errors.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationError:

    message: str

    module: str | None = None
