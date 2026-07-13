# Notebooks

Carpeta reservada para el análisis exploratorio de los datasets cargados en
`odemiro_db` (ver `docs/data_dictionary.md`), siguiendo la convención sugerida:

- `01_EDA_exploracion_datos.ipynb`
- `02_limpieza_transformacion.ipynb`
- `03_analisis_descriptivo.ipynb`
- `04_modelo_predictivo.ipynb`
- `05_reportes_automaticos.ipynb`

**Estado actual:** vacía. El proyecto no incluye todavía un EDA formal en
notebook — el análisis exploratorio, si existió, se hizo ad-hoc para diseñar
el esquema en `scripts/init-sql/create_schema.sql`. Se recomienda al menos un
`01_EDA_exploracion_datos.ipynb` antes de la entrega final, dado que el jurado
técnico probablemente valore evidencia reproducible del análisis de datos
(distribución de matriculados por área, tasas de deserción por estrato, etc.)
más allá del pipeline productivo.
