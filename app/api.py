"""HTTP API: savol -> javob.

Ishlatish:  uvicorn app.api:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.embedder import get_model
from app.search import Status, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_model()  # model server ishga tushganda bir marta yuklanadi
    yield


app = FastAPI(title="Savol-javob API", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class MatchOut(BaseModel):
    answer_id: int
    score: float
    matched_question: str
    answer: str


class AskResponse(BaseModel):
    status: Status
    matches: list[MatchOut]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    result = search(req.question)
    return AskResponse(
        status=result.status,
        matches=[MatchOut(**vars(m)) for m in result.matches],
    )
