from src.constants.enums import UserRole

ROLE_LABELS = {
    UserRole.ADMIN.value: "平台管理员",
    UserRole.ENGINEER.value: "值守操作员",
    UserRole.VIEWER.value: "审计只读",
}

ROLE_PERMISSIONS = {
    UserRole.ADMIN.value: [
        "process:read", "process:edit", "process:publish", "process:archive",
        "run:read", "run:execute", "run:cancel", "run:dry_run",
        "intervention:read", "intervention:resolve",
        "material:read", "material:write",
        "report:export", "audit:read",
    ],
    UserRole.ENGINEER.value: [
        "process:read", "process:edit",
        "run:read", "run:execute", "run:cancel", "run:dry_run",
        "intervention:read", "intervention:resolve",
        "material:read", "report:export",
    ],
    UserRole.VIEWER.value: [
        "process:read", "run:read", "intervention:read", "material:read", "report:export",
    ],
}
