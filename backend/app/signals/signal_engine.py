"""Deterministic signal extraction. No network, no model.

The previous version of this file defined `build_signals` twice: the first
definition's body was a single indented `import`, after which the module-level
imports and a second `def build_signals` were pasted in again. It worked only
because the second definition shadowed the first. Both copies also recomputed
and re-printed the source breakdown that AnalysisService had already logged.
"""

from app.signals.competitive_signals import extract as competitive
from app.signals.customer_signals import extract as customer
from app.signals.market_opportunity_signals import extract as market_opportunity
from app.signals.market_signals import extract as market
from app.signals.market_size_signals import extract as market_size
from app.signals.virality_signals import extract as virality


def build_signals(evidence):
    return {
        "virality": virality(evidence),
        "competitive": competitive(evidence),
        "market": market(evidence),
        "customer": customer(evidence),
        "market_opportunity": market_opportunity(evidence),
        "market_size": market_size(evidence),
    }
