from typing import List
from fastapi import APIRouter, Path, status
from app.models.repository import repo
from app.schemas.guests import GuestCreate, GuestRead

router = APIRouter(prefix="/guests", tags=["Guests"])

@router.post("", response_model=GuestRead, status_code=status.HTTP_201_CREATED, summary="Create/register a guest")
def create_guest(guest_in: GuestCreate):
    return repo.create_guest(guest_in)

@router.get("", response_model=List[GuestRead], summary="List all registered guests")
def list_guests():
    return repo.list_guests()

@router.get("/{guest_id}", response_model=GuestRead, summary="Get guest by ID")
def get_guest(guest_id: int = Path(..., gt=0)):
    return repo.get_guest(guest_id)
