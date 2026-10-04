from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src import get_db
from src.config import settings
from src.schemas import ProductCreate, ProductResponse, ProductUpdate
from src.models import Product
from src.events import (
    send_product_created_event,
    send_product_updated_event,
    start_producer,
    stop_producer,
)
from src.services.user_service import user_service, UserService


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer()
    yield
    await stop_producer()


app = FastAPI(
    title="Products service",
    description="Microservice on FastAPI to manage products",
    debug=settings.debug,
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/products", response_model=list[ProductResponse])
async def get_products(db: Annotated[AsyncSession, Depends(get_db)]):
    products = await db.scalars(select(Product))
    result = []

    for product in products:
        result.append(
            ProductResponse(
                id=product.id,
                user_id=product.user_id,
                title=product.title,
                description=product.description,
                price=product.price,
            )
        )

    return result


@app.post("/products", response_model=ProductResponse)
async def create_product(
    product_create: ProductCreate,
    user_service: Annotated[UserService, Depends(user_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await user_service.get_user(product_create.user_id)

    if not user:
        raise HTTPException(
            detail="user not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    product = Product(
        user_id=product_create.user_id,  # TODO: change to real user
        title=product_create.title,
        description=product_create.description,
        price=product_create.price,
    )

    db.add(product)
    await db.commit()
    await db.refresh(product)

    await send_product_created_event(
        {
            "title": product.title,
            "description": product.description,
            "price": float(product.price),
        }
    )

    return ProductResponse(
        id=product.id,
        user_id=product.user_id,
        title=product.title,
        description=product.description,
        price=product.price,
    )


@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    product = await db.scalar(
        select(Product).where(Product.id == product_id),
    )

    if not product:
        raise HTTPException(
            detail="product not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return ProductResponse(
        id=product.id,
        user_id=product.user_id,
        title=product.title,
        description=product.description,
        price=product.price,
    )


@app.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    user_id: int,
    product_update: ProductUpdate,
    user_service: Annotated[UserService, Depends(user_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await user_service.get_user(user_id)

    if not user:
        raise HTTPException(
            detail="user not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    product = await db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.user_id == user_id,
        ),
    )

    if not product or product.user_id != user.id:
        raise HTTPException(
            detail="product not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    old_product_snapshot = {
        "title": product.title,
        "description": product.description,
        "price": float(product.price),
    }

    update_dict = product_update.model_dump(exclude_unset=True)

    for k, v in update_dict.items():
        setattr(product, k, v)

    await db.commit()
    await db.refresh(product)

    await send_product_updated_event(
        old_product_snapshot,
        {
            "title": product.title,
            "description": product.description,
            "price": float(product.price),
        },
    )

    return ProductResponse(
        id=product.id,
        user_id=product.user_id,
        title=product.title,
        description=product.description,
        price=product.price,
    )
