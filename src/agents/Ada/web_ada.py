import http.server
import socketserver
import json
import subprocess
import sys
import os
import urllib.request
import urllib.parse

PORT = 8081


def _cargar_env():
    """Carga variables de un .env en la raiz de SHIDO_MINTIC (sin dependencias)."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(aqui)))  # .../SHIDO_MINTIC
    ruta_env = os.path.join(raiz, ".env")
    if not os.path.exists(ruta_env):
        return
    try:
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
    except Exception:
        pass


_cargar_env()


def _db_kwargs():
    return {
        "host": os.environ.get("DB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("DB_PORT", "3306")),
        "user": os.environ.get("DB_USER", "odemiro"),
        "password": os.environ.get("DB_PASS", ""),
        "database": os.environ.get("DB_NAME", "odemiro_db"),
        "connection_timeout": 10,
    }


def consultar_carrera_directo(carrera, municipio=""):
    """Consulta DETERMINISTA (SQL fijo) de estadisticas de una carrera en SNIES.
    Retorna dict con cifras reales, o None si la DB no esta disponible."""
    import mysql.connector
    like = f"%{carrera.upper()}%"
    try:
        conn = mysql.connector.connect(**_db_kwargs())
        cur = conn.cursor()
        # Totales, IES, distribucion por sexo
        cur.execute(
            "SELECT SUM(matriculados), COUNT(DISTINCT institucion_de_educacion_superior_ies), "
            "SUM(CASE WHEN UPPER(sexo)='FEMENINO' THEN matriculados ELSE 0 END), "
            "SUM(CASE WHEN UPPER(sexo) IN ('HOMBRE','MASCULINO') THEN matriculados ELSE 0 END) "
            "FROM snies_matriculados WHERE UPPER(programa_academico) LIKE %s",
            (like,)
        )
        total, n_ies, fem, masc = cur.fetchone()
        if not total:
            cur.close(); conn.close()
            return {"encontrado": False, "carrera": carrera}
        # Top IES
        cur.execute(
            "SELECT institucion_de_educacion_superior_ies, SUM(matriculados) t "
            "FROM snies_matriculados WHERE UPPER(programa_academico) LIKE %s "
            "GROUP BY institucion_de_educacion_superior_ies ORDER BY t DESC LIMIT 5",
            (like,)
        )
        top_ies = [(r[0].title(), int(r[1])) for r in cur.fetchall()]
        # Top municipios de oferta
        cur.execute(
            "SELECT municipio_de_oferta_del_programa, SUM(matriculados) t "
            "FROM snies_matriculados WHERE UPPER(programa_academico) LIKE %s "
            "GROUP BY municipio_de_oferta_del_programa ORDER BY t DESC LIMIT 5",
            (like,)
        )
        top_mun = [(r[0].title(), int(r[1])) for r in cur.fetchall()]
        # Caracter (publica/privada) via sector
        cur.execute(
            "SELECT sector_ies, SUM(matriculados) t FROM snies_matriculados "
            "WHERE UPPER(programa_academico) LIKE %s GROUP BY sector_ies ORDER BY t DESC",
            (like,)
        )
        sectores = [(r[0].title() if r[0] else 'N/A', int(r[1])) for r in cur.fetchall()]

        # DESERCION de la carrera de interes (tabla desercion_academica)
        desercion = None
        try:
            like_prog = f"%{carrera.upper()}%"
            cur.execute(
                "SELECT COUNT(*) FROM desercion_academica WHERE UPPER(nombre_programa) LIKE %s",
                (like_prog,)
            )
            total_deser = int(cur.fetchone()[0] or 0)
            if total_deser > 0:
                cur.execute(
                    "SELECT estrato, COUNT(*) c FROM desercion_academica "
                    "WHERE UPPER(nombre_programa) LIKE %s AND estrato IS NOT NULL AND estrato <> '' "
                    "GROUP BY estrato ORDER BY c DESC LIMIT 6",
                    (like_prog,)
                )
                deser_estrato = [(str(r[0]), int(r[1])) for r in cur.fetchall()]
                cur.execute(
                    "SELECT genero, COUNT(*) c FROM desercion_academica "
                    "WHERE UPPER(nombre_programa) LIKE %s GROUP BY genero ORDER BY c DESC",
                    (like_prog,)
                )
                deser_genero = [(str(r[0]), int(r[1])) for r in cur.fetchall()]
                # Indice aproximado: casos de desercion vs matriculados historicos
                indice = round(total_deser / int(total) * 100, 2) if total else None
                desercion = {
                    "total_casos": total_deser,
                    "indice_pct": indice,
                    "por_estrato": deser_estrato,
                    "por_genero": deser_genero,
                }
        except Exception:
            desercion = None

        cur.close(); conn.close()
        return {
            "encontrado": True,
            "carrera": carrera,
            "municipio_interes": municipio,
            "total_matriculados": int(total),
            "num_ies": int(n_ies),
            "femenino": int(fem or 0),
            "masculino": int(masc or 0),
            "top_ies": top_ies,
            "top_municipios": top_mun,
            "sectores": sectores,
            "desercion": desercion,
        }
    except Exception:
        return None


def redactar_analisis_gemini(stats):
    """Usa Gemini para redactar un analisis amigable a partir de cifras reales.
    Si Gemini falla, arma un resumen de respaldo con las cifras."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    fem = stats["femenino"]; masc = stats["masculino"]
    tot_sexo = fem + masc
    pct_fem = round(fem / tot_sexo * 100, 1) if tot_sexo else 0
    pct_masc = round(masc / tot_sexo * 100, 1) if tot_sexo else 0
    datos_txt = (
        f"Carrera: {stats['carrera']}\n"
        f"Total matriculados (historico): {stats['total_matriculados']:,}\n"
        f"Numero de IES que la ofrecen: {stats['num_ies']}\n"
        f"Distribucion por sexo: Femenino {fem:,} ({pct_fem}%), Masculino {masc:,} ({pct_masc}%)\n"
        f"Top IES: {stats['top_ies']}\n"
        f"Top municipios de oferta: {stats['top_municipios']}\n"
        f"Distribucion por sector: {stats['sectores']}\n"
        f"Municipio de interes del usuario: {stats.get('municipio_interes') or 'no especificado'}\n"
    )
    deser = stats.get("desercion")
    if deser:
        datos_txt += (
            f"DESERCION (tabla desercion_academica): {deser['total_casos']} casos de perdida de cupo registrados; "
            f"indice aprox {deser['indice_pct']}% respecto a matriculados historicos; "
            f"por estrato: {deser['por_estrato']}; por genero: {deser['por_genero']}\n"
        )
    else:
        datos_txt += "DESERCION: sin registros para esta carrera en la tabla desercion_academica.\n"
    if not api_key:
        return _resumen_respaldo(stats, pct_fem, pct_masc)
    prompt = (
        "Eres Lumina, analista de datos de ODEM (Universidad EAN). Con base en estas cifras REALES "
        "del SNIES, redacta un analisis estadistico claro, amigable y con emojis moderados. "
        "NO inventes cifras: usa solo las proporcionadas. Estructura: resumen, universidades destacadas, "
        "distribucion por sexo, oferta por ciudad, un apartado de INDICE DE DESERCION (interpreta las cifras "
        "reales de desercion y da consejos de permanencia; si no hay datos, dilo), y una nota final util.\n\n" + datos_txt
    )
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192},
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        cand = data["candidates"][0]
        # Concatenar TODAS las partes (Gemini puede dividir la respuesta en varias)
        partes = cand.get("content", {}).get("parts", [])
        texto = "".join(p.get("text", "") for p in partes).strip()
        if not texto:
            return _resumen_respaldo(stats, pct_fem, pct_masc)
        # Si se corto por limite de tokens, anexar el resumen de respaldo con las cifras clave
        if cand.get("finishReason") == "MAX_TOKENS":
            texto += "\n\n---\n" + _resumen_respaldo(stats, pct_fem, pct_masc)
        return texto
    except Exception:
        return _resumen_respaldo(stats, pct_fem, pct_masc)


