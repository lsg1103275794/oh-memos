__version__ = "3.1.10"

import os


# numpy and scipy each bundle OpenBLAS, which commits a ~32 MB buffer per CPU thread
# when loaded (~350 MB apiece on a 12-thread Windows host). Nothing here runs heavy
# BLAS work, so default to one thread. A value set in the launching environment wins;
# one in .env is applied too late to take effect.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

from oh_memos.configs.mem_cube import GeneralMemCubeConfig
from oh_memos.configs.mem_os import MOSConfig
from oh_memos.configs.mem_scheduler import SchedulerConfigFactory
from oh_memos.mem_cube.general import GeneralMemCube
from oh_memos.mem_os.main import MOS
from oh_memos.mem_scheduler.general_scheduler import GeneralScheduler
from oh_memos.mem_scheduler.scheduler_factory import SchedulerFactory


__all__ = [
    "MOS",
    "GeneralMemCube",
    "GeneralMemCubeConfig",
    "GeneralScheduler",
    "MOSConfig",
    "SchedulerConfigFactory",
    "SchedulerFactory",
]
