from pydantic import BaseModel


class BaseProduct(BaseModel):
    title: str
    description: str
    price: float


class ProductCreate(BaseProduct):
    user_id: int


class ProductUpdate(BaseProduct):
    pass


class ProductResponse(BaseProduct):
    id: int
    user_id: int
