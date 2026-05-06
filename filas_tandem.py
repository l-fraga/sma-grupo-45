import heapq

# =====================================================================
# 1. GERADOR DE NÚMEROS PSEUDOALEATÓRIOS (MCL)
# =====================================================================
class StopSimulation(Exception):
    """Exceção levantada quando atingimos o limite de números aleatórios."""
    pass

_a = 1664525
_c = 1013904223
_m = 2**32
_seed = 12345
_rnd_used = 0
_MAX_RND = 100000

def reset_generator():
    global _seed, _rnd_used
    _seed = 12345
    _rnd_used = 0

def rnd():
    """Gera número [0, 1) e controla a condição de parada."""
    global _seed, _rnd_used
    if _rnd_used >= _MAX_RND:
        raise StopSimulation()
    _seed = (_a * _seed + _c) % _m
    _rnd_used += 1
    return _seed / _m

def uniform(min_val, max_val):
    return min_val + (max_val - min_val) * rnd()


# =====================================================================
# 2. CONFIGURAÇÃO DA REDE (TOPOLOGIA GENÉRICA)
# =====================================================================
config_rede = {
    # Define os parâmetros estruturais de cada fila
    "filas": {
        "q1": {"servidores": 1, "capacidade": 1, "atend_min": 1.0, "atend_max": 2.0},
        "q2": {"servidores": 2, "capacidade": 5, "atend_min": 4.0, "atend_max": 6.0},
        "q3": {"servidores": 2, "capacidade": 10, "atend_min": 5.0, "atend_max": 15.0}
    },
    
    # Define quais filas recebem clientes de "fora" do sistema
    "chegadas_externas": {
        "q1": {"cheg_min": 2.0, "cheg_max": 4.0, "primeira_chegada": 2.0}
    },
    
    # Define para onde o cliente vai após o atendimento (Matriz de Probabilidades)
    "roteamento": {
        "q1": [
            {"destino": "q2", "prob": 0.8},
            {"destino": "q3", "prob": 0.2}
        ],
        "q2": [
            {"destino": "q1", "prob": 0.3},
            {"destino": "q2", "prob": 0.5},
            {"destino": "OUT", "prob": 0.2}
        ],
        "q3": [
            {"destino": "q3", "prob": 0.7},
            {"destino": "OUT", "prob": 0.3}
        ]
    }
}


