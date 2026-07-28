# -*- coding: utf-8 -*-

"""
repo_guardian/core/domain/rules.py

Scentralizowane słowniki reguł analitycznych.
"""

RISK_RULES = {

    "exec": "exec",
    "eval": "eval",
    "compile": "reflection",

    "open": "filesystem_write",

    "connect": "network_io",

    "Thread": "threading",

    "setattr": "monkey_patch",
    "globals": "global_state",
    "locals": "reflection",
}

SIDE_EFFECT_RULES = {

    "open": "filesystem",

    "print": "logging",

    "sleep": "time",

    "random": "random",

    "connect": "network",

    "execute": "database",
}
