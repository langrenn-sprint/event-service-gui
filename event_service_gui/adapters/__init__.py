"""Package for all services."""

from .competition_format_adapter import CompetitionFormatAdapter
from .contestants_adapter import ContestantsAdapter
from .events_adapter import EventsAdapter
from .raceclass_result_adapter import RaceclassResultsAdapter
from .raceclasses_adapter import RaceclassesAdapter
from .raceplans_adapter import RaceplansAdapter
from .service_health_adapter import ServiceHealthAdapter
from .start_adapter import StartAdapter
from .system_status_adapter import SystemStatusAdapter
from .time_events_adapter import TimeEventsAdapter
from .user_adapter import UserAdapter

__all__ = [
    "CompetitionFormatAdapter",
    "ContestantsAdapter",
    "EventsAdapter",
    "RaceclassResultsAdapter",
    "RaceclassesAdapter",
    "RaceplansAdapter",
    "ServiceHealthAdapter",
    "StartAdapter",
    "SystemStatusAdapter",
    "TimeEventsAdapter",
    "UserAdapter",
]