# =====================================================================
# 3. NÚCLEO DO SIMULADOR DE REDES
# =====================================================================
def simular_rede(config):
    reset_generator()
    
    # Tipos de Eventos
    CHEGADA_EXTERNA = 1
    CHEGADA_INTERNA = 2  # Chegada proveniente de outra fila
    SAIDA = 3
    
    filas_cfg = config["filas"]
    
    # Inicialização de Variáveis de Estado Dinâmicas
    estado = {fid: 0 for fid in filas_cfg}
    perdas = {fid: 0 for fid in filas_cfg}
    tempos = {fid: [0.0] * (filas_cfg[fid]["capacidade"] + 1) for fid in filas_cfg}
    
    heap = []
    t_atual = 0.0
    
    # Agenda as primeiras chegadas externas baseadas na configuração
    for fid, cfg in config["chegadas_externas"].items():
        t_inicial = cfg.get("primeira_chegada", uniform(cfg["cheg_min"], cfg["cheg_max"]))
        heapq.heappush(heap, (t_inicial, CHEGADA_EXTERNA, fid))
        
    try:
        while heap:
            t_evento, tipo, fid = heapq.heappop(heap)
            
            # 1. Atualiza os acumuladores de tempo de TODAS as filas
            delta = t_evento - t_atual
            for fila_id in filas_cfg:
                tempos[fila_id][estado[fila_id]] += delta
            t_atual = t_evento
            
            # 2. Tratamento dos Eventos
            if tipo == CHEGADA_EXTERNA:
                # Agenda a próxima chegada de fora
                cfg_ch = config["chegadas_externas"][fid]
                prox_chegada = t_atual + uniform(cfg_ch["cheg_min"], cfg_ch["cheg_max"])
                heapq.heappush(heap, (prox_chegada, CHEGADA_EXTERNA, fid))
                
                # Trata o cliente chegando
                if estado[fid] < filas_cfg[fid]["capacidade"]:
                    estado[fid] += 1
                    if estado[fid] <= filas_cfg[fid]["servidores"]:
                        t_saida = t_atual + uniform(filas_cfg[fid]["atend_min"], filas_cfg[fid]["atend_max"])
                        heapq.heappush(heap, (t_saida, SAIDA, fid))
                else:
                    perdas[fid] += 1
                    
            elif tipo == CHEGADA_INTERNA:
                # Vem de outra fila: não agenda nova chegada externa, só processa a entrada
                if estado[fid] < filas_cfg[fid]["capacidade"]:
                    estado[fid] += 1
                    if estado[fid] <= filas_cfg[fid]["servidores"]:
                        t_saida = t_atual + uniform(filas_cfg[fid]["atend_min"], filas_cfg[fid]["atend_max"])
                        heapq.heappush(heap, (t_saida, SAIDA, fid))
                else:
                    perdas[fid] += 1
                    
            elif tipo == SAIDA:
                # Libera o cliente da fila atual
                estado[fid] -= 1
                if estado[fid] >= filas_cfg[fid]["servidores"]:
                    t_saida = t_atual + uniform(filas_cfg[fid]["atend_min"], filas_cfg[fid]["atend_max"])
                    heapq.heappush(heap, (t_saida, SAIDA, fid))
                    
                # Roteamento: Decide o destino baseado nas probabilidades
                rotas = config["roteamento"].get(fid, [])
                r = rnd() # Sorteia [0, 1) para a probabilidade
                acc = 0.0
                destino = "OUT"
                
                for rota in rotas:
                    acc += rota["prob"]
                    if r <= acc:
                        destino = rota["destino"]
                        break
                
                # Se o destino for outra fila, agenda uma CHEGADA_INTERNA no instante atual
                if destino != "OUT":
                    heapq.heappush(heap, (t_atual, CHEGADA_INTERNA, destino))

    except StopSimulation:
        pass # Simulação encerra limpa no limite de números aleatórios
        
    return t_atual, tempos, perdas


# =====================================================================
# 4. IMPRESSÃO DE RESULTADOS
# =====================================================================
def imprimir_resultados(t_global, tempos, perdas, config):
    for fid, cfg in config["filas"].items():
        print("\n------------- Queue Information ---------------")
        print(f"Queue: (G/G/{cfg['servidores']}/{cfg['capacidade']})")
        
        # Verifica se a fila recebe chegadas externas para imprimir
        if fid in config["chegadas_externas"]:
            ch = config["chegadas_externas"][fid]
            print(f"Arrivals between: {ch['cheg_min']:.1f} ... {ch['cheg_max']:.1f}")
        else:
            print("Arrivals between: Routed from network")
            
        print(f"Service between: {cfg['atend_min']:.1f} ... {cfg['atend_max']:.1f}")
        print("-------------- Time Distribution ---------------")
        
        for i, t in enumerate(tempos[fid]):
            p = (t / t_global * 100) if t_global > 0 else 0
            print(f"{i}: {t:.2f} ({p:.2f}%)")

        print("------------- Lost Clients --------------")
        print(f"Lost Clients: {perdas[fid]}")
        print("-------- Simulation Time ----------")
        print(f"Total Time: {t_global:.2f}")
        print("=================================================================")

    print("Total Simulation Time: {:.2f}".format(t_global))

# =====================================================================
# MAIN
# =====================================================================
if __name__ == "__main__":
    tempo_global, estado_tempos, quant_perdas = simular_rede(config_rede)
    imprimir_resultados(tempo_global, estado_tempos, quant_perdas, config_rede)