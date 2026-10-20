from typing import List
from fastapi import APIRouter, status
from app.models.repository import repo
from app.schemas.reviews import ReviewCreate, ReviewRead

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("", response_model=ReviewRead, status_code=status.HTTP_201_CREATED, summary="Submit a review for a booking")
def create_review(review_in: ReviewCreate):
    return repo.create_review(review_in)

@router.get("", response_model=List[ReviewRead], summary="List all reviews")
def list_reviews():
    return repo.list_reviews()
