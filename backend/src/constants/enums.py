from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"


class MatterType(str, Enum):
    ANNUAL_REPORT = "annual_report"
    QUALIFICATION = "qualification"
    SUBSIDY = "subsidy"
    CHANGE = "change"


class ProcessStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StepAction(str, Enum):
    CLICK = "click"
    INPUT = "input"
    UPLOAD = "upload"
    ASSERT = "assert"
    WAIT = "wait"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TAKEOVER = "takeover"


class RunTrigger(str, Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    DRY_RUN = "dry_run"


class RunStepStatus(str, Enum):
    OK = "ok"
    RETRIED = "retried"
    FAILED = "failed"
    SKIPPED = "skipped"


class InterventionReason(str, Enum):
    ASSERT_FAILED = "assert_failed"
    LOCATOR_DRIFT = "locator_drift"
    TIMEOUT = "timeout"
    MANUAL = "manual"


class InterventionStatus(str, Enum):
    OPEN = "open"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    ABORTED = "aborted"
    RESOLVED = "resolved"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ErrorCode(str, Enum):
    E_TIMEOUT = "E_TIMEOUT"
    E_ASSERT_FAILED = "E_ASSERT_FAILED"
    E_LOCATOR_MISS = "E_LOCATOR_MISS"
    E_CREDIT_INVALID = "E_CREDIT_INVALID"
    E_CONCURRENCY_CONFLICT = "E_CONCURRENCY_CONFLICT"
    E_STEP_FAILED = "E_STEP_FAILED"


ACTIVE_RUN_STATUSES = (RunStatus.QUEUED.value, RunStatus.RUNNING.value, RunStatus.TAKEOVER.value)
