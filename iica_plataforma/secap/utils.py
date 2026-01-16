from datetime import timedelta

def estado_actual_proyecto(proyecto, hoy):
    """
    Retorna el peor estado (0..4) de todos los indicadores
    en la semana actual.
    """
    peor_estado = 0

    for indicador in proyecto.indicadores.all():
        estado = calcular_estado_indicador(indicador, hoy)
        peor_estado = max(peor_estado, estado)

    return peor_estado


def estado_general_proyecto(proyecto, hoy, semanas_proyeccion=4):
    """
    Estado general del proyecto considerando:
    - Estado actual (base, nunca mejora)
    - Proyección cercana SOLO para empeorar el estado
    """

    estado_base = estado_actual_proyecto(proyecto, hoy)

    #Regla absoluta: si hoy es rojo, siempre será rojo
    if estado_base == 4:
        return 4

    peor_estado = estado_base

    fechas_futuras = [
        hoy + timedelta(weeks=i)
        for i in range(1, semanas_proyeccion + 1)
    ]

    for indicador in proyecto.indicadores.all():
        for fecha in fechas_futuras:
            estado_futuro = calcular_estado_indicador(indicador, fecha)

            # Nunca permitir "mejora"
            if estado_futuro > peor_estado:
                peor_estado = estado_futuro

            # Corte temprano si llega a rojo
            if peor_estado == 4:
                return 4

    return peor_estado

def calcular_estado_indicador(indicador, fecha_eval):
    """
    Calcula el estado (0..4) de un indicador en una fecha dada,
    basado en la PRIMERA meta incumplida.
    """

    # Metas ordenadas cronológicamente
    metas = indicador.metas.all().order_by("fecha")

    # Buscar la primera meta NO cumplida
    meta_incumplida = None
    for meta in metas:
        if indicador.valor_actual < meta.valor_objetivo:
            meta_incumplida = meta
            break

    # Si no hay metas incumplidas → todo bien
    if not meta_incumplida:
        return 0

    # Diferencia temporal respecto a ESA meta
    delta_dias = (meta_incumplida.fecha - fecha_eval).days

    # Estados según cercanía / atraso
    if delta_dias > 14:
        return 0      # Verde
    elif delta_dias > 7:
        return 1      # Verde lima
    elif delta_dias >= 0:
        return 2      # Amarillo
    else:
         # Meta ya vencida

        metas_restantes = [
            m for m in metas
            if m.fecha > meta_incumplida.fecha
            and indicador.valor_actual < m.valor_objetivo
        ]

        # ❗ Si NO hay otra meta incumplida → naranja
        if not metas_restantes:
            return 3  # Naranja

        # Tomamos la siguiente meta incumplida
        meta_proxima = metas_restantes[0]
        delta_dias_p = (meta_proxima.fecha - fecha_eval).days

        if delta_dias_p > 7:
            return 3  # Naranja
        return 4      # Rojo