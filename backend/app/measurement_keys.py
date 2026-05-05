"""Allowed keys for body measurement logs (cm). Shared by API validation."""

MEASUREMENT_KEYS: frozenset[str] = frozenset(
    {
        "neck",
        "shoulders",
        "chest",
        "waist",
        "navel",
        "hips",
        "bicep_l",
        "bicep_r",
        "forearm_l",
        "forearm_r",
        "thigh_l",
        "thigh_r",
        "calf_l",
        "calf_r",
    }
)
