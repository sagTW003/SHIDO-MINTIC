"""
Consolida el CSV crudo de la GEIH (DANE) en dos tablas agregadas dentro de
odemiro_db, para que Ada/Lumina puedan responder sobre mercado laboral real
(ingresos, informalidad) por departamento y sector economico.

El CSV crudo (~400MB, ~3.7M registros de personas) NO se versiona en el repo
(supera el limite practico de GitHub y el patron de dumps livianos que ya
sigue este proyecto para SNIES/desercion). Este script lo agrega -ponderando
por FACTOR_EXPANSION, como corresponde a una encuesta de hogares muestral,
NO un censo- en dos tablas pequenas (miles de filas, no millones) que si se
cargan a odemiro_db y quedan incluidas en el dump versionado
(scripts/init-sql/data/odemiro_db.sql.gz).

Uso:
    python3 scripts/consolidar_geih.py [--input RUTA_CSV]

Por defecto busca el CSV en data/raw/GEIH_consolidado_2022_2026.csv; si no
existe ahi, hay que pasar --input con la ruta real (p.ej. la carpeta de
Descargas donde DANE/el usuario dejo el consolidado).

Tablas creadas:
- geih_departamento_resumen: panorama laboral general por departamento
  (poblacion ocupada/desocupada estimada, tasa de desempleo, ingreso
  mediano, % informalidad).
- geih_sector_departamento: lo mismo pero cruzado por sector economico
  (SECTOR_CIIU_2D), para poder responder "cuanto se gana / que tan informal
  es el sector afin a tu carrera, en tu departamento".
"""
import argparse
import os
import sys

import mysql.connector
import numpy as np
import pandas as pd

# ================================================================
#   CONFIG
# ================================================================

def _cargar_env():
    aqui = os.path.dirname(os.path.abspath(__file__))
    raiz = os.path.dirname(aqui)  # .../SHIDO_MINTIC (scripts/ esta un nivel abajo de la raiz)
    ruta_env = os.path.join(raiz, ".env")
    if not os.path.exists(ruta_env):
        return
    with open(ruta_env, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            if clave and clave not in os.environ:
                os.environ[clave] = valor


_cargar_env()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "odemiro"),
    "password": os.getenv("DB_PASS", "odemiro_pass_2026"),
    "database": os.getenv("DB_NAME", "odemiro_db"),
}

RUTA_DEFECTO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "raw", "GEIH_consolidado_2022_2026.csv",
)

# Codigo DANE de departamento -> nombre, EXACTO como aparece en
# snies_matriculados.departamento_de_oferta_del_programa (verificado por
# consulta directa a la BD), para que el join por texto sea consistente si
# se necesita ademas del join por codigo numerico.
DPTO_NOMBRE = {
    5: "ANTIOQUIA", 8: "ATLÁNTICO", 11: "BOGOTÁ D.C.", 13: "BOLÍVAR",
    15: "BOYACÁ", 17: "CALDAS", 18: "CAQUETÁ", 19: "CAUCA", 20: "CESAR",
    23: "CÓRDOBA", 25: "CUNDINAMARCA", 27: "CHOCÓ", 41: "HUILA",
    44: "LA GUAJIRA", 47: "MAGDALENA", 50: "META", 52: "NARIÑO",
    54: "NORTE DE SANTANDER", 63: "QUINDÍO", 66: "RISARALDA",
    68: "SANTANDER", 70: "SUCRE", 73: "TOLIMA", 76: "VALLE DEL CAUCA",
    81: "ARAUCA", 85: "CASANARE", 86: "PUTUMAYO",
    88: "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA",
    91: "AMAZONAS", 94: "GUAINÍA", 95: "GUAVIARE", 97: "VAUPÉS", 99: "VICHADA",
}

