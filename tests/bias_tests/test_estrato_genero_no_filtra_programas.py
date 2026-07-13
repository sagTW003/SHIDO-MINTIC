"""Pruebas de equidad pendientes de implementar.

Objetivo (ver docs/public_impact_assessment.md): verificar que, ante perfiles
de usuario idénticos salvo por `estrato` o `genero`, Ada no reduzca
sistemáticamente el conjunto de programas académicos recomendados ni cambie
el tono del reporte de forma desalentadora para estratos bajos.

Esto requiere primero exponer la lógica de recomendación de Ada.py como una
función pura (hoy está acoplada al flujo CLI/web e invoca la API de Gemini),
para poder invocarla en pruebas sin red. Se deja como TODO explícito en lugar
de una prueba falsa que no verifique nada real.
"""
import pytest


@pytest.mark.skip(
    reason="TODO: refactorizar Ada.py para exponer la lógica de recomendación "
    "como función testeable sin llamadas de red, luego comparar outputs "
    "entre perfiles que solo difieren en estrato/genero."
)
def test_recomendaciones_no_dependen_de_estrato():
    ...


@pytest.mark.skip(reason="Ver TODO en test_recomendaciones_no_dependen_de_estrato")
def test_tono_reporte_no_dependen_de_genero():
    ...