def _resumen_respaldo(stats, pct_fem, pct_masc):
    lineas = [
        f"### \U0001F4CA An\u00e1lisis de {stats['carrera']}",
        "",
        f"**Total de matriculados (hist\u00f3rico):** {stats['total_matriculados']:,}",
        f"**Instituciones que la ofrecen:** {stats['num_ies']}",
        f"**Distribuci\u00f3n por sexo:** Femenino {pct_fem}% \u00b7 Masculino {pct_masc}%",
        "",
        "**Principales universidades:**",
    ]
    for ies, t in stats["top_ies"]:
        lineas.append(f"- {ies}: {t:,} matriculados")
    lineas.append("")
    lineas.append("**Ciudades con mayor oferta:**")
    for mun, t in stats["top_municipios"]:
        lineas.append(f"- {mun}: {t:,}")
    deser = stats.get("desercion")
    lineas.append("")
    lineas.append("**\u00cdndice de deserci\u00f3n:**")
    if deser:
        lineas.append(f"- Casos registrados de p\u00e9rdida de cupo: {deser['total_casos']:,} (\u2248 {deser['indice_pct']}% de los matriculados hist\u00f3ricos)")
        if deser.get("por_estrato"):
            lineas.append("- Por estrato: " + ", ".join(f"estrato {e}: {c}" for e, c in deser["por_estrato"]))
        if deser.get("por_genero"):
            lineas.append("- Por g\u00e9nero: " + ", ".join(f"{g}: {c}" for g, c in deser["por_genero"]))
    else:
        lineas.append("- Sin registros de deserci\u00f3n para esta carrera en la base de datos.")
    return "\n".join(lineas)

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MinTIC - Orientación Vocacional Ada (Cuestionario Completo)</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding-bottom: 50px; }
        header { background-color: #004884; color: white; padding: 20px; display: flex; align-items: center; box-shadow: 0 4px 10px rgba(0,0,0,0.08); }
        header .logo-gov { font-size: 26px; font-weight: bold; margin-right: 20px; background: white; color: #004884; padding: 5px 15px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        header h1 { margin: 0; font-size: 22px; font-weight: 400; }
        .container { max-width: 800px; margin: 40px auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.06); border: 1px solid #e2e8f0; }
        h2 { color: #004884; border-bottom: 2px solid #E0004D; padding-bottom: 12px; font-size: 24px; margin-top: 0; }
        h3 { color: #3366CC; margin-top: 25px; font-size: 18px; border-bottom: 1px dashed #e2e8f0; padding-bottom: 8px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #2d3748; font-size: 14px; }
        input[type="text"], input[type="number"], select { width: 100%; padding: 12px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; font-size: 15px; transition: border-color 0.2s; }
        input[type="text"]:focus, input[type="number"]:focus, select:focus { border-color: #3366CC; outline: none; }
        
        .progress-container { margin: 25px 0 15px 0; }
        .progress-bar-bg { width: 100%; background-color: #e2e8f0; border-radius: 20px; height: 12px; overflow: hidden; }
        .progress-bar-fill { height: 100%; background-color: #27ae60; width: 0%; transition: width 0.4s ease; }
        .progress-text { display: flex; justify-content: space-between; font-size: 12px; color: #64748b; margin-top: 6px; font-weight: bold; }

        .test-question { background: #f8fafc; padding: 20px; margin-bottom: 20px; border-radius: 8px; border-left: 5px solid #004884; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
        .test-question p { margin-top: 0; margin-bottom: 15px; font-weight: bold; color: #1e293b; font-size: 15px; line-height: 1.5; }
        
        .scale-container { display: flex; justify-content: space-between; align-items: center; padding: 12px 15px; background: white; border-radius: 6px; border: 1px solid #cbd5e1; }
        .scale-label { font-size: 12px; font-weight: bold; color: #64748b; }
        .scale-option { display: flex; flex-direction: column; align-items: center; cursor: pointer; position: relative; }
        .scale-option input { transform: scale(1.3); cursor: pointer; margin-bottom: 6px; }
        .scale-option span { font-size: 11px; color: #64748b; font-weight: bold; }

        .nav-buttons { display: flex; justify-content: space-between; margin-top: 30px; gap: 15px; }
        .btn { border: none; padding: 12px 24px; cursor: pointer; border-radius: 6px; font-size: 15px; font-weight: bold; transition: background-color 0.2s, transform 0.1s; display: inline-flex; align-items: center; justify-content: center; text-decoration: none; }
        .btn-primary { background-color: #004884; color: white; width: auto; min-width: 130px; }
        .btn-primary:hover { background-color: #00366a; }
        .btn-secondary { background-color: #64748b; color: white; width: auto; min-width: 130px; }
        .btn-secondary:hover { background-color: #475569; }
        .btn-accent { background-color: #E0004D; color: white; width: 100%; font-size: 16px; padding: 15px; }
        .btn-accent:hover { background-color: #c00040; }
        .btn-disabled { opacity: 0.5; cursor: not-allowed; }

        #reporte { display: none; background: #ffffff; padding: 35px; border-radius: 12px; margin-top: 40px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px rgba(0,0,0,0.05); line-height: 1.7; color: #333; }
        #reporte h1 { color: #004884; font-size: 26px; border-bottom: 2px solid #E0004D; padding-bottom: 12px; margin-top: 0; }
        #reporte h2, #reporte h3, #reporte h4 { color: #004884; margin-top: 30px; }
        #reporte img { max-width: 100%; height: auto; border-radius: 8px; display: block; margin: 25px auto; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        #reporte table { width: 100%; border-collapse: collapse; margin: 25px 0; }
        #reporte th, #reporte td { border: 1px solid #cbd5e1; padding: 12px 15px; text-align: left; font-size: 14px; }
        #reporte th { background-color: #f8fafc; color: #004884; font-weight: bold; }
        #reporte ul, #reporte ol { padding-left: 20px; }
        #reporte li { margin-bottom: 10px; }
        #reporte hr { border: 0; border-top: 1px solid #e2e8f0; margin: 35px 0; }
        .family-friendly-intro { background-color: #e8f4fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #3366CC; font-style: italic; }
        .loader { display: none; text-align: center; margin-top: 30px; font-weight: bold; color: #004884; font-size: 16px; }
        .loader-spinner { border: 4px solid #f3f3f3; border-top: 4px solid #004884; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 15px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>

<header>
    <div class="logo-gov">GOV.CO</div>
    <div>
        <h1>Ministerio de Tecnologías de la Información y las Comunicaciones</h1>
        <div style="font-size: 14px; margin-top: 4px; opacity: 0.9;">Plataforma de Orientación Vocacional - Proyecto ODEM Universidad EAN</div>
    </div>
</header>

<div class="container">
    <h2>Agente Ada - Cuestionario Vocacional Optimizado (personality.co)</h2>
    <p style="color: #475569; font-size: 15px; line-height: 1.5; margin-bottom: 30px;">
        Este test consta de 40 preguntas diseñadas para evaluar en profundidad tus aptitudes, intereses y rasgos de personalidad. Al finalizar, la inteligencia artificial de Ada cruzará tus resultados con las bases de datos de Lumina (SNIES real) y generará un reporte vocacional detallado y un archivo Excel descargable.
    </p>

    <form id="adaForm">
        <div id="section-personal">
            <h3>1. Datos Personales & Socioeconómicos</h3>
            <div class="form-group">
                <label>Nombre Completo:</label>
                <input type="text" id="nombre_completo" required value="" placeholder="Escribe tu nombre completo">
            </div>
            <div class="form-group">
                <label>Municipio de residencia:</label>
                <select id="municipio" required>
                    <option value="" selected disabled>Selecciona tu municipio...</option>
                    <option value="Bogotá, D.C.">Bogotá, D.C.</option>
                    <option value="Medellín">Medellín</option>
                    <option value="Cali">Cali</option>
                    <option value="Barranquilla">Barranquilla</option>
                    <option value="Bucaramanga">Bucaramanga</option>
                    <option value="Cartagena De Indias">Cartagena De Indias</option>
                    <option value="Manizales">Manizales</option>
                    <option value="Pereira">Pereira</option>
                    <option value="Ibagué">Ibagué</option>
                    <option value="Cúcuta">Cúcuta</option>
                </select>
            </div>
            <div class="form-group">
                <label>Estrato Socioeconómico (1 - 6):</label>
                <input type="number" id="estrato" required value="" min="1" max="6" placeholder="1 a 6">
            </div>
            <div class="form-group">
                <label>Ingresos Familiares Mensuales (COP):</label>
                <input type="number" id="ingresos" required value="" placeholder="Ej: 2000000">
            </div>
            <div class="form-group">
                <label>Puntaje Pruebas Saber 11 / ICFES (0 - 500):</label>
                <input type="number" id="icfes" required value="" min="0" max="500" placeholder="0 a 500">
            </div>
            
            <div class="form-group">
                <label>Carrera de interés (Lumina la analizará en el Excel):</label>
                <select id="carrera_interes_personal">
                    <option value="" selected>Sugerir automáticamente...</option>
                    <option value="Ingeniería de Sistemas">Ingeniería de Sistemas</option>
                    <option value="Ingeniería Biomédica">Ingeniería Biomédica</option>
                    <option value="Ingeniería Civil">Ingeniería Civil</option>
                    <option value="Psicología">Psicología</option>
                    <option value="Medicina">Medicina</option>
                    <option value="Enfermería">Enfermería</option>
                    <option value="Derecho">Derecho</option>
                    <option value="Administración de Empresas">Administración de Empresas</option>
                    <option value="Diseño Gráfico">Diseño Gráfico</option>
                    <option value="Estadística">Estadística</option>
                    <option value="Licenciatura en Matemáticas">Licenciatura en Matemáticas</option>
                </select>
            </div>
            <div class="form-group" style="margin-top:10px;">
                <label style="font-weight:normal; cursor:pointer;">
                    <input type="checkbox" id="becas_en_vivo" style="width:auto; margin-right:8px;">
                    Actualizar becas en vivo (consulta convocatorias reales en la web; el reporte tarda un poco más)
                </label>
            </div>
            <button type="button" class="btn btn-accent" style="margin-top: 15px;" onclick="startTest()">Comenzar Test Vocacional (40 preguntas) »</button>
        </div>

        <div id="section-test" style="display: none;">
            <div class="progress-container">
                <div class="progress-bar-bg">
                    <div id="progressBar" class="progress-bar-fill"></div>
                </div>
                <div class="progress-text">
                    <span id="progressTextPercentage">Progreso: 0%</span>
                    <span id="progressTextQuestions">Preguntas: 0 de 40</span>
                </div>
            </div>

            <div id="questions-container">
                <!-- Las preguntas se cargarán aquí dinámicamente -->
            </div>

            <div class="nav-buttons">
                <button type="button" id="prevBtn" class="btn btn-secondary btn-disabled" onclick="changePage(-1)">« Anterior</button>
                <span id="pageIndicator" style="align-self: center; font-weight: bold; color: #1e293b; font-size: 14px;">Página 1 de 4</span>
                <button type="button" id="nextBtn" class="btn btn-primary" onclick="changePage(1)">Siguiente »</button>
            </div>

            <div id="submit-container" style="display: none; margin-top: 30px;">
                <button type="submit" id="submitBtn" class="btn btn-accent">🚀 Enviar Cuestionario y Generar Reporte de Producción</button>
            </div>
        </div>
    </form>

    <div class="loader" id="loader">
        <div class="loader-spinner"></div>
        <span id="loader-message">Procesando respuestas con el motor de Ada... Por favor espera...</span>
    </div>
    
    <div id="reporte"></div>

    <!-- ====== SECCIÓN POST-REPORTE: CONSULTA DE CARRERA DE INTERÉS (LUMINA) ====== -->
    <div id="section-lumina" style="display: none; margin-top: 40px; background: #ffffff; padding: 35px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
        <h3 style="color: #004884; border-bottom: 2px solid #E0004D; padding-bottom: 12px; margin-top: 0;">🔍 ¿Te interesa una carrera específica?</h3>
        <p style="color: #475569; font-size: 15px; line-height: 1.5;">
            Escribe el nombre de una carrera y <strong>Lumina</strong> analizará las estadísticas reales del SNIES:
            matriculados, universidades que la ofrecen, distribución por sexo, oferta por ciudad y estimación de deserción.
        </p>
        <div class="form-group">
            <label>Carrera de interés:</label>
            <select id="carrera_interes">
                <option value="" disabled selected>Selecciona una carrera...</option>
                <option value="Ingeniería de Sistemas">Ingeniería de Sistemas</option>
                <option value="Ingeniería Biomédica">Ingeniería Biomédica</option>
                <option value="Ingeniería Civil">Ingeniería Civil</option>
                <option value="Psicología">Psicología</option>
                <option value="Medicina">Medicina</option>
                <option value="Enfermería">Enfermería</option>
                <option value="Derecho">Derecho</option>
                <option value="Administración de Empresas">Administración de Empresas</option>
                <option value="Diseño Gráfico">Diseño Gráfico</option>
                <option value="Estadística">Estadística</option>
                <option value="Licenciatura en Matemáticas">Licenciatura en Matemáticas</option>
            </select>
        </div>
        <button type="button" class="btn btn-primary" style="width: 100%;" onclick="consultarLumina()">📊 Consultar estadísticas con Lumina</button>

        <div class="loader" id="loader-lumina">
            <div class="loader-spinner"></div>
            <span>Lumina está consultando la base de datos... Por favor espera...</span>
        </div>

        <div id="resultado-lumina" style="display: none; margin-top: 25px; padding: 25px; background: #f8fafc; border-radius: 8px; border-left: 5px solid #004884; line-height: 1.7; color: #333;"></div>
    </div>
</div>

<script>
    let questions = [];
    let currentPage = 0;
    const questionsPerPage = 10;
    // totalQuestions se establece dinámicamente al cargar las preguntas

    // Cargar preguntas desde el backend
    async function loadQuestions() {
        try {
            const response = await fetch('/api/questions');
            questions = await response.json();
            totalQuestions = questions.length;
        } catch (error) {
            console.error('Error cargando preguntas:', error);
            alert('Error al conectar con la API de preguntas. Asegúrate de que el servidor está corriendo.');
        }
    }

    // Iniciar test vocacional
    async function startTest() {
        // Validar datos personales primero
        const nombre = document.getElementById('nombre_completo').value;
        const estrato = parseInt(document.getElementById('estrato').value);
        const icfes = parseInt(document.getElementById('icfes').value);

        if (!nombre) {
            alert('Por favor ingresa tu nombre completo.');
            return;
        }
        if (isNaN(estrato) || estrato < 1 || estrato > 6) {
            alert('El estrato debe ser un número entre 1 y 6.');
            return;
        }
        if (isNaN(icfes) || icfes < 0 || icfes > 500) {
            alert('El puntaje ICFES debe estar entre 0 y 500.');
            return;
        }

        document.getElementById('section-personal').style.display = 'none';
        document.getElementById('section-test').style.display = 'block';
        
        await loadQuestions();
        renderPage();
    }

    // Renderizar la página actual de preguntas
    function renderPage() {
        const container = document.getElementById('questions-container');
        container.innerHTML = '';

        const start = currentPage * questionsPerPage;
        const end = Math.min(start + questionsPerPage, questions.length);

        for (let i = start; i < end; i++) {
            const q = questions[i];
            const savedValue = localStorage.getItem(`p${q.id}`) || '';
            
            // Render properly with simpler inline html
            let qHtml = `
                <div class="test-question">
                    <p>${q.id}. ${q.question}</p>
                    <div class="scale-container">
                        <span class="scale-label" style="color: #e11d48;">En desacuerdo</span>
                        <div class="scale-option"><input type="radio" name="p${q.id}" value="1" ${savedValue === '1' ? 'checked' : ''} onchange="saveAnswer(${q.id}, 1)" required><span>1</span></div>
                        <div class="scale-option"><input type="radio" name="p${q.id}" value="2" ${savedValue === '2' ? 'checked' : ''} onchange="saveAnswer(${q.id}, 2)"><span>2</span></div>
                        <div class="scale-option"><input type="radio" name="p${q.id}" value="3" ${savedValue === '3' ? 'checked' : ''} onchange="saveAnswer(${q.id}, 3)"><span>3</span></div>
                        <div class="scale-option"><input type="radio" name="p${q.id}" value="4" ${savedValue === '4' ? 'checked' : ''} onchange="saveAnswer(${q.id}, 4)"><span>4</span></div>
                        <div class="scale-option"><input type="radio" name="p${q.id}" value="5" ${savedValue === '5' ? 'checked' : ''} onchange="saveAnswer(${q.id}, 5)"><span>5</span></div>
                        <span class="scale-label" style="color: #16a34a; font-weight: bold;">De acuerdo</span>
                    </div>
                </div>
            `;
            container.innerHTML += qHtml;
        }

        // Indicador de página
        const totalPages = Math.ceil(questions.length / questionsPerPage);
        document.getElementById('pageIndicator').textContent = `Página ${currentPage + 1} de ${totalPages}`;

        // Deshabilitar botón "Anterior" si estamos en la página 0
        const prevBtn = document.getElementById('prevBtn');
        if (currentPage === 0) {
            prevBtn.classList.add('btn-disabled');
        } else {
            prevBtn.classList.remove('btn-disabled');
        }

        // Si estamos en la última página, ocultar "Siguiente" y mostrar el contenedor de envío
        const nextBtn = document.getElementById('nextBtn');
        const submitContainer = document.getElementById('submit-container');
        if (currentPage === totalPages - 1) {
            nextBtn.style.display = 'none';
            submitContainer.style.display = 'block';
        } else {
            nextBtn.style.display = 'inline-flex';
            submitContainer.style.display = 'none';
        }

        updateProgress();
    }

    // Guardar respuesta localmente
    function saveAnswer(id, val) {
        localStorage.setItem(`p${id}`, val);
        updateProgress();
    }

    // Calcular progreso
    function updateProgress() {
        let answeredCount = 0;
        for (let i = 1; i <= questions.length; i++) {
            if (localStorage.getItem(`p${i}`)) {
                answeredCount++;
            }
        }
        const pct = Math.round((answeredCount / questions.length) * 100);
        document.getElementById('progressBar').style.width = `${pct}%`;
        document.getElementById('progressTextPercentage').textContent = `Progreso: ${pct}%`;
        document.getElementById('progressTextQuestions').textContent = `Preguntas: ${answeredCount} de ${questions.length}`;
    }

    // Validar si la página actual está completamente contestada
    function isPageComplete() {
        const start = currentPage * questionsPerPage;
        const end = Math.min(start + questionsPerPage, questions.length);
        for (let i = start; i < end; i++) {
            const q = questions[i];
            if (!localStorage.getItem(`p${q.id}`)) {
                return false;
            }
        }
        return true;
    }

    // Cambiar de página
    function changePage(dir) {
        if (dir === 1 && !isPageComplete()) {
            alert('Por favor responde todas las preguntas de la página actual antes de continuar.');
            return;
        }

        const totalPages = Math.ceil(questions.length / questionsPerPage);
        const targetPage = currentPage + dir;

        if (targetPage >= 0 && targetPage < totalPages) {
            currentPage = targetPage;
            renderPage();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }

    // Enviar formulario
    document.getElementById('adaForm').addEventListener('submit', async function(e) {
        e.preventDefault();

        // Validar que todo el test esté contestado
        for (let i = 1; i <= questions.length; i++) {
            if (!localStorage.getItem(`p${i}`)) {
                alert(`Falta responder la pregunta ${i}. Por favor completa todo el cuestionario.`);
                return;
            }
        }

        document.getElementById('loader').style.display = 'block';
        document.getElementById('reporte').style.display = 'none';
        
        // Armar el payload dinámicamente
        const respuestas_test = {};
        for (let i = 1; i <= questions.length; i++) {
            respuestas_test[`p${i}`] = parseInt(localStorage.getItem(`p${i}`));
        }

        const payload = {
            datos_personales: {
                nombre_completo: document.getElementById('nombre_completo').value,
                municipio: document.getElementById('municipio').value,
                estrato: parseInt(document.getElementById('estrato').value),
                ingresos_familiares_cop: parseInt(document.getElementById('ingresos').value),
                icfes_puntaje: parseInt(document.getElementById('icfes').value),
                carrera_interes: document.getElementById('carrera_interes_personal').value,
                becas_en_vivo: document.getElementById('becas_en_vivo') ? document.getElementById('becas_en_vivo').checked : false
            },
            respuestas_test: respuestas_test
        };

        try {
            const response = await fetch('/api/ada', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            const repDiv = document.getElementById('reporte');
            repDiv.style.display = 'block';
            
            if (data.status === 'ok') {
                repDiv.innerHTML = marked.parse(data.reporte_texto);

                // Mostrar la sección de consulta de carrera de interés (Lumina)
                const secLumina = document.getElementById('section-lumina');
                secLumina.style.display = 'block';
                // Prellenar el municipio del formulario para dar contexto a Lumina
                window._municipioUsuario = document.getElementById('municipio').value;
                
                // Botón de descarga de Excel
                if (data.combined_excel_base64 && data.excel_filename) {
                    const downloadLink = document.createElement('a');
                    downloadLink.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + data.combined_excel_base64;
                    downloadLink.download = data.excel_filename;
                    downloadLink.textContent = '📥 Descargar Análisis Consolidado de Producción (Excel)';
                    downloadLink.className = 'btn btn-accent';
                    downloadLink.style.display = 'inline-block';
                    downloadLink.style.marginTop = '25px';
                    downloadLink.style.textAlign = 'center';
                    downloadLink.style.width = 'auto';
                    
                    repDiv.appendChild(document.createElement('hr'));
                    // --- Botón PDF ---
                    const pdfBtn = document.createElement('button');
                    pdfBtn.textContent = '📄 Descargar Informe Visual (PDF)';
                    pdfBtn.style.cssText = 'display:inline-block;margin-top:25px;margin-left:15px;background:#d32f2f;color:#fff;border:none;padding:0.8rem 1.5rem;border-radius:8px;cursor:pointer;font-weight:bold;';
                    pdfBtn.onclick = async function() {
                        pdfBtn.innerHTML = '⏳ Generando...'; pdfBtn.disabled = true;
                        // Ocultar los botones para que no salgan en el PDF (sin clonar)
                        const hr = repDiv.querySelector('hr');
                        downloadLink.style.display = 'none';
                        pdfBtn.style.display = 'none';
                        if (hr) hr.style.display = 'none';
                        // Esperar a que todas las imagenes del reporte terminen de cargar
                        const imgs = Array.from(repDiv.querySelectorAll('img'));
                        await Promise.all(imgs.map(img => img.complete ? Promise.resolve() : new Promise(res => { img.onload = res; img.onerror = res; })));
                        await new Promise(r => setTimeout(r, 400));
                        const opt = {
                            margin: 10,
                            filename: 'Reporte_Vocacional_Ada.pdf',
                            image: { type: 'jpeg', quality: 0.98 },
                            html2canvas: { scale: 2, useCORS: true, allowTaint: true, logging: false, backgroundColor: '#ffffff', scrollY: 0 },
                            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
                            pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
                        };
                        html2pdf().set(opt).from(repDiv).save().then(() => {
                            pdfBtn.textContent = '📄 Descargar Informe Visual (PDF)';
                            pdfBtn.disabled = false;
                            downloadLink.style.display = 'inline-block';
                            pdfBtn.style.display = 'inline-block';
                            if (hr) hr.style.display = 'block';
                        }).catch(err => {
                            alert('Error generando PDF: ' + err.message);
                            pdfBtn.textContent = '📄 Descargar Informe Visual (PDF)';
                            pdfBtn.disabled = false;
                            downloadLink.style.display = 'inline-block';
                            pdfBtn.style.display = 'inline-block';
                            if (hr) hr.style.display = 'block';
                        });
                    };
                    repDiv.appendChild(pdfBtn);
                    repDiv.appendChild(downloadLink);
                    
                    // Limpiar localStorage después de enviar con éxito para futuras pruebas
                    for (let i = 1; i <= totalQuestions; i++) {
                        localStorage.removeItem(`p${i}`);
                    }
                }
            } else {
                repDiv.innerHTML = `<h3 style="color: red;">Error en el procesamiento</h3><p>${data.error}</p>`;
            }
        } catch (error) {
            alert('Error conectando con el servidor local de Ada: ' + error.message);
        } finally {
            document.getElementById('loader').style.display = 'none';
        }
    });

    // ====== CONSULTA DE CARRERA DE INTERÉS VÍA LUMINA ======
    async function consultarLumina() {
        const carrera = document.getElementById('carrera_interes').value.trim();
        const resultDiv = document.getElementById('resultado-lumina');
        const loaderLumina = document.getElementById('loader-lumina');

        if (!carrera) {
            alert('Por favor escribe el nombre de una carrera de interés.');
            return;
        }

        loaderLumina.style.display = 'block';
        resultDiv.style.display = 'none';

        try {
            const response = await fetch('/api/lumina', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    carrera: carrera,
                    municipio: window._municipioUsuario || ''
                })
            });
            const data = await response.json();
            resultDiv.style.display = 'block';

            if (data.status === 'ok') {
                let html = `<h4 style="color:#004884; margin-top:0;">📈 Análisis de: ${carrera}</h4>`;
                html += marked.parse(data.respuesta || 'Sin datos disponibles.');
                if (data.sql) {
                    html += `<details style="margin-top:15px; font-size:13px; color:#64748b;"><summary style="cursor:pointer;">Ver consulta SQL generada</summary><pre style="background:#1e293b; color:#e2e8f0; padding:12px; border-radius:6px; overflow-x:auto; font-size:12px;">${data.sql}</pre></details>`;
                }
                resultDiv.innerHTML = html;
            } else {
                resultDiv.innerHTML = `<h4 style="color:#c00040; margin-top:0;">⚠️ No se pudo completar la consulta</h4><p>${data.error || 'Error desconocido.'}</p><p style="font-size:13px; color:#64748b;">Puedes intentar de nuevo o con otro nombre de carrera.</p>`;
            }
        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `<h4 style="color:#c00040; margin-top:0;">⚠️ Error de conexión</h4><p>No se pudo conectar con Lumina: ${error.message}</p>`;
        } finally {
            loaderLumina.style.display = 'none';
        }
    }

    // Limpiar caché de respuestas viejas de 10 preguntas si existen
    if (localStorage.getItem('p1') === 'A' || localStorage.getItem('p1') === 'B') {
        localStorage.clear();
    }
</script>

</body>
</html>
"""

class AdaHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path.startswith('/?'):
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        elif self.path == '/api/questions':
            try:
                path_json = os.path.join(os.path.dirname(__file__), 'preguntas_estructuradas.json')
                with open(path_json, 'r', encoding='utf-8') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(data.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/ada':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # Correr Ada.py con el JSON de entrada
                ada_script = os.path.join(os.path.dirname(__file__), 'Ada.py')
                result = subprocess.run(
                    [sys.executable, ada_script, post_data.decode('utf-8')],
                    capture_output=True, text=True, timeout=220
                )
                salida = result.stdout.strip()
                # Tolerancia a fallos: si Ada no devolvió JSON válido, empaquetar error legible
                if not salida:
                    salida = json.dumps({
                        "status": "error",
                        "error": "El motor de Ada no devolvió respuesta. Detalle: " + (result.stderr.strip()[:500] or "sin stderr")
                    }, ensure_ascii=False)
                else:
                    try:
                        json.loads(salida)  # validar
                    except Exception:
                        salida = json.dumps({
                            "status": "error",
                            "error": "Respuesta no válida del motor de Ada.",
                            "raw": salida[:1000]
                        }, ensure_ascii=False)
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(salida.encode('utf-8'))
            except subprocess.TimeoutExpired:
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "error": "El análisis de Ada tardó demasiado (timeout). Intenta de nuevo en unos minutos."
                }, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False).encode('utf-8'))

        elif self.path == '/api/lumina':
            # Consulta estadística de una carrera de interés vía Lumina (BD SNIES/GEIH)
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length else b'{}'
            try:
                payload = json.loads(post_data.decode('utf-8') or '{}')
                carrera = (payload.get('carrera') or '').strip()
                municipio = (payload.get('municipio') or '').strip()
                if not carrera:
                    raise ValueError("Debes indicar una carrera de interés.")

                # Consulta DETERMINISTA a la BD (SQL fijo). Gemini solo redacta el analisis.
                # Esto elimina el error 1064 intermitente por SQL generado por el LLM.
                stats = consultar_carrera_directo(carrera, municipio)
                if stats is None:
                    respuesta = {
                        "status": "error",
                        "error": "No se pudo conectar con la base de datos SNIES. Verifica que MySQL esté disponible."
                    }
                elif not stats.get("encontrado"):
                    respuesta = {
                        "status": "error",
                        "error": f"No se encontraron registros en el SNIES para '{carrera}'. Intenta con otro nombre (ej. 'Ingeniería de Sistemas')."
                    }
                else:
                    analisis = redactar_analisis_gemini(stats)
                    respuesta = {
                        "status": "ok",
                        "carrera": carrera,
                        "tipo": "SQL",
                        "respuesta": analisis,
                        "stats": {
                            "total_matriculados": stats["total_matriculados"],
                            "num_ies": stats["num_ies"],
                            "femenino": stats["femenino"],
                            "masculino": stats["masculino"],
                        }
                    }

                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(respuesta, ensure_ascii=False).encode('utf-8'))
            except subprocess.TimeoutExpired:
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "error": "La consulta a Lumina tardó demasiado (timeout). La base de datos puede estar ocupada; intenta de nuevo."
                }, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    with ReusableTCPServer(("", PORT), AdaHandler) as httpd:
        print(f"Servidor MinTIC - Ada corriendo en http://localhost:{PORT}")
        httpd.serve_forever()
