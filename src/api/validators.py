"""
Fonctions de validation des entrées API.
"""
import re
from fastapi import HTTPException

_LICENCE_PATTERN = re.compile(r'^\d{5,7}$')
_CLUB_CODE_PATTERN = re.compile(r'^[A-Z]{1,3}\d{2,4}$')


def validate_licence(licence: str) -> str:
    """Valide et nettoie un numéro de licence."""
    licence = licence.strip()
    if not _LICENCE_PATTERN.match(licence):
        raise HTTPException(status_code=400, detail="Numéro de licence invalide (5 à 7 chiffres attendus)")
    return licence


def validate_club_code(code: str) -> str:
    """Valide et nettoie un code club."""
    code = code.strip().upper()
    if not _CLUB_CODE_PATTERN.match(code):
        raise HTTPException(status_code=400, detail="Code club invalide (ex: H004, BW023)")
    return code
