from src.config.settings import settings
from src.constants.enums import (
    InterventionReason, InterventionStatus, MatterType, ProcessStatus, RiskLevel,
    RunStatus, RunStepStatus, RunTrigger, StepAction, UserRole,
)


def meta() -> dict:
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "enums": {
            "user_roles": [item.value for item in UserRole],
            "matter_types": [item.value for item in MatterType],
            "process_statuses": [item.value for item in ProcessStatus],
            "step_actions": [item.value for item in StepAction],
            "run_statuses": [item.value for item in RunStatus],
            "run_triggers": [item.value for item in RunTrigger],
            "run_step_statuses": [item.value for item in RunStepStatus],
            "intervention_reasons": [item.value for item in InterventionReason],
            "intervention_statuses": [item.value for item in InterventionStatus],
            "risk_levels": [item.value for item in RiskLevel],
        },
    }
