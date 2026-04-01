"""
Simulador de Filas G/G/c/K
===========================
Gerador MCL + Simulação orientada a eventos (discrete-event simulation).
 
Configurações simuladas:
  1) G/G/1/5 — 1 servidor, capacidade 5, chegadas U[2,5], atendimento U[3,5]
  2) G/G/2/5 — 2 servidores, capacidade 5, chegadas U[2,5], atendimento U[3,5]
 
Condições:
  • Fila inicialmente vazia
  • Primeiro cliente chega no tempo 2.0 (sem consumir número aleatório)
  • Simulação encerra ao consumir o 100.000º número pseudoaleatório
"""
 
import heapq
 
# =====================================================================
# 1. GERADOR DE NÚMEROS PSEUDOALEATÓRIOS — Método Congruente Linear
# =====================================================================
_MCL_a    = 1_664_525       # multiplicador
_MCL_c    = 1_013_904_223   # incremento
_MCL_M    = 2**32           # módulo
_MCL_prev = 12_345          # semente inicial
_MCL_used = 0               # contador de aleatórios consumidos
 
def reset_lcg(seed: int = 12_345) -> None:
    """Reinicia o gerador com a semente dada."""
    global _MCL_prev, _MCL_used
    _MCL_prev = seed
    _MCL_used = 0
 
def NextRandom() -> float:
    """
    Gera o próximo número pseudoaleatório normalizado em [0, 1).
    Armazena o último valor gerado (_MCL_prev) e incrementa o contador.
    """
    global _MCL_prev, _MCL_used
    _MCL_prev = (_MCL_a * _MCL_prev + _MCL_c) % _MCL_M
    _MCL_used += 1
    return _MCL_prev / _MCL_M
 
def randoms_used() -> int:
    return _MCL_used
 
def uniform(lo: float, hi: float) -> float:
    """Distribuição Uniforme no intervalo [lo, hi] via inversão."""
    return lo + (hi - lo) * NextRandom()
 
 
# =====================================================================
# 2. NÚCLEO DO SIMULADOR G/G/c/K
# =====================================================================
_CHEGADA = 0   # tipo de evento: chegada
_SAIDA   = 1   # tipo de evento: saída (fim de atendimento)
 
def simular(
    num_servers: int,           # número de servidores (c)
    K: int,                     # capacidade total do sistema
    arrival_lo: float,          # limite inferior do intervalo de chegada
    arrival_hi: float,          # limite superior do intervalo de chegada
    service_lo: float,          # limite inferior do tempo de atendimento
    service_hi: float,          # limite superior do tempo de atendimento
    max_randoms: int = 100_000, # limite de números pseudoaleatórios
    seed: int = 12_345,         # semente do gerador
    first_arrival: float = 2.0, # tempo fixo do primeiro cliente
) -> dict:
    """
    Executa a simulação e retorna as estatísticas coletadas.
 
    Escalonador: min-heap ordenado por tempo de evento.
    Estados: 0..K (número de clientes no sistema em cada instante).
    """
    reset_lcg(seed)
 
    n            = 0            # clientes no sistema (estado atual)
    t            = 0.0          # relógio de simulação
    perdas       = 0            # clientes rejeitados por fila cheia
    heap         = []           # escalonador de eventos
    tempo_estados = [0.0] * (K + 1)   # tempo acumulado em cada estado
 
    # Agenda o primeiro cliente sem consumir aleatório
    heapq.heappush(heap, (first_arrival, _CHEGADA))
 
    # ── Loop principal ─────────────────────────────────────────────
    # Continua enquanto houver aleatórios disponíveis E eventos agendados
    while randoms_used() < max_randoms and heap:
        evt_t, tipo = heapq.heappop(heap)
 
        # Acumula o tempo decorrido no estado n antes de avançar o relógio
        tempo_estados[n] += evt_t - t
        t = evt_t
 
        # ── Procedimento CHEGADA ──────────────────────────────────
        if tipo == _CHEGADA:
            # Sempre agenda a próxima chegada
            heapq.heappush(heap, (t + uniform(arrival_lo, arrival_hi), _CHEGADA))
 
            if n < K:                     # há espaço no sistema
                n += 1
                if n <= num_servers:      # servidor livre → inicia atendimento
                    heapq.heappush(heap, (t + uniform(service_lo, service_hi), _SAIDA))
            else:                         # fila cheia → cliente perdido
                perdas += 1
 
        # ── Procedimento SAIDA ────────────────────────────────────
        else:
            n -= 1
            # Se havia fila, o próximo cliente começa a ser atendido
            if n >= num_servers:
                heapq.heappush(heap, (t + uniform(service_lo, service_hi), _SAIDA))
 
    tempo_global = sum(tempo_estados)
    return {
        'tempo_global'   : tempo_global,
        'tempo_estados'  : tempo_estados,
        'perdas'         : perdas,
        'randoms_usados' : randoms_used(),
    }
 
# =====================================================================
# 3. RELATÓRIO DE RESULTADOS (FORMATO SIMPLES)
# =====================================================================
def imprimir_resultados_simples(nome_fila: str, arr_lo: float, arr_hi: float, serv_lo: float, serv_hi: float, res: dict, K: int) -> None:
    tg = res['tempo_global']
    te = res['tempo_estados']
    perdas = res['perdas']

    print("*" * 54)
    print(f"Queue:    {nome_fila}")
    print(f"Arrival: {arr_lo:.1f} ... {arr_hi:.1f}")
    print(f"Service: {serv_lo:.1f} ... {serv_hi:.1f}")
    print("*" * 54)
    print("  State           Time        Probability")

    for i in range(K + 1):
        p = (te[i] / tg * 100) if tg > 0 else 0.0
        # Formatando para alinhar perfeitamente com o exemplo da imagem
        print(f"{i:>7}     {te[i]:10.4f}         {p:>5.2f}%")

    print(f"\nNumber of losses: {perdas}\n")


# =====================================================================
# 4. MAIN
# =====================================================================
if __name__ == "__main__":
    # ── Simulação 1: G/G/1/5 ─────────────────────────────────────
    res_gg15 = simular(
        num_servers=1, K=5,
        arrival_lo=2.0, arrival_hi=5.0,
        service_lo=3.0, service_hi=5.0,
    )
    imprimir_resultados_simples("Queue1 (G/G/1/5)", 2.0, 5.0, 3.0, 5.0, res_gg15, 5)

    # ── Simulação 2: G/G/2/5 ─────────────────────────────────────
    res_gg25 = simular(
        num_servers=2, K=5,
        arrival_lo=2.0, arrival_hi=5.0,
        service_lo=3.0, service_hi=5.0,
    )
    imprimir_resultados_simples("Queue2 (G/G/2/5)", 2.0, 5.0, 3.0, 5.0, res_gg25, 5)