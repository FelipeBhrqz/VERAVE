"""Comparison utilities for Electoral Auditor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .csv_loader import CsvLoadResult
from .pdf_parser import EntityVotes, PdfParseResult, NON_VOTE_ENTITIES


def _normalize(text: str) -> str:
    return " ".join(str(text).strip().upper().split())


def _candidate_diffs(
    pdf_map: Dict[str, EntityVotes],
    csv_map: Dict[str, EntityVotes],
    limit: int = 5,
) -> List[str]:
    diffs: List[str] = []
    skip = {"BLANCOS", "NULOS", "VOTOS VALIDOS", "SUFRAGANTES"}
    for key, csv_votes in csv_map.items():
        norm_key = _normalize(key)
        if norm_key in NON_VOTE_ENTITIES or norm_key in skip:
            continue
        pdf_votes = pdf_map.get(norm_key)
        if not pdf_votes:
            continue
        if (
            pdf_votes.total != csv_votes.total
            or pdf_votes.hombres != csv_votes.hombres
            or pdf_votes.mujeres != csv_votes.mujeres
        ):
            diffs.append(
                f"{norm_key} (T {pdf_votes.total}->{csv_votes.total}, "
                f"H {pdf_votes.hombres}->{csv_votes.hombres}, "
                f"M {pdf_votes.mujeres}->{csv_votes.mujeres})"
            )
            if len(diffs) >= limit:
                break
    return diffs


@dataclass(frozen=True)
class ComparisonItem:
    entidad: str
    ok: bool
    pdf: EntityVotes | None
    csv: EntityVotes | None
    message: str
    phase: int | None = None
    is_header: bool = False


@dataclass(frozen=True)
class ComparisonResult:
    items: List[ComparisonItem]
    halted: bool
    halt_reason: str | None


def _select_csv_map(pdf_entities: Dict[str, EntityVotes], csv_result: CsvLoadResult) -> Dict[str, EntityVotes]:
    if not csv_result.entidades_por_provincia:
        return csv_result.entidades

    pdf_keys = {_normalize(key) for key in pdf_entities.keys()}
    provincia_keys = set(csv_result.entidades_por_provincia.keys())

    if pdf_keys.intersection(provincia_keys):
        return csv_result.entidades_por_provincia

    return csv_result.entidades


def compare_results(pdf_result: PdfParseResult, csv_result: CsvLoadResult) -> ComparisonResult:
    csv_map = _select_csv_map(pdf_result.entidades, csv_result)

    items: List[ComparisonItem] = []

    pdf_map = {_normalize(key): value for key, value in pdf_result.entidades.items()}

    def halt(message: str) -> ComparisonResult:
        items.append(ComparisonItem(entidad="CONTROL", ok=False, pdf=None, csv=None, message=message))
        return ComparisonResult(items=items, halted=True, halt_reason=message)

    def add_phase_header(phase: int, title: str) -> None:
        items.append(
            ComparisonItem(
                entidad="FASE",
                ok=True,
                pdf=None,
                csv=None,
                message="=" * 40,
                phase=phase,
                is_header=True,
            )
        )
        items.append(
            ComparisonItem(
                entidad="FASE",
                ok=True,
                pdf=None,
                csv=None,
                message=f"Fase {phase}: {title}",
                phase=phase,
                is_header=True,
            )
        )

    # 1) Femenino y Masculino
    add_phase_header(1, "Femenino y Masculino")
    # Skip non-candidate aggregates; these are validated in later phases.
    skip_fm = {_normalize("SUFRAGANTES"), _normalize("VOTOS VALIDOS"), _normalize("BLANCOS"), _normalize("NULOS")}
    skip_fm.update({_normalize(key) for key in NON_VOTE_ENTITIES})
    for key, csv_votes in csv_map.items():
        if _normalize(key) in skip_fm:
            continue
        pdf_votes = pdf_map.get(_normalize(key))
        if not pdf_votes:
            return halt(f"❌ {key}: No existe en el PDF (fase 1: F/M).")

        if pdf_votes.hombres != csv_votes.hombres or pdf_votes.mujeres != csv_votes.mujeres:
            return halt(
                "❌ "
                f"{key}: Discrepancia en F/M. "
                f"PDF: H={pdf_votes.hombres}, M={pdf_votes.mujeres}. "
                f"CSV: H={csv_votes.hombres}, M={csv_votes.mujeres}."
            )

        items.append(
            ComparisonItem(
                entidad=key,
                ok=True,
                pdf=pdf_votes,
                csv=csv_votes,
                message=f"✅ {key}: F/M coinciden.",
            )
        )

    # 2) Totales por candidato/blanco/nulo
    add_phase_header(2, "Totales por candidato/blanco/nulo")
    skip_totals = {_normalize("VOTOS VALIDOS"), _normalize("SUFRAGANTES")}
    for key, csv_votes in csv_map.items():
        norm_key = _normalize(key)
        if norm_key in skip_totals:
            continue
        if norm_key in NON_VOTE_ENTITIES:
            continue

        pdf_votes = pdf_map.get(norm_key)
        if not pdf_votes:
            return halt(f"❌ {key}: No existe en el PDF (fase 2: Totales).")

        if pdf_votes.total != csv_votes.total:
            return halt(
                "❌ "
                f"{key}: Discrepancia en Total. "
                f"PDF: T={pdf_votes.total}. CSV: T={csv_votes.total}."
            )

        items.append(
            ComparisonItem(
                entidad=key,
                ok=True,
                pdf=pdf_votes,
                csv=csv_votes,
                message=f"✅ {key}: Total coincide.",
            )
        )

    # 3) Validos
    add_phase_header(3, "Votos validos")
    valid_key = _normalize("VOTOS VALIDOS")
    pdf_valid = pdf_map.get(valid_key)
    csv_valid = csv_map.get(valid_key)
    if not pdf_valid or not csv_valid:
        return halt("❌ VOTOS VALIDOS: No existe en PDF o CSV (fase 3).")

    if (
        pdf_valid.total != csv_valid.total
        or pdf_valid.hombres != csv_valid.hombres
        or pdf_valid.mujeres != csv_valid.mujeres
    ):
        diffs = _candidate_diffs(pdf_map, csv_map)
        hint = (
            " Posibles diferencias en candidatos: " + "; ".join(diffs)
            if diffs
            else " No se encontraron diferencias por candidato."
        )
        return halt(
            "❌ VOTOS VALIDOS: Discrepancia detectada. "
            f"PDF: T={pdf_valid.total}, H={pdf_valid.hombres}, M={pdf_valid.mujeres}. "
            f"CSV: T={csv_valid.total}, H={csv_valid.hombres}, M={csv_valid.mujeres}."
            f"{hint}"
        )

    items.append(
        ComparisonItem(
            entidad="VOTOS VALIDOS",
            ok=True,
            pdf=pdf_valid,
            csv=csv_valid,
            message="✅ VOTOS VALIDOS: Coinciden.",
        )
    )

    for label in ("BLANCOS", "NULOS"):
        pdf_item = pdf_map.get(label)
        csv_item = csv_map.get(label)
        if not pdf_item or not csv_item:
            return halt(f"❌ {label}: No existe en PDF o CSV (fase 3).")
        if (
            pdf_item.total != csv_item.total
            or pdf_item.hombres != csv_item.hombres
            or pdf_item.mujeres != csv_item.mujeres
        ):
            return halt(
                f"❌ {label}: Discrepancia detectada. "
                f"PDF: T={pdf_item.total}, H={pdf_item.hombres}, M={pdf_item.mujeres}. "
                f"CSV: T={csv_item.total}, H={csv_item.hombres}, M={csv_item.mujeres}."
            )

        items.append(
            ComparisonItem(
                entidad=label,
                ok=True,
                pdf=pdf_item,
                csv=csv_item,
                message=f"✅ {label}: Coinciden.",
            )
        )

    # 4) Invalidos (blancos + nulos)
    add_phase_header(4, "Invalidos (blancos + nulos)")
    invalid_keys = {"BLANCOS", "NULOS"}
    missing_invalid = [key for key in invalid_keys if key not in csv_map or key not in pdf_map]
    if missing_invalid:
        return halt("❌ Invalidos: Faltan BLANCOS o NULOS en PDF/CSV (fase 4).")

    pdf_invalid_total = sum(pdf_map[key].total for key in invalid_keys)
    pdf_invalid_h = sum(pdf_map[key].hombres for key in invalid_keys)
    pdf_invalid_m = sum(pdf_map[key].mujeres for key in invalid_keys)

    csv_invalid_total = sum(csv_map[key].total for key in invalid_keys)
    csv_invalid_h = sum(csv_map[key].hombres for key in invalid_keys)
    csv_invalid_m = sum(csv_map[key].mujeres for key in invalid_keys)

    if (pdf_invalid_total, pdf_invalid_h, pdf_invalid_m) != (csv_invalid_total, csv_invalid_h, csv_invalid_m):
        return halt(
            "❌ INVALIDOS (BLANCOS+NULOS): Discrepancia detectada. "
            f"PDF: T={pdf_invalid_total}, H={pdf_invalid_h}, M={pdf_invalid_m}. "
            f"CSV: T={csv_invalid_total}, H={csv_invalid_h}, M={csv_invalid_m}."
        )

    items.append(
        ComparisonItem(
            entidad="INVALIDOS",
            ok=True,
            pdf=EntityVotes("INVALIDOS", pdf_invalid_total, pdf_invalid_h, pdf_invalid_m),
            csv=EntityVotes("INVALIDOS", csv_invalid_total, csv_invalid_h, csv_invalid_m),
            message="✅ INVALIDOS: Coinciden.",
        )
    )

    # 5) Total votos totales (validos + invalidos)
    add_phase_header(5, "Total votos (validos + invalidos)")
    total_pdf = EntityVotes(
        "TOTAL VOTOS",
        pdf_valid.total + pdf_invalid_total,
        pdf_valid.hombres + pdf_invalid_h,
        pdf_valid.mujeres + pdf_invalid_m,
    )
    total_csv = EntityVotes(
        "TOTAL VOTOS",
        csv_valid.total + csv_invalid_total,
        csv_valid.hombres + csv_invalid_h,
        csv_valid.mujeres + csv_invalid_m,
    )
    if (
        total_pdf.total != total_csv.total
        or total_pdf.hombres != total_csv.hombres
        or total_pdf.mujeres != total_csv.mujeres
    ):
        return halt(
            "❌ TOTAL VOTOS: Discrepancia detectada. "
            f"PDF: T={total_pdf.total}, H={total_pdf.hombres}, M={total_pdf.mujeres}. "
            f"CSV: T={total_csv.total}, H={total_csv.hombres}, M={total_csv.mujeres}."
        )

    items.append(
        ComparisonItem(
            entidad="TOTAL VOTOS",
            ok=True,
            pdf=total_pdf,
            csv=total_csv,
            message="✅ TOTAL VOTOS: Coinciden.",
        )
    )

    return ComparisonResult(items=items, halted=False, halt_reason=None)
