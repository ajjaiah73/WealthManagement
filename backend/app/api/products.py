from fastapi import APIRouter

from app.container import container
from app.domain.product import Product

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[Product])
def list_products() -> list[Product]:
    return container.product_repository.list()
