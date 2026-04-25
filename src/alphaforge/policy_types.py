from __future__ import annotations

from typing import Literal

CandidateVerdict = Literal["candidate", "validated", "rejected", "inconclusive"]
ResearchPolicyVerdict = Literal["promote", "reject", "blocked"]
ParameterValue = int | float
ParameterGrid = dict[str, list[ParameterValue]]
