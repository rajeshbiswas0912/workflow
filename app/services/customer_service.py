from sqlalchemy.orm import Session

from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerItem, CustomerList, CustomerUpdate
from app.utils.db_errors import db_errors
from app.utils.exceptions import NotFoundError


UPDATABLE = ("name", "email", "phone", "city", "address")


class CustomerService:
    def __init__(self, db: Session, repo: CustomerRepository):
        self._db = db
        self._repo = repo

    def list_customers(self, search: str | None, city: str | None, include_deleted: bool,
                       limit: int, offset: int) -> CustomerList:
        with db_errors(self._db):
            rows = self._repo.list_all(search, city, include_deleted, limit, offset)
        return CustomerList(
            items=[CustomerItem(**r) for r in rows],
            total=rows[0]["total_count"] if rows else 0,
            limit=limit,
            offset=offset,
        )

    def get_customer(self, customer_id: int, include_deleted: bool = False) -> CustomerItem:
        with db_errors(self._db):
            row = self._repo.get_by_id(customer_id, include_deleted)
        if row is None:
            raise NotFoundError(f"Customer with ID {customer_id} not found")
        return CustomerItem(**row)

    def get_customer_by_email(self, email: str) -> CustomerItem:
        with db_errors(self._db):
            row = self._repo.get_by_email(email)
        if row is None:
            raise NotFoundError("No customer with that email")
        return CustomerItem(**row)

    def create_customer(self, data: CustomerCreate) -> CustomerItem:
        with db_errors(self._db):
            new_id = self._repo.create(data.name, data.email, data.phone, data.city, data.address)
            self._db.commit()
        return self.get_customer(new_id)

    def update_customer(self, customer_id: int, data: CustomerUpdate) -> CustomerItem:
        with db_errors(self._db):
            current = self._repo.get_by_id(customer_id)
            if current is None:
                raise NotFoundError(f"Customer with ID {customer_id} not found")

            # sp_customer_update overwrites all five fields, so merge with the current values
            sent = data.model_fields_set
            merged = {f: getattr(data, f) if f in sent else current[f] for f in UPDATABLE}

            self._repo.update(customer_id, **merged)
            self._db.commit()
        return self.get_customer(customer_id)

    def delete_customer(self, customer_id: int) -> None:
        with db_errors(self._db):
            self._repo.delete(customer_id)
            self._db.commit()

    def restore_customer(self, customer_id: int) -> CustomerItem:
        with db_errors(self._db):
            self._repo.restore(customer_id)
            self._db.commit()
        return self.get_customer(customer_id)
