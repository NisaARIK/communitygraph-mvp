
import os
import jwt
from jwt import PyJWKClient
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from openai import OpenAI

app = FastAPI(title="CommunityGraph AI API")
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")

security = HTTPBearer(auto_error=False)

jwks_client = PyJWKClient(
    f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
)


def verify_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Login required"
        )

    token = credentials.credentials

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=f"{SUPABASE_URL}/auth/v1",
            options={"require": ["exp", "iat", "sub", "aud", "iss"]}
        )

        return payload

    except Exception as exc:
        print(
            "JWT verification error:",
            type(exc).__name__,
            flush=True
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


class ProblemRequest(BaseModel):
    description: str = Field(min_length=10, max_length=5000)


class ProblemAnalysis(BaseModel):
    industry: str
    required_skills: list[str]
    expert_roles: list[str]


@app.get("/health")
def health():
    return {"status": "ok", "service": "communitygraph-ai"}


@app.post("/analyze", response_model=ProblemAnalysis)
def analyze_problem(
    request: ProblemRequest,
    user: dict = Depends(verify_user)
):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured",
        )

    try:
        client = OpenAI(api_key=api_key, timeout=30.0)

        response = client.responses.parse(
            model="gpt-4.1-mini",
            instructions=(
                "You are CommunityGraph's AI Problem Analyzer. "
                "Analyze startup, academic, open-source, and social "
                "impact problems. Identify the relevant industry, "
                "required skills, and expert roles. "
                "Do not invent people or connections."
            ),
            input=request.description,
            text_format=ProblemAnalysis,
            max_output_tokens=400,
        )

        if response.output_parsed is None:
            raise ValueError("No structured analysis returned")

        return response.output_parsed
    except Exception as e:
        print("AI_ERROR_TYPE:", type(e).__name__, flush=True)
        raise HTTPException(
            status_code=502,
            detail="AI analysis failed",
        )


class ExpertMatchRequest(BaseModel):
    industry: str
    required_skills: list[str]


@app.post("/recommend-experts")
def recommend_experts_endpoint(
    request: ExpertMatchRequest,
    user=Depends(verify_user),
):
    from backend.matching import recommend_experts
    from backend.neo4j_experts import get_experts

    try:
        experts = get_experts()

        matches = recommend_experts(
            analysis=request.model_dump(),
            experts=experts,
            top_k=3,
        )

        return {"matches": matches}

    except Exception as exc:
        print(
            "MATCHING_ERROR_TYPE:",
            type(exc).__name__,
            flush=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Expert matching temporarily unavailable",
        )