# CIIU Rev.4 A.C. -- division a 2 digitos -> nombre del sector (clasificacion
# estandar DANE/CIIU, publica). Solo se listan las que realmente aparecen en
# la GEIH; 0 se deja como "Sin clasificar" (codigo residual del CSV).
CIIU_NOMBRE = {
    0: "Sin clasificar", 1: "Agricultura y ganadería", 2: "Silvicultura",
    3: "Pesca y acuicultura", 5: "Extracción de carbón", 6: "Extracción de petróleo y gas",
    7: "Extracción de minerales metálicos", 8: "Extracción de otras minas y canteras",
    9: "Actividades de apoyo a la minería", 10: "Elaboración de alimentos",
    11: "Elaboración de bebidas", 12: "Elaboración de productos de tabaco",
    13: "Fabricación de productos textiles", 14: "Confección de prendas de vestir",
    15: "Curtido y fabricación de calzado", 16: "Transformación de la madera",
    17: "Fabricación de papel", 18: "Impresión y reproducción de grabaciones",
    19: "Refinación de petróleo", 20: "Fabricación de sustancias químicas",
    21: "Fabricación de productos farmacéuticos", 22: "Fabricación de caucho y plástico",
    23: "Fabricación de minerales no metálicos", 24: "Industrias metalúrgicas básicas",
    25: "Fabricación de productos elaborados de metal", 26: "Fabricación de productos electrónicos",
    27: "Fabricación de equipo eléctrico", 28: "Fabricación de maquinaria y equipo",
    29: "Fabricación de vehículos automotores", 30: "Fabricación de otros equipos de transporte",
    31: "Fabricación de muebles", 32: "Otras industrias manufactureras",
    33: "Instalación y reparación de maquinaria", 35: "Suministro de electricidad y gas",
    36: "Captación y tratamiento de agua", 37: "Alcantarillado",
    38: "Recolección y tratamiento de desechos", 39: "Actividades de saneamiento ambiental",
    41: "Construcción de edificios", 42: "Obras de ingeniería civil",
    43: "Actividades especializadas de construcción", 45: "Comercio de vehículos automotores",
    46: "Comercio al por mayor", 47: "Comercio al por menor",
    49: "Transporte terrestre", 50: "Transporte acuático", 51: "Transporte aéreo",
    52: "Almacenamiento y actividades de transporte", 53: "Correo y servicios de mensajería",
    55: "Alojamiento", 56: "Restaurantes y servicios de comida",
    58: "Actividades de edición", 59: "Producción audiovisual",
    60: "Programación y transmisión (radio/TV)", 61: "Telecomunicaciones",
    62: "Desarrollo de sistemas informáticos / programación", 63: "Actividades de servicios de información",
    64: "Actividades financieras", 65: "Seguros", 66: "Actividades auxiliares financieras",
    68: "Actividades inmobiliarias", 69: "Actividades jurídicas y contables",
    70: "Administración empresarial y consultoría", 71: "Arquitectura e ingeniería",
    72: "Investigación científica y desarrollo", 73: "Publicidad y estudios de mercado",
    74: "Otras actividades profesionales", 75: "Actividades veterinarias",
    77: "Actividades de alquiler y arrendamiento", 78: "Actividades de empleo",
    79: "Agencias de viajes", 80: "Actividades de seguridad",
    81: "Actividades de servicios a edificios", 82: "Actividades administrativas de apoyo",
    84: "Administración pública y defensa", 85: "Educación",
    86: "Actividades de atención de la salud humana", 87: "Actividades de asistencia social residencial",
    88: "Actividades de asistencia social sin alojamiento", 90: "Actividades creativas, artísticas y de entretenimiento",
    91: "Bibliotecas, archivos y museos", 92: "Actividades de juegos de azar",
    93: "Actividades deportivas y de recreación", 94: "Actividades de asociaciones",
    95: "Reparación de computadores y enseres", 96: "Otras actividades de servicios personales",
    97: "Actividades de hogares como empleadores", 98: "Actividades no diferenciadas de hogares",
    99: "Actividades de organizaciones extraterritoriales",
}

