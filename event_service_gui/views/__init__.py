"""Package for all views."""

from .activate import Activate
from .config import Config
from .contestants import Contestants
from .control import Control
from .corrections import Corrections
from .csv_list import CsvList
from .events import Events
from .live import Live
from .liveness import Ping, Ready
from .login import Login
from .logout import Logout
from .main import Main
from .photo_finish import PhotoFinish
from .photo_update import PhotoUpdate
from .photos import Photos
from .photos_edit import PhotosEdit
from .print_contestants import PrintContestants
from .print_dash import PrintDash
from .print_lists import PrintLists
from .raceclasses import Raceclasses
from .raceplans import Raceplans
from .resultat import Resultat
from .resultat_edit_new import ResultatEditNew
from .resultat_update import ResultatUpdate
from .seeding import Seeding
from .settings import Settings
from .start import Start
from .start_edit import StartEdit
from .system import System, SystemStatus
from .tasks import Tasks
from .td_report import TdReport
from .timing import Timing
from .timing_dash import TimingDash
from .timing_info import TimingInfo
from .users import Users
from .video_events import VideoEvents

__all__ = [
    "Activate",
    "Config",
    "Contestants",
    "Control",
    "Corrections",
    "CsvList",
    "Events",
    "Live",
    "Login",
    "Logout",
    "Main",
    "PhotoFinish",
    "PhotoUpdate",
    "Photos",
    "PhotosEdit",
    "Ping",
    "PrintContestants",
    "PrintDash",
    "PrintLists",
    "Raceclasses",
    "Raceplans",
    "Ready",
    "Resultat",
    "ResultatEditNew",
    "ResultatUpdate",
    "Seeding",
    "Settings",
    "Start",
    "StartEdit",
    "System",
    "SystemStatus",
    "Tasks",
    "TdReport",
    "Timing",
    "TimingDash",
    "TimingInfo",
    "Users",
    "VideoEvents",
]
