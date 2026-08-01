"""The two shapes everything scored or listed is published in.

Before this, every section invented its own: `{"estimate": str, "confidence": int}`
in market, `{"name": str, "score": int}` in customer with the score key renamed
per list, bare integers in signals, bare strings in synthesis. Five ways to
publish a number means five ways to render one, which is most of why the UI has
five ways to draw a number.

Nothing here replaces those. They are emitted alongside, under `report`, so the
deployed frontend keeps reading what it already reads.
"""

from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

ConfidenceBand = Literal["high", "moderate", "low", "none"]
ScoreBand = Literal["high", "moderate", "low"]

# The only three values the model is allowed to emit for an Insight score, and
# what each one is asserting. See app/payload/definitions.py:SCORE_SCALE.
BAND_BY_SCORE = {90: "high", 75: "moderate", 50: "low"}


def band_for_confidence(confidence: int | None) -> ConfidenceBand:
    if confidence is None:
        return "none"
    if confidence >= 80:
        return "high"
    if confidence >= 55:
        return "moderate"
    return "low"


class Estimate(BaseModel):
    """One figure, plus everything needed to decide whether to believe it.

    `display` is pre-formatted on purpose. The rounding rules, the suppression
    threshold and the em-dash for uncollected signals are all decisions about
    what the number *means*, and they belong next to the code that knows -- not
    in a frontend formatter that has to re-derive the context.
    """

    # `int` first so an exact count stays an int. With `float` first, pydantic
    # coerces 481 comments to 481.0, which reads as a measurement with a
    # decimal place rather than a count of things.
    value: int | float | str | None = None
    display: str
    unit: str | None = None
    confidence: int | None = None
    confidence_band: ConfidenceBand = "none"
    basis: str = ""
    source_count: int = 0
    evidence_ids: list[str] = []

    # True when the collector that feeds this figure contributed nothing to the
    # ranked evidence. Distinguishes "we looked and found none" from "we did not
    # look", which a bare 0 cannot.
    collected: bool = True

    @model_validator(mode="after")
    def _suppressed_values_have_no_number(self):
        if self.value is None and not self.display:
            raise ValueError("an Estimate with no value must still carry a display string")
        return self


class Insight(BaseModel):
    """One row in any ranked list.

    `label` is what the row renders and is length-capped, because the truncation
    the UI was doing with `line-clamp` was throwing away the only part of the
    row that carried meaning. `detail` is what the drawer renders.
    """

    id: str
    label: str
    detail: str = ""
    score: int
    score_band: ScoreBand
    evidence_ids: list[str] = []
    rank: int = 0

    @field_validator("score")
    @classmethod
    def _score_is_banded(cls, v: int) -> int:
        if v not in BAND_BY_SCORE:
            raise ValueError(
                f"score must be one of {sorted(BAND_BY_SCORE)}, got {v!r}"
            )
        return v

    @model_validator(mode="after")
    def _band_matches_score(self):
        expected = BAND_BY_SCORE[self.score]
        if self.score_band != expected:
            raise ValueError(
                f"score {self.score} implies band {expected!r}, got {self.score_band!r}"
            )
        return self


class InsightList(BaseModel):
    """A ranked list plus a statement of how it was ranked.

    The drawer currently tells the user the order is "as the model returned
    them", which says the visual hierarchy is meaningless. It is not meaningless
    any more, so the list says what it means instead.
    """

    key: str
    label: str
    metric_key: str
    sort_basis: str = "Score, then number of supporting sources"
    items: list[Insight] = []


class MetricDefinition(BaseModel):
    """What a column header actually means.

    Shipped in the payload rather than written into the frontend so that the
    definition lives next to the code that computes the number, and cannot drift
    from it.
    """

    key: str
    label: str
    definition: str
    derivation: str
    scale: str

    @model_validator(mode="after")
    def _definition_does_not_use_its_own_label(self):
        """A definition that contains its own label defines a word with itself.

        This is the check that rejects "Confidence in the pattern", which is
        what the drawer says today under WHAT THIS MEASURES.
        """
        if self.label.lower() in self.definition.lower():
            raise ValueError(
                f"definition for {self.key!r} contains its own label "
                f"({self.label!r}): {self.definition!r}"
            )
        return self
