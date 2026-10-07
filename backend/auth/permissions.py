import logging
from typing import List, Set, Dict
from fastapi import HTTPException, status
from backend.auth.schemas import UserRole

logger = logging.getLogger(__name__)


# Standard permissions defined for the platform
class Permission:
    READ_PUBLIC = "read:public"
    EXECUTE_RESEARCH = "execute:research"
    RUN_VALIDATION = "run:validation"
    RESOLVE_ENTITIES = "resolve:entities"
    MANAGE_REVIEWS = "manage:reviews"
    EXECUTE_MERGE = "execute:merge"
    MANAGE_USERS = "manage:users"
    VIEW_SECURITY_AUDITS = "view:security_audits"


# Role to Permissions Mapping Matrix
ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
    UserRole.ADMIN: {
        Permission.READ_PUBLIC,
        Permission.EXECUTE_RESEARCH,
        Permission.RUN_VALIDATION,
        Permission.RESOLVE_ENTITIES,
        Permission.MANAGE_REVIEWS,
        Permission.EXECUTE_MERGE,
        Permission.MANAGE_USERS,
        Permission.VIEW_SECURITY_AUDITS,
    },
    UserRole.RESEARCHER: {
        Permission.READ_PUBLIC,
        Permission.EXECUTE_RESEARCH,
        Permission.RUN_VALIDATION,
        Permission.RESOLVE_ENTITIES,
    },
    UserRole.REVIEWER: {
        Permission.READ_PUBLIC,
        Permission.RUN_VALIDATION,
        Permission.RESOLVE_ENTITIES,
        Permission.MANAGE_REVIEWS,
    },
    UserRole.READ_ONLY: {
        Permission.READ_PUBLIC,
    },
}


def check_role_permission(user_role: UserRole, required_permission: str) -> bool:
    """Evaluates if given UserRole possesses required permission."""
    permissions = ROLE_PERMISSIONS.get(user_role, set())
    return required_permission in permissions
