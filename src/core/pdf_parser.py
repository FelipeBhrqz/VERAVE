"""PDF parsing utilities for Electoral Auditor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import re

import pdfplumber


VUELTA_1_DATE = "09 DE FEBRERO DE 2025"
VUELTA_2_DATE = "13 DE ABRIL DE 2025"


@dataclass(frozen=True)
class EntityVotes:
    entidad: str
    total: int
    hombres: int
    mujeres: int


@dataclass(frozen=True)
class PdfParseResult:
    vuelta: int
    entidades: Dict[str, EntityVotes]


DEFAULT_PATTERN = re.compile(
    r"^(?P<entidad>[A-ZÁÉÍÓÚÜÑa-záéíóúüñ0-9/\s\+\-\.]+?)\s+"
    r"(?P<total>\d+)\s+[\d,.]+\s*%?\s+"
    r"(?P<hombres>\d+)\s+[\d,.]+\s*%?\s+"
    r"(?P<mujeres>\d+)\s+[\d,.]+\s*%?\s*$"
)


class PdfParseError(RuntimeError):
    pass


NON_VOTE_ENTITIES = {
    "ELECTORES",
    "ELECTORES PPL",
    "TOTAL ELECTORES + PPL",
    "JUNTAS",
    "JUNTAS PPL",
    "TOTAL JUNTAS + PPL",
    "JUNTAS ANULADAS",
    "SUFRAGANTES",
    "AUSENTISMO",
}

NON_VALID_ENTITIES = {
    "BLANCOS",
    "NULOS",
}


def _detect_vuelta(lines: List[str]) -> int:
    joined = "\n".join(lines[:30]).upper()
    if VUELTA_1_DATE in joined:
        return 1
    if VUELTA_2_DATE in joined:
        return 2
    raise PdfParseError(
        "No se pudo detectar la vuelta. Verifica la fecha en el PDF."
    )


def _normalize_entidad(entidad: str) -> str:
    return re.sub(r"\s+", " ", entidad).strip().upper()


def parse_pdf(
    pdf_path: str,
    pattern: re.Pattern[str] = DEFAULT_PATTERN,
) -> PdfParseResult:
    """Parse the PDF report and return detected vuelta and entity votes."""
    all_text: List[str] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text.append(text)
    except Exception as exc:  # pragma: no cover
        raise PdfParseError(f"Error leyendo PDF: {exc}") from exc

    raw_text = "\n".join(all_text)
    lines = raw_text.splitlines()
    vuelta = _detect_vuelta(lines)

    entidades: Dict[str, EntityVotes] = {}
    for line in lines:
        match = pattern.match(line.strip())
        if not match:
            continue
        entidad = _normalize_entidad(match.group("entidad"))
        total = int(match.group("total"))
        hombres = int(match.group("hombres"))
        mujeres = int(match.group("mujeres"))
        entidades[entidad] = EntityVotes(
            entidad=entidad,
            total=total,
            hombres=hombres,
            mujeres=mujeres,
        )

    if "VOTOS VALIDOS" not in entidades:
        votos_total = 0
        votos_hombres = 0
        votos_mujeres = 0
        for key, votes in entidades.items():
            if key in NON_VOTE_ENTITIES:
                continue
            if key in NON_VALID_ENTITIES:
                continue
            if key == "VOTOS VALIDOS":
                continue
            votos_total += votes.total
            votos_hombres += votes.hombres
            votos_mujeres += votes.mujeres

        if votos_total > 0:
            entidades["VOTOS VALIDOS"] = EntityVotes(
                entidad="VOTOS VALIDOS",
                total=votos_total,
                hombres=votos_hombres,
                mujeres=votos_mujeres,
            )

    if not entidades:
        raise PdfParseError("No se encontraron entidades en el PDF.")

    return PdfParseResult(vuelta=vuelta, entidades=entidades)
