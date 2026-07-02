from datetime import datetime
from pydantic import BaseModel
from redirect_tracker.model import Redirect


class RedirectDto(BaseModel):
    id: int | None = None
    platform: str
    host: str
    user_agent: str
    destination: str
    created_at: datetime

    def to_model(self) -> Redirect:
        return Redirect(
            platform=self.platform,
            host=self.host,
            user_agent=self.user_agent,
            destination=self.destination,
            created_at=self.created_at,
        )
