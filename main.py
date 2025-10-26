from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from core.config_loader import settings

from auth.routes.auth_router import auth_router
from user.router import user_router
from shift.router import shift_router
from location.router import location_router
from employee.router import employee_router
from preference.router import pref_router
from jobrole.router import jobrole_router
from organization.router import organization_router
import models_bootstrap 

openapi_tags = [
    {
        "name": "Users",
        "description": "User operations",
    },
    {
        "name": "Health Checks",
        "description": "Application health checks",
    }
]

app = FastAPI(openapi_tags=openapi_tags)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(shift_router, prefix="/api")
app.include_router(location_router, prefix="/api")
app.include_router(pref_router, prefix="/api")
app.include_router(employee_router, prefix="/api")
app.include_router(jobrole_router, prefix="/api")
app.include_router(organization_router, prefix="/api")



@app.get("/health", tags=['Health Checks'])
def read_root():
    return {"health": "true"}

