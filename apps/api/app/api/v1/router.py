"""Aggregates all /api/v1 routers. Add new resource routers here as phases land."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.customers import router as customers_router
from app.api.v1.health import router as health_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.tickets import router as tickets_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(customers_router)
api_v1_router.include_router(tickets_router)
api_v1_router.include_router(integrations_router)
