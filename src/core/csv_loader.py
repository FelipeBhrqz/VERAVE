"""CSV loading and transformation for Electoral Auditor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple
import re

import pandas as pd

from .pdf_parser import EntityVotes


VARIABLE_PATTERN = re.compile(r"^(?P<name>.+)_(?P<sexo>[FMT])$")


@dataclass(frozen=True)
class CsvLoadResult:
    vuelta: int
    entidades: Dict[str, EntityVotes]
    entidades_por_provincia: Dict[str, EntityVotes]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().upper()


def _split_variable(variable: str) -> Tuple[str, str] | None:
    match = VARIABLE_PATTERN.match(variable.strip())
    if not match:
        return None
    return match.group("name"), match.group("sexo")


def load_csv(csv_path: str, vuelta: int) -> CsvLoadResult:
    """Load and transform consolidated CSV data.

    Args:
        csv_path: Path to CSV file.
        vuelta: Detected vuelta from PDF.

    Returns:
        CsvLoadResult with aggregated values.
    """
    df = pd.read_csv(csv_path)
    if "VUELTA" not in df.columns:
        raise ValueError("El CSV no contiene la columna VUELTA.")

    df = df[df["VUELTA"] == vuelta].copy()
    if df.empty:
        raise ValueError(f"No hay datos para la vuelta {vuelta} en el CSV.")

    df["VARIABLE"] = df["VARIABLE"].astype(str).str.strip()
    df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce").fillna(0).astype(int)

    extracted = df["VARIABLE"].apply(_split_variable)
    df["BASE"] = extracted.apply(lambda x: x[0] if x else None)
    df["SEXO"] = extracted.apply(lambda x: x[1] if x else None)

    df = df.dropna(subset=["BASE", "SEXO"])

    entidades: Dict[str, EntityVotes] = {}
    aggregated = df.groupby(["BASE", "SEXO"])["VALUE"].sum().unstack(fill_value=0)
    for base, row in aggregated.iterrows():
        entidad = _normalize(base)
        mujeres = int(row.get("F", 0))
        hombres = int(row.get("M", 0))
        total = int(row.get("T", mujeres + hombres))
        entidades[entidad] = EntityVotes(entidad=entidad, total=total, hombres=hombres, mujeres=mujeres)

    entidades_por_provincia: Dict[str, EntityVotes] = {}
    if "PROVINCIA_NOMBRE" in df.columns:
        aggregated_p = (
            df.groupby(["PROVINCIA_NOMBRE", "BASE", "SEXO"])["VALUE"].sum().unstack(fill_value=0)
        )
        for (provincia, base), row in aggregated_p.iterrows():
            key = _normalize(f"{provincia} - {base}")
            mujeres = int(row.get("F", 0))
            hombres = int(row.get("M", 0))
            total = int(row.get("T", mujeres + hombres))
            entidades_por_provincia[key] = EntityVotes(
                entidad=key,
                total=total,
                hombres=hombres,
                mujeres=mujeres,
            )

    return CsvLoadResult(vuelta=vuelta, entidades=entidades, entidades_por_provincia=entidades_por_provincia)
