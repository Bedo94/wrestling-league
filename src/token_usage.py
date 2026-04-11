from __future__ import annotations

from typing import Literal


TokenUsedBy = Literal["athlete_a", "athlete_b"]

TOKEN_USED_BY_ATHLETE_A: TokenUsedBy = "athlete_a"
TOKEN_USED_BY_ATHLETE_B: TokenUsedBy = "athlete_b"


def get_token_used_by_from_spender_id(
    *,
    athlete_a_id: int,
    athlete_b_id: int,
    token_spender_id: int | None,
) -> TokenUsedBy | None:
    if token_spender_id is None:
        return None

    if token_spender_id == athlete_a_id:
        return TOKEN_USED_BY_ATHLETE_A

    if token_spender_id == athlete_b_id:
        return TOKEN_USED_BY_ATHLETE_B

    raise ValueError("Il token spender deve essere uno dei due partecipanti.")


def get_token_spender_id_from_used_by(
    *,
    athlete_a_id: int,
    athlete_b_id: int,
    token_used_by: TokenUsedBy | None,
) -> int | None:
    if token_used_by is None:
        return None

    if token_used_by == TOKEN_USED_BY_ATHLETE_A:
        return athlete_a_id

    if token_used_by == TOKEN_USED_BY_ATHLETE_B:
        return athlete_b_id

    raise ValueError(f"token_used_by non valido: {token_used_by}")
