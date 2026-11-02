from typing import Literal

from pydantic import BaseModel


class SourceOut(BaseModel):
    title: str
    url: str
    publisher: str
    source_type: str
    note: str | None = None  # paraphrase of what this source says about the claim


class ClaimOut(BaseModel):
    key: str
    type: str
    text: str
    is_legend: bool
    sources: list[SourceOut]


class MonumentSummary(BaseModel):
    slug: str
    name: str
    city: str


class MonumentProfile(BaseModel):
    slug: str
    name: str
    description: str
    latitude: float
    longitude: float
    era: str
    architectural_style: str
    location: str
    city: str
    claims: list[ClaimOut]
    sources: list[SourceOut]  # every source behind this monument, deduplicated


class RelatedItem(BaseModel):
    relation_type: str
    direction: Literal["outgoing", "incoming"]
    note: str
    monument: MonumentSummary
    sources: list[SourceOut]  # evidence behind the edge's claim


class RelatedResponse(BaseModel):
    monument: MonumentSummary
    related: list[RelatedItem]