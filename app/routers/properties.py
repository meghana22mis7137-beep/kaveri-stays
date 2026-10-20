from typing import List, Optional
from fastapi import APIRouter, Path, Query
from app.models.repository import repo
from app.schemas.properties import PropertyRead, RoomRead

router = APIRouter(prefix="/properties", tags=["Properties"])

@router.get("", response_model=List[PropertyRead], summary="List all properties")
def list_properties():
    return repo.list_properties()

@router.get("/{property_id}", response_model=PropertyRead, summary="Get property by ID")
def get_property(property_id: int = Path(..., gt=0)):
    prop = repo.get_property(property_id)
    rooms = repo.list_rooms(property_id=property_id)
    return {**prop, "rooms": rooms}

@router.get("/{property_id}/rooms", response_model=List[RoomRead], summary="List rooms for a property")
def list_property_rooms(property_id: int = Path(..., gt=0)):
    # Verify property exists
    repo.get_property(property_id)
    return repo.list_rooms(property_id=property_id)
