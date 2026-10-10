"""HTTP API: savol -> javob.

Ishlatish:  uvicorn app.api:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.embedder import get_model
from app.search import Status, answer_text, search


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


class AnswerOut(BaseModel):
    answer_id: int
    answer: str


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


@app.get("/answers/{answer_id}", response_model=AnswerOut)
def get_answer(answer_id: int) -> AnswerOut:
    text = answer_text(answer_id)
    if text is None:
        raise HTTPException(status_code=404, detail="Javob topilmadi")
    return AnswerOut(answer_id=answer_id, answer=text)
