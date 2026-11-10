import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from guardrails import build_system_prompt, check_user_input, sanitize_assistant_output
from llm import chat_completion, health_check
from rag import RagStore

load_dotenv()

rag = RagStore()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="Acme Widgets Chat API", lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    sources: list[str]


class HealthResponse(BaseModel):
    status: str
    ollama: bool
    ollama_detail: str
    chunks_indexed: int


@app.get("/health", response_model=HealthResponse)
async def get_health():
    ok, detail = await health_check()
    return HealthResponse(
        status="ok" if ok else "degraded",
        ollama=ok,
        ollama_detail=detail,
        chunks_indexed=len(rag._chunks),
    )


@app.post("/chat", response_model=ChatResponse)
async def post_chat(body: ChatRequest):
    check = check_user_input(body.message)
    if not check.ok:
        raise HTTPException(status_code=400, detail=check.error)

    ollama_ok, ollama_detail = await health_check()
    if not ollama_ok:
        raise HTTPException(
            status_code=503,
            detail=f"LLM unavailable: {ollama_detail}. Install Ollama and run `ollama pull llama3.2`.",
        )

    hits = rag.retrieve(body.message)
    context_block = rag.format_context(hits)
    system = build_system_prompt()
    user_prompt = f"""Context from knowledge base:
{context_block}

Customer question:
{body.message}"""

    try:
        raw = await chat_completion(system, user_prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}") from e

    reply = sanitize_assistant_output(raw)
    sources = [h[0][:120] + ("..." if len(h[0]) > 120 else "") for h in hits]
    return ChatResponse(reply=reply, sources=sources)
