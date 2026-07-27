# -*- coding: utf-8 -*-

"""
repo_guardian/core/risk_analysis.py

AST risk and side effect extraction.

Facts only.
No architectural judgement.

Detects:
- side effects
- risky operations
- intensity scores

Score model:
- exponential saturation
- local risk intensity
- scale 0-1

This module does not use thresholds.
Threshold decisions belong to higher layers.
"""

import ast
import math


# ==========================================================
# SIDE EFFECT RULES
# ==========================================================


SIDE_EFFECT_RULES = {

    "filesystem_access":
        {
            "open",
        },

    "filesystem_write":
        {
            "write",
            "remove",
            "unlink",
            "mkdir",
            "makedirs",
        },

    "network":
        {
            "requests",
            "urlopen",
            "socket",
        },

    "process":
        {
            "Popen",
            "run",
            "call",
            "system",
        },

    "environment":
        {
            "getenv",
            "environ",
        },

    "logging":
        {
            "debug",
            "info",
            "warning",
            "error",
            "critical",
        },

    "random":
        {
            "random",
            "randint",
            "choice",
        },

    "time":
        {
            "sleep",
            "time",
        },
}


# ==========================================================
# RISK RULES
# ==========================================================


RISK_RULES = {

    "exec":
        {
            "exec",
        },

    "eval":
        {
            "eval",
        },

    "subprocess":
        {
            "Popen",
            "run",
            "call",
        },

    "reflection":
        {
            "getattr",
            "setattr",
            "inspect",
        },

    "filesystem_write":
        {
            "remove",
            "unlink",
            "write",
            "mkdir",
            "makedirs",
        },

    "global_state":
        {
            "global",
        },

    "threading":
        {
            "Thread",
            "Process",
        },
}


# ==========================================================
# AST VISITOR
# ==========================================================


class EffectVisitor(ast.NodeVisitor):

    def __init__(self):

        self.calls = {}
        self.statements = set()


    def visit_Call(
        self,
        node
    ):

        name = None


        if isinstance(
            node.func,
            ast.Name
        ):

            name = node.func.id


        elif isinstance(
            node.func,
            ast.Attribute
        ):

            name = node.func.attr


        if name:

            self.calls[name] = (
                self.calls.get(
                    name,
                    0
                )
                + 1
            )


        self.generic_visit(
            node
        )



    def visit_Global(
        self,
        node
    ):

        self.statements.add(
            "global"
        )

        self.generic_visit(
            node
        )


# ==========================================================
# SCORE MODEL
# ==========================================================


def _intensity_score(
    hits: int,
    saturation: float
) -> float:
    """
    Saturating exponential score.

    Small number of events:
        weak signal

    Many events:
        approaches 1.0

    Prevents linear explosion.
    """

    if hits <= 0:

        return 0.0


    return round(
        1 -
        math.exp(
            -hits / saturation
        ),
        4
    )


# ==========================================================
# PUBLIC API
# ==========================================================


def analyze_effects(
    tree
):

    visitor = EffectVisitor()

    visitor.visit(
        tree
    )


    effects = set()

    risks = set()


    effect_scores = {}

    risk_scores = {}



    for effect, names in SIDE_EFFECT_RULES.items():

        hits = sum(
            visitor.calls.get(
                name,
                0
            )
            for name in names
        )


        if hits:

            effects.add(
                effect
            )

            effect_scores[effect] = (
                _intensity_score(
                    hits,
                    saturation=3
                )
            )



    for risk, names in RISK_RULES.items():

        hits = sum(
            visitor.calls.get(
                name,
                0
            )
            for name in names
        )


        if "global" in names:

            if "global" in visitor.statements:

                hits += 1


        if hits:

            risks.add(
                risk
            )

            risk_scores[risk] = (
                _intensity_score(
                    hits,
                    saturation=2
                )
            )



    return {

        "side_effects":

            sorted(
                effects
            ),


        "side_effect_scores":

            effect_scores,


        "risks":

            sorted(
                risks
            ),


        "risk_scores":

            risk_scores,


        "analysis_meta":
        {

            "model":
                "exponential_saturation",


            "score_type":
                "local_risk_intensity",


            "scale":
                "0-1",


            "threshold_source":
                None,
        }
    }
