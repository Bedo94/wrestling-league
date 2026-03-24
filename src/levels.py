LEVEL_LABELS = {
    1: "Principiante",
    2: "Base",
    3: "Intermedio",
    4: "Avanzato",
}

LABEL_TO_LEVEL = {label: level for level, label in LEVEL_LABELS.items()}


def get_level_label(level: int) -> str:
    return LEVEL_LABELS.get(level, f"Sconosciuto ({level})")


def get_level_labels() -> list[str]:
    return list(LABEL_TO_LEVEL.keys())


def get_level_from_label(label: str) -> int:
    return LABEL_TO_LEVEL[label]