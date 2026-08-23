"""The ``BonusIssue`` value object: a free distribution of new shares to
existing holders, funded from reserves rather than cash paid by the holder.

TLV (Banca Transilvania) is BVB's most prominent example, having issued
bonus shares in most recent years — hence this sprint's name — but the
model here is generic and applies to any BVB-listed instrument.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class BonusIssue(BaseModel):
    """A bonus share issue: ``new_shares_per_held_share`` new shares are
    granted for every share already held, at zero cost.

    For example, a "1-for-4" bonus issue (1 new share for every 4 held) is
    ``new_shares_per_held_share=Decimal("0.25")``. Economically this is a
    stock dividend: it dilutes the average cost per share but does not
    change the total amount originally invested — see
    :meth:`~finapp.domain.entities.position.Position.with_bonus_shares`.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    new_shares_per_held_share: Decimal
    record_date: date

    @field_validator("symbol")
    @classmethod
    def _symbol_uppercase(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("BonusIssue.symbol must not be blank")
        return normalized

    @field_validator("new_shares_per_held_share")
    @classmethod
    def _ratio_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise ValueError(
                f"BonusIssue.new_shares_per_held_share must be positive, got {value}"
            )
        return value

    def __str__(self) -> str:
        return (
            f"{self.symbol} bonus issue: {self.new_shares_per_held_share} new share(s) "
            f"per share held, record date {self.record_date.isoformat()}"
        )
