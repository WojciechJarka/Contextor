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


from repo_guardian.core.domain.rules import SIDE_EFFECT_RULES, RISK_RULES


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



    effect_hits = {}
    for name, count in visitor.calls.items():
        if name in SIDE_EFFECT_RULES:
            effect = SIDE_EFFECT_RULES[name]
            effect_hits[effect] = effect_hits.get(effect, 0) + count

    for effect, hits in effect_hits.items():
        effects.add(effect)
        effect_scores[effect] = _intensity_score(hits, saturation=3)

    risk_hits = {}
    for name, count in visitor.calls.items():
        if name in RISK_RULES:
            risk = RISK_RULES[name]
            risk_hits[risk] = risk_hits.get(risk, 0) + count

    if "global" in visitor.statements:
        risk_hits["global_state"] = risk_hits.get("global_state", 0) + 1

    for risk, hits in risk_hits.items():
        risks.add(risk)
        risk_scores[risk] = _intensity_score(hits, saturation=2)



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
