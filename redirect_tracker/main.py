from datetime import datetime
from typing import Annotated, TypeAlias

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from redirect_tracker.dto import RedirectDto
from redirect_tracker.session import get_session

app = FastAPI()
SessionDep: TypeAlias = Annotated[Session, Depends(get_session)]


@app.get("/redirect")
async def redirect(
    session: SessionDep,
    request: Request,
    platform: str,
    user_agent: Annotated[str | None, Header()],
    destination: str,
):
    redirect_dto = RedirectDto(
        platform=platform,
        host=request.client.host if request.client else "",
        user_agent=user_agent or "",
        destination=destination,
        created_at=datetime.now(),
    )
    redirect_model = redirect_dto.to_model()

    session.add(redirect_model)
    session.commit()
    session.refresh(redirect_model)

    return RedirectResponse(url=destination)
