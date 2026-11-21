from enum import Enum

class PermissionArea(str, Enum):
    employees = "employees"
    departments = "departments"
    customers = "customers"
    products = "products"
    orders = "orders"
    reports = "reports"
    settings = "settings"

class PermissionLevel(str, Enum):
    none = "none"
    view = "view"
    edit = "edit"
    full = "full"

LEVEL_RANK = {PermissionLevel.none: 0, PermissionLevel.view: 1,
              PermissionLevel.edit: 2, PermissionLevel.full: 3}
