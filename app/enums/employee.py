import enum

class EmployeeStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"

    @property
    def label(self) -> str:
        labels = {
            EmployeeStatus.ACTIVE: "Active",
            EmployeeStatus.INACTIVE: "Inactive",
            EmployeeStatus.ON_LEAVE: "On Leave",
        }
        return labels[self]
