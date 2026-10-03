
from app.domain.product import Product


class InMemoryProductRepository:
    def __init__(self, products: list[Product]) -> None:
        self._products: dict[str, Product] = {p.product_id: p for p in products}

    def get(self, product_id: str) -> Product | None:
        return self._products.get(product_id)

    def list(self) -> list[Product]:
        return list(self._products.values())

    def add(self, product: Product) -> Product:
        self._products[product.product_id] = product
        return product
