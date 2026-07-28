from app.signals.virality_signals import (
    extract as virality
)

from app.signals.competitive_signals import (
    extract as competitive
)

from app.signals.market_signals import (
    extract as market
)

from app.signals.customer_signals import (
    extract as customer
)

from app.signals.market_size_signals import (
    extract as market_size
)

from app.signals.market_opportunity_signals import (
    extract as market_opportunity
)



def build_signals(
    evidence
):
    from app.signals.virality_signals import (
    extract as virality
)

from app.signals.competitive_signals import (
    extract as competitive
)

from app.signals.market_signals import (
    extract as market
)

from app.signals.customer_signals import (
    extract as customer
)

from app.signals.market_size_signals import (
    extract as market_size
)

from app.signals.market_opportunity_signals import (
    extract as market_opportunity
)



def build_signals(
    evidence
):
    print("\nEVIDENCE COUNT:", len(evidence))

    sources = {}

    for item in evidence:

       source = item.get(
        "source",
        "unknown"
    )

       sources[source] = (
        sources.get(source, 0)
        + 1
    )

    print("\nSOURCE BREAKDOWN:")
    print(sources)

    return {

        "virality":
        virality(
            evidence
        ),

        "competitive":
        competitive(
            evidence
        ),

        "market":
        market(
            evidence
        ),

        "customer":
        customer(
            evidence
        ),
        
        "market_opportunity":
        market_opportunity(
            evidence
        ),

        "market_size":
        market_size(
            evidence
        )
    }

   