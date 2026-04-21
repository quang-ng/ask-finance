from typing import Any

ROLE_PERMISSIONS: dict[str, dict[str, Any]] = {
    "analyst": {
        "allowed_bus": None,        # set at runtime from user_bu
        "allowed_regions": None,    # set at runtime from user_region
        "allowed_reports": ["PNL", "OPEX"],
    },
    "bu_gm": {
        "allowed_bus": None,        # set at runtime from user_bu
        "allowed_regions": ["*"],   # all regions
        "allowed_reports": ["PNL", "OPEX", "ROI"],
    },
    "group_cfo": {
        "allowed_bus": ["*"],       # all BUs
        "allowed_regions": ["*"],   # all regions
        "allowed_reports": ["PNL", "OPEX", "ROI"],
    },
}


def get_permissions(role: str, user_bu: str, user_region: str) -> dict[str, Any]:
    perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["analyst"]).copy()

    if perms["allowed_bus"] is None:
        perms["allowed_bus"] = [user_bu]
    if perms["allowed_regions"] is None:
        perms["allowed_regions"] = [user_region]

    return perms


def is_data_type_allowed(role: str, data_type: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["analyst"])
    return data_type.upper() in perms["allowed_reports"]
