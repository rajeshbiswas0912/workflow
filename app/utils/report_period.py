from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from zoneinfo import ZoneInfo

APP_TZ = ZoneInfo("Asia/Kolkata")


class ReportPeriod(str, Enum):
    LAST_6_MONTHS = "last_6_months"
    THIS_QUARTER = "this_quarter"
    LAST_12_MONTHS = "last_12_months"

    @property
    def label(self) -> str:
        return {
            ReportPeriod.LAST_6_MONTHS: "Last 6 months",
            ReportPeriod.THIS_QUARTER: "This quarter",
            ReportPeriod.LAST_12_MONTHS: "Last 12 months",
        }[self]


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date
    months: int


def resolve_period(period: ReportPeriod, today: date | None = None) -> DateRange:
    today = today or datetime.now(APP_TZ).date()
    if period is ReportPeriod.LAST_6_MONTHS:
        months = 6
    elif period is ReportPeriod.LAST_12_MONTHS:
        months = 12
    else:
        months = (today.month - 1) % 3 + 1
    index = today.year * 12 + (today.month - 1) - (months - 1)
    return DateRange(start=date(index // 12, index % 12 + 1, 1), end=today, months=months)
