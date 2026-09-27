from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawListing:
    external_id: str
    title: str
    raw_address: str
    price: int | None
    deal_type: str
    posted_at: datetime
    url: str
    deposit: int | None = None
    monthly_rent: int | None = None
    area_m2: int | None = None
    rooms: int | None = None
    attributes: dict | None = None


class SourceAdapter(ABC):
    source_name: str

    @abstractmethod
    def fetch_new(self, city: str, category: str, since: datetime) -> list[RawListing]:
        ...