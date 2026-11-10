"""Package for all adapters."""

from .competition_format_adapter import CompetitionFormatAdapter
from .config_adapter import ConfigAdapter
from .contestants_adapter import ContestantsAdapter
from .events_adapter import EventsAdapter
from .ids import require_id
from .photos_adapter import PhotosAdapter
from .raceclass_result_adapter import RaceclassResultsAdapter
from .raceclasses_adapter import RaceclassesAdapter
from .raceplans_adapter import RaceplansAdapter
from .result_adapter import ResultAdapter
from .service_health_adapter import ServiceHealthAdapter
from .start_adapter import StartAdapter
from .status_adapter import StatusAdapter
from .system_status_adapter import SystemStatusAdapter
from .time_events_adapter import TimeEventsAdapter
from .user_adapter import UserAdapter

__all__ = [
    "CompetitionFormatAdapter",
    "ConfigAdapter",
    "ContestantsAdapter",
    "EventsAdapter",
    "PhotosAdapter",
    "RaceclassResultsAdapter",
    "RaceclassesAdapter",
    "RaceplansAdapter",
    "ResultAdapter",
    "ServiceHealthAdapter",
    "StartAdapter",
    "StatusAdapter",
    "SystemStatusAdapter",
    "TimeEventsAdapter",
    "UserAdapter",
    "require_id",
]
