from fastapi import APIRouter

from app.controllers import auth_controller


api_router = APIRouter()
api_router.include_router(auth_controller.router)
