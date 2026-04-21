from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass


DEADLINES_SEC = {
    "CRITICAL": 30,
    "URGENT": 60,
    "STANDARD": 90,
}

PRIORITY_ORDER = {
    "CRITICAL": 0,
    "URGENT": 1,
    "STANDARD": 2,
}


@dataclass
class MedicationTask:
    task_id: str
    patient_service: str
    medication_name: str
    priority: str
    created_at: float
    deadline_at: float
    estimated_exec_sec: int

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(payload: str) -> "MedicationTask":
        raw = json.loads(payload)
        return MedicationTask(**raw)

    @staticmethod
    def new_random(priority: str, patient_service: str, medication_name: str, estimated_exec_sec: int) -> "MedicationTask":
        now = time.time()
        return MedicationTask(
            task_id=str(uuid.uuid4())[:8],
            patient_service=patient_service,
            medication_name=medication_name,
            priority=priority,
            created_at=now,
            deadline_at=now + DEADLINES_SEC[priority],
            estimated_exec_sec=estimated_exec_sec,
        )
