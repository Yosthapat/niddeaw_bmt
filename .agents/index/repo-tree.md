# Repo Tree

```
niddeaw_bmt/
├── ISSUE_beerminton_webapp.md      # spec + decisions log — read this first
├── logo-nidedeaw-badminton-club.jpg
├── frontend/                        # Vue3 + TS + Vite + Tailwind v4 + PWA
│   ├── src/{views/{public,admin},components,stores,api,composables,types,router}
│   └── public/pwa-icons/            # generated from the club logo
├── backend/                         # FastAPI + PDM
│   └── app/{models,services,routers/{public,admin}}
│       services/{elo_service,matchmaking_service,billing_service,promptpay_service,stats_service}.py
├── db/
│   ├── migrations/0001-0005_*.sql   # applied manually via Supabase SQL editor
│   └── seed/seed_dev.sql
└── deploy/{render.yaml,cloudflare/,ENV_SETUP.md}
```

See `.agents/topics/service-overview.md` for architecture/decisions detail.