DDL_RESUMEN = """
CREATE TABLE IF NOT EXISTS geih_departamento_resumen (
    dpto INT NOT NULL,
    departamento VARCHAR(80) DEFAULT NULL,
    n_observaciones INT DEFAULT NULL,
    poblacion_ocupada_estimada BIGINT DEFAULT NULL,
    poblacion_desocupada_estimada BIGINT DEFAULT NULL,
    tasa_desempleo_pct DECIMAL(5,2) DEFAULT NULL,
    ingreso_mediana DECIMAL(12,2) DEFAULT NULL,
    ingreso_medio DECIMAL(12,2) DEFAULT NULL,
    pct_informalidad DECIMAL(5,2) DEFAULT NULL,
    pct_cabecera DECIMAL(5,2) DEFAULT NULL,
    anio_inicio INT DEFAULT NULL,
    anio_fin INT DEFAULT NULL,
    PRIMARY KEY (dpto)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""

DDL_SECTOR = """
CREATE TABLE IF NOT EXISTS geih_sector_departamento (
    dpto INT NOT NULL,
    departamento VARCHAR(80) DEFAULT NULL,
    sector_ciiu_2d INT NOT NULL,
    sector_nombre VARCHAR(120) DEFAULT NULL,
    n_observaciones INT DEFAULT NULL,
    poblacion_ocupada_estimada BIGINT DEFAULT NULL,
    ingreso_mediana DECIMAL(12,2) DEFAULT NULL,
    ingreso_medio DECIMAL(12,2) DEFAULT NULL,
    pct_informalidad DECIMAL(5,2) DEFAULT NULL,
    horas_promedio_semanales DECIMAL(5,2) DEFAULT NULL,
    anio_inicio INT DEFAULT NULL,
    anio_fin INT DEFAULT NULL,
    PRIMARY KEY (dpto, sector_ciiu_2d)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""


def weighted_median(values: np.ndarray, weights: np.ndarray):
    if len(values) == 0:
        return None
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cum = np.cumsum(weights)
    cutoff = weights.sum() / 2.0
    idx = int(np.searchsorted(cum, cutoff))
    idx = min(idx, len(values) - 1)
    return float(values[idx])


def weighted_mean(values: np.ndarray, weights: np.ndarray):
    if len(values) == 0 or weights.sum() == 0:
        return None
    return float(np.average(values, weights=weights))


def weighted_pct(mask: np.ndarray, weights: np.ndarray):
    total = weights.sum()
    if total == 0:
        return None
    return float(weights[mask].sum() / total * 100)


# ================================================================
#   AGREGACION
# ================================================================

def cargar_geih(ruta_csv: str) -> pd.DataFrame:
    print(f"Leyendo {ruta_csv} ...")
    df = pd.read_csv(ruta_csv, low_memory=False)
    print(f"  {len(df):,} registros, {df['ANIO'].min()}-{df['ANIO'].max()}")
    return df


def agregar_departamento(df: pd.DataFrame) -> list:
    filas = []
    anio_inicio, anio_fin = int(df["ANIO"].min()), int(df["ANIO"].max())
    for dpto, g in df.groupby("DPTO"):
        # La GEIH es un panel MENSUAL: cada mes es una foto transversal con su
        # propio FACTOR_EXPANSION. Sumar el factor de 52 meses sin promediar
        # infla la poblacion ~52x (cada persona-mes se cuenta como una
        # persona distinta). Se divide por el numero de meses del grupo para
        # obtener el promedio mensual estimado, que es lo comparable.
        n_meses = g[["ANIO", "MES"]].drop_duplicates().shape[0] or 1
        w = g["FACTOR_EXPANSION"].to_numpy()
        ocupados = g["CONDICION_ACTIVIDAD"] == "Ocupado"
        desocupados = g["CONDICION_ACTIVIDAD"] == "Desocupado"
        pob_ocupada = float(w[ocupados.to_numpy()].sum()) / n_meses
        pob_desocupada = float(w[desocupados.to_numpy()].sum()) / n_meses
        peaa = pob_ocupada + pob_desocupada  # poblacion economicamente activa (aprox)
        tasa_desempleo = round(pob_desocupada / peaa * 100, 2) if peaa > 0 else None

        g_ing = g[ocupados & g["INGRESOS_MENSUALES"].notna()]
        ing_vals = g_ing["INGRESOS_MENSUALES"].to_numpy()
        ing_w = g_ing["FACTOR_EXPANSION"].to_numpy()

        g_inf = g[g["INFORMALIDAD_DANE"].isin(["Informal", "Formal"])]
        inf_mask = (g_inf["INFORMALIDAD_DANE"] == "Informal").to_numpy()
        inf_w = g_inf["FACTOR_EXPANSION"].to_numpy()

        cabecera_mask = (g["CLASE"] == "Cabecera").to_numpy()

        filas.append((
            int(dpto), DPTO_NOMBRE.get(int(dpto), None), int(len(g)),
            int(round(pob_ocupada)), int(round(pob_desocupada)), tasa_desempleo,
            weighted_median(ing_vals, ing_w), weighted_mean(ing_vals, ing_w),
            weighted_pct(inf_mask, inf_w), weighted_pct(cabecera_mask, w),
            anio_inicio, anio_fin,
        ))
    return filas


def agregar_sector_departamento(df: pd.DataFrame) -> list:
    filas = []
    anio_inicio, anio_fin = int(df["ANIO"].min()), int(df["ANIO"].max())
    ocupados = df[(df["CONDICION_ACTIVIDAD"] == "Ocupado") & df["SECTOR_CIIU_2D"].notna()].copy()
    ocupados["SECTOR_CIIU_2D"] = ocupados["SECTOR_CIIU_2D"].astype(int)

    for (dpto, sector), g in ocupados.groupby(["DPTO", "SECTOR_CIIU_2D"]):
        # Mismo ajuste que en agregar_departamento(): promediar por mes, no
        # sumar los 52 meses del panel (ver comentario ahi).
        n_meses = g[["ANIO", "MES"]].drop_duplicates().shape[0] or 1
        w = g["FACTOR_EXPANSION"].to_numpy()
        pob_ocupada = float(w.sum()) / n_meses

        g_ing = g[g["INGRESOS_MENSUALES"].notna()]
        ing_vals = g_ing["INGRESOS_MENSUALES"].to_numpy()
        ing_w = g_ing["FACTOR_EXPANSION"].to_numpy()

        g_inf = g[g["INFORMALIDAD_DANE"].isin(["Informal", "Formal"])]
        inf_mask = (g_inf["INFORMALIDAD_DANE"] == "Informal").to_numpy()
        inf_w = g_inf["FACTOR_EXPANSION"].to_numpy()

        g_horas = g[g["HORAS_TRABAJADAS_SEMANALES"].notna()]
        horas_vals = g_horas["HORAS_TRABAJADAS_SEMANALES"].to_numpy()
        horas_w = g_horas["FACTOR_EXPANSION"].to_numpy()

        # Filtrar celdas con muy pocas observaciones crudas: la GEIH no es
        # confiable para desagregaciones tan finas por debajo de ~30 registros.
        if len(g) < 30:
            continue

        filas.append((
            int(dpto), DPTO_NOMBRE.get(int(dpto), None), int(sector),
            CIIU_NOMBRE.get(int(sector), "Sin clasificar"), int(len(g)),
            int(round(pob_ocupada)),
            weighted_median(ing_vals, ing_w), weighted_mean(ing_vals, ing_w),
            weighted_pct(inf_mask, inf_w), weighted_mean(horas_vals, horas_w),
            anio_inicio, anio_fin,
        ))
    return filas


# ================================================================
#   CARGA A MYSQL
# ================================================================

def cargar_mysql(filas_resumen: list, filas_sector: list):
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(DDL_RESUMEN)
    cur.execute(DDL_SECTOR)

    cur.execute("TRUNCATE TABLE geih_departamento_resumen")
    cur.executemany(
        "INSERT INTO geih_departamento_resumen "
        "(dpto, departamento, n_observaciones, poblacion_ocupada_estimada, "
        " poblacion_desocupada_estimada, tasa_desempleo_pct, ingreso_mediana, "
        " ingreso_medio, pct_informalidad, pct_cabecera, anio_inicio, anio_fin) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        filas_resumen,
    )

    cur.execute("TRUNCATE TABLE geih_sector_departamento")
    cur.executemany(
        "INSERT INTO geih_sector_departamento "
        "(dpto, departamento, sector_ciiu_2d, sector_nombre, n_observaciones, "
        " poblacion_ocupada_estimada, ingreso_mediana, ingreso_medio, "
        " pct_informalidad, horas_promedio_semanales, anio_inicio, anio_fin) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        filas_sector,
    )

    conn.commit()
    print(f"  geih_departamento_resumen: {len(filas_resumen)} filas")
    print(f"  geih_sector_departamento: {len(filas_sector)} filas")
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=RUTA_DEFECTO, help="Ruta al CSV crudo de la GEIH")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: no se encontró el CSV en {args.input}", file=sys.stderr)
        print("Pasa la ruta real con --input /ruta/al/GEIH_consolidado_2022_2026.csv", file=sys.stderr)
        sys.exit(1)

    df = cargar_geih(args.input)
    print("Agregando por departamento (ponderado por FACTOR_EXPANSION)...")
    filas_resumen = agregar_departamento(df)
    print("Agregando por departamento x sector CIIU...")
    filas_sector = agregar_sector_departamento(df)
    print("Cargando a MySQL...")
    cargar_mysql(filas_resumen, filas_sector)
    print("Listo.")


if __name__ == "__main__":
    main()
