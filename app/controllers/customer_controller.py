from fastapi import APIRouter, Depends, Query

from app.enums.permission import PermissionArea, PermissionLevel
from app.schemas.common import ApiResponse
from app.schemas.customer import CustomerCreate, CustomerItem, CustomerList, CustomerUpdate
from app.services.customer_service import CustomerService
from app.utils.dependencies import get_customer_service, require_permission


router = APIRouter(prefix="/customers", tags=["Customers"])

CUST_VIEW = Depends(require_permission(PermissionArea.customers, PermissionLevel.view))
CUST_EDIT = Depends(require_permission(PermissionArea.customers, PermissionLevel.edit))
CUST_FULL = Depends(require_permission(PermissionArea.customers, PermissionLevel.full))


@router.get("", response_model=ApiResponse[CustomerList], dependencies=[CUST_VIEW],
            summary="List customers (search and city filter, paginated)")
def list_customers(
    search: str | None = None,
    city: str | None = None,
    include_deleted: bool = False,
    limit: int = Query(10, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: CustomerService = Depends(get_customer_service),
):
    return ApiResponse(data=service.list_customers(search, city, include_deleted, limit, offset),
                       message="Customers fetched")


@router.get("/by-email", response_model=ApiResponse[CustomerItem], dependencies=[CUST_VIEW],
            summary="Find an active customer by email")
def get_customer_by_email(email: str, service: CustomerService = Depends(get_customer_service)):
    return ApiResponse(data=service.get_customer_by_email(email), message="Customer fetched")


@router.get("/{customer_id}", response_model=ApiResponse[CustomerItem], dependencies=[CUST_VIEW])
def get_customer(customer_id: int, service: CustomerService = Depends(get_customer_service)):
    return ApiResponse(data=service.get_customer(customer_id), message="Customer fetched")


@router.post("", response_model=ApiResponse[CustomerItem], status_code=201, dependencies=[CUST_EDIT])
def create_customer(body: CustomerCreate, service: CustomerService = Depends(get_customer_service)):
    return ApiResponse(data=service.create_customer(body), message="Customer created")


@router.put("/{customer_id}", response_model=ApiResponse[CustomerItem], dependencies=[CUST_EDIT],
            summary="Update a customer (omitted fields are kept)")
def update_customer(customer_id: int, body: CustomerUpdate,
                    service: CustomerService = Depends(get_customer_service)):
    return ApiResponse(data=service.update_customer(customer_id, body), message="Customer updated")


@router.delete("/{customer_id}", response_model=ApiResponse[None], dependencies=[CUST_FULL],
               summary="Soft-delete a customer")
def delete_customer(customer_id: int, service: CustomerService = Depends(get_customer_service)):
    service.delete_customer(customer_id)
    return ApiResponse(data=None, message="Customer deleted")


@router.post("/{customer_id}/restore", response_model=ApiResponse[CustomerItem], dependencies=[CUST_FULL])
def restore_customer(customer_id: int, service: CustomerService = Depends(get_customer_service)):
    return ApiResponse(data=service.restore_customer(customer_id), message="Customer restored")
