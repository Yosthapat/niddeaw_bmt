from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.admin import auth as admin_auth
from app.routers.admin import billing as admin_billing
from app.routers.admin import checkins as admin_checkins
from app.routers.admin import matchmaking as admin_matchmaking
from app.routers.admin import players_admin
from app.routers.admin import sessions as admin_sessions
from app.routers.admin import settings as admin_settings
from app.routers.public import hall_of_fame, matches, players, ranking

app = FastAPI(title="นิดเดียว Badminton Club API")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(players.router)
app.include_router(ranking.router)
app.include_router(hall_of_fame.router)
app.include_router(matches.router)

app.include_router(admin_auth.router)
app.include_router(admin_sessions.router)
app.include_router(admin_checkins.router)
app.include_router(players_admin.router)
app.include_router(admin_settings.router)
app.include_router(admin_matchmaking.router)
app.include_router(admin_billing.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Trivial liveness check — no DB dependency, so cron-job.org anti-cold-start
    pings don't fail on transient Supabase hiccups."""
    return {"status": "ok"}
