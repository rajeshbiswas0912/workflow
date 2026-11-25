from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from app.config.settings import settings
from app.enums.permission import PermissionArea, PermissionLevel
from app.schemas.common import ApiResponse
from app.schemas.product import ProductCategory, ProductCreate, ProductItem, ProductList, ProductStats, ProductStatusUpdate, ProductStockAdjust, ProductStockSet, ProductUpdate
from app.services.product_service import ProductService
from app.utils.dependencies import get_product_service, require_permission


router = APIRouter(prefix="/products", tags=["Products"])

PROD_VIEW = Depends(require_permission(PermissionArea.products, PermissionLevel.view))
PROD_EDIT = Depends(require_permission(PermissionArea.products, PermissionLevel.edit))
PROD_FULL = Depends(require_permission(PermissionArea.products, PermissionLevel.full))


@router.get("", response_model=ApiResponse[ProductList], dependencies=[PROD_VIEW],
            summary="List products (search, status, price range, in-stock filters)")
def list_products(
    search: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    min_price: Decimal | None = Query(None, ge=0),
    max_price: Decimal | None = Query(None, ge=0),
    in_stock_only: bool = False,
    include_deleted: bool = False,
    limit: int = Query(8, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: ProductService = Depends(get_product_service),
):
    return ApiResponse(
        data=service.list_products(search, category, is_active, min_price, max_price, in_stock_only,
                                   include_deleted, limit, offset),
        message="Products fetched",
    )


@router.get("/summary", response_model=ApiResponse[ProductStats], dependencies=[PROD_VIEW],
            summary="Numbers for the stat cards")
def product_stats(
    low_stock_threshold: int = Query(settings.LOW_STOCK_THRESHOLD, ge=1, le=1_000_000),
    service: ProductService = Depends(get_product_service),
):
    return ApiResponse(data=service.stats(low_stock_threshold), message="Summary fetched")


@router.get("/by-sku", response_model=ApiResponse[ProductItem], dependencies=[PROD_VIEW],
            summary="Find an active product by SKU")
def get_product_by_sku(sku: str, service: ProductService = Depends(get_product_service)):
    return ApiResponse(data=service.get_product_by_sku(sku), message="Product fetched")


@router.get("/categories", response_model=ApiResponse[list[ProductCategory]], dependencies=[PROD_VIEW],
            summary="Categories in use (for the dropdown and filter)")
def list_categories(service: ProductService = Depends(get_product_service)):
    return ApiResponse(data=service.list_categories(), message="Categories fetched")


@router.get("/{product_id}", response_model=ApiResponse[ProductItem], dependencies=[PROD_VIEW])
def get_product(product_id: int, service: ProductService = Depends(get_product_service)):
    return ApiResponse(data=service.get_product(product_id), message="Product fetched")


@router.post("", response_model=ApiResponse[ProductItem], status_code=201, dependencies=[PROD_EDIT])
def create_product(body: ProductCreate, service: ProductService = Depends(get_product_service)):
    return ApiResponse(data=service.create_product(body), message="Product created")


@router.put("/{product_id}", response_model=ApiResponse[ProductItem], dependencies=[PROD_EDIT],
            summary="Update a product (omitted fields are kept)")
def update_product(product_id: int, body: ProductUpdate,
                   service: ProductService = Depends(get_product_service)):
    return ApiResponse(data=service.update_product(product_id, body), message="Product updated")


@router.patch("/{product_id}/status", response_model=ApiResponse[ProductItem], dependencies=[PROD_EDIT],
              summary="Mark a product active or discontinued")
def set_product_status(product_id: int, body: ProductStatusUpdate,
                       service: ProductService = Depends(get_product_service)):
    return ApiResponse(data=service.set_active(product_id, body.is_active), message="Status updated")


@router.put("/{product_id}/stock", response_model=ApiResponse[ProductItem], dependencies=[PROD_EDIT],
            summary="Set the exact stock quantity (e.g. after a stock count)")
def set_product_stock(product_id: int, body: ProductStockSet,
                      service: ProductService = Depends(get_product_service)):
    return ApiResponse(data=service.set_stock(product_id, body.stock_quantity), message="Stock updated")


@router.post("/{product_id}/stock/adjust", response_model=ApiResponse[ProductItem], dependencies=[PROD_EDIT],
             summary="Add or remove units (+10 restock, -3 removal). Never goes below zero")
def adjust_product_stock(product_id: int, body: ProductStockAdjust,
                         service: ProductService = Depends(get_product_service)):
    return ApiResponse(data=service.adjust_stock(product_id, body.delta), message="Stock adjusted")


@router.delete("/{product_id}", response_model=ApiResponse[None], dependencies=[PROD_FULL],
               summary="Soft-delete a product")
def delete_product(product_id: int, service: ProductService = Depends(get_product_service)):
    service.delete_product(product_id)
    return ApiResponse(data=None, message="Product deleted")


@router.post("/{product_id}/restore", response_model=ApiResponse[ProductItem], dependencies=[PROD_FULL])
def restore_product(product_id: int, service: ProductService = Depends(get_product_service)):
    return ApiResponse(data=service.restore_product(product_id), message="Product restored")
