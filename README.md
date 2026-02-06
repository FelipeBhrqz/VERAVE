# VERAVE

VERAVE es una herramienta para comparar datos de votacion entre un PDF y un CSV consolidado.

## Requisitos

- Python 3.10+ (recomendado 3.11)

## Instalacion

En Windows PowerShell:

```powershell
cd C:\Users\FELIPE\repos\VERAVE
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecutar

```powershell
python main.py
```

## Verificar con archivos de ejemplo

En `data/examples/primera_vuelta/` tienes:

- `reporte_v1.pdf`
- `datos_completos_fase2.csv` (fase 2 fallida: total por candidato)
- `datos_completos_fase1.csv` (fase 1 fallida: F/M candidato)
- `datos_completos_fase3.csv` (fase 3 fallida: votos validos)
- `datos_completos_fase4.csv` (fase 4 fallida: blancos/nulos)

Pasos sugeridos:

1. Abre la app con `python main.py`.
2. Selecciona el PDF `data/examples/primera_vuelta/reporte_v1.pdf`.
3. Selecciona un CSV de la misma carpeta.
4. Observa en que fase se detiene la verificacion.

En `data/examples/segunda_vuleta/` tienes `reporte_v2.pdf` y `datos_completos.csv` para pruebas de segunda vuelta.

## Notas

- La fase 5 (total votos) se calcula con `VOTOS VALIDOS + (BLANCOS + NULOS)`.
- Si modificas un CSV, asegurate de mantener el formato de columnas y la columna `VUELTA`.
