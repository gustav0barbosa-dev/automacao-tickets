# ============================================================
# main_teste.py - Versão de TESTE (DRY-RUN) do Pipeline
# ============================================================
# Usa os arquivos JÁ EXISTENTES na pasta Downloads do Windows:
#   - tickets.xlsx
#   - tickets_com_respondido.xlsx
#
# NÃO gera esses arquivos, apenas os LÊ.
# NÃO faz login, NÃO baixa nada, NÃO abre abas.
# Gera apenas 'acompanhamento_teste.xlsx' para inspeção.
# ============================================================

import pandas as pd
import os
from datetime import datetime, timedelta

# ============================================================
# CONFIGURAÇÕES DO TESTE
# ============================================================
PASTA_DOWNLOADS = os.path.join(os.path.expanduser('~'), 'Downloads')

# Arquivos de ENTRADA (lidos da pasta Downloads do Windows)
CAMINHO_TICKETS = os.path.join(PASTA_DOWNLOADS, 'tickets.xlsx')
CAMINHO_RESPONDIDOS = os.path.join(PASTA_DOWNLOADS, 'tickets_com_respondido.xlsx')

# Arquivo de SAÍDA (gerado na pasta atual do script)
ARQUIVO_ACOMPANHAMENTO = 'acompanhamento_teste.xlsx'

# Simula a resposta do input() do Programa2
DIAS_ANTECIPAR_SIMULADO = 2

# ============================================================
# FUNÇÕES AUXILIARES (cópias de utils_help360 sem Selenium)
# ============================================================
DATA_COLUNAS = [
    'Criado Data', 'Alterado Data', 'Previsão',
    'Data do Resolvido', 'Data do 1°resolvido'
]

CATEGORIAS_FORA = [
    '1ª Etapa Censo', 'Alteração de Grupo de Pagamento', 'Alterações Bancárias',
    'Aplicações Folha', 'Cancelar Protocolo', 'Cálculo da Média',
    'Consignatárias', 'Deploy - Homologação', 'Extinção', 'Folha de Pagamento',
    'Monitoramento Folha', 'Parametrização Folha', 'Processamento Folha',
    'Reabertura de Protocolo', 'Reajuste', 'Recadastramento', 'Reenvio Bancário',
    'Reprocessamento Folha', 'Retorno de Tarefa ', 'Rubricas',
    'Rubricas Judiciais Base Duplicadas', 'Rúbricas Concomitantes', 'Task',
    'Vínculos', 'Visita domiciliar'
]


def tratar_datas_excel(df, colunas=DATA_COLUNAS):
    for coluna in colunas:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(df[coluna], dayfirst=True, errors='coerce')
    return df


def filtrar_categoria(df, categorias=CATEGORIAS_FORA):
    if 'Categoria' in df.columns:
        df = df[~df['Categoria'].isin(categorias)]
    return df


def verificar_arquivos_entrada():
    """Verifica se os arquivos necessários existem na pasta Downloads."""
    print("=" * 60)
    print("VERIFICAÇÃO DOS ARQUIVOS DE ENTRADA")
    print("=" * 60)
    print(f"📁 Pasta Downloads: {PASTA_DOWNLOADS}\n")

    ok = True
    for caminho in [CAMINHO_TICKETS, CAMINHO_RESPONDIDOS]:
        if os.path.exists(caminho):
            tamanho_kb = os.path.getsize(caminho) / 1024
            modif = datetime.fromtimestamp(os.path.getmtime(caminho))
            print(f"✅ {os.path.basename(caminho)}")
            print(f"   ├─ Tamanho: {tamanho_kb:.1f} KB")
            print(f"   └─ Modificado em: {modif:%d/%m/%Y %H:%M:%S}")
        else:
            print(f"❌ {os.path.basename(caminho)} NÃO ENCONTRADO em Downloads")
            ok = False
    print()
    return ok


# ============================================================
# ETAPA 2: FILTRAGEM (mesma lógica do Programa2, sem input)
# ============================================================
def etapa2_filtrar():
    print("=" * 60)
    print("ETAPA 2 - FILTRAGEM DE TICKETS")
    print("=" * 60)
    print(f"📂 Carregando: {CAMINHO_TICKETS}")
    df = pd.read_excel(CAMINHO_TICKETS)
    print(f"   Total bruto: {len(df)} linhas, {len(df.columns)} colunas")
    print(f"   Colunas: {list(df.columns)}\n")

    df = tratar_datas_excel(df)

    print("Amostra de datas:")
    print(df[['ID', 'Alterado Data']].head(5).to_string(index=False))
    print(f"   Tipos: {df['Alterado Data'].dtype}")
    print(f"   Mínimo: {df['Alterado Data'].min()}")
    print(f"   Máximo: {df['Alterado Data'].max()}\n")

    # ---- Carregar respondidos ----
    df_resp = None
    if os.path.exists(CAMINHO_RESPONDIDOS):
        print(f"📂 Carregando: {CAMINHO_RESPONDIDOS}")
        df_resp = pd.read_excel(CAMINHO_RESPONDIDOS)
        if 'Data Respondido' in df_resp.columns:
            df_resp['Data Respondido'] = pd.to_datetime(
                df_resp['Data Respondido'], dayfirst=True, errors='coerce')
            resp = df_resp['Data Respondido'].notna().sum()
            print(f"   Total: {len(df_resp)} registros ({resp} com data, {len(df_resp)-resp} sem data)\n")
        else:
            print("   ⚠️ Coluna 'Data Respondido' não encontrada. Ignorando filtro.\n")
            df_resp = None

    # ---- Datas de referência ----
    hoje = pd.Timestamp.today().normalize()
    dias_postergar = 4 if hoje.weekday() == 4 else 2
    dias_antecipar = DIAS_ANTECIPAR_SIMULADO

    data_inicial_resolvido = hoje - timedelta(days=dias_antecipar)
    data_final_previsao = hoje + timedelta(days=dias_postergar) - timedelta(seconds=1)

    print(f"📅 Hoje                     : {hoje:%d/%m/%Y}")
    print(f"📅 Data inicial (alterações): {data_inicial_resolvido:%d/%m/%Y}")
    print(f"📅 Data final   (previsão)  : {data_final_previsao:%d/%m/%Y %H:%M:%S}\n")

    # ---- Filtro 1: status temporais ----
    regra_temporais = (
        df['Status'].isin(['Aguardando confirmação do usuário', 'Resolvido']) &
        (df['Alterado Data'] >= data_inicial_resolvido)
    )
    print(f"✅ Tickets com status temporais: {regra_temporais.sum()}")

    # ---- Filtro 2: em atendimento com previsão ----
    data_inicial_atendimento = pd.to_datetime('2025-01-01')
    regra_atendimento = (
        (df['Status'] == 'Em atendimento') &
        (df['Previsão'] <= data_final_previsao) &
        (df['Previsão'] > data_inicial_atendimento)
    )
    print(f"✅ Tickets em atendimento: {regra_atendimento.sum()}")

    df_filtrado = df[regra_temporais | regra_atendimento].copy()
    print(f"📊 Total após filtros iniciais: {len(df_filtrado)}")

    df_filtrado = filtrar_categoria(df_filtrado)
    print(f"📊 Total após filtro de categorias: {len(df_filtrado)}")

    # ---- Filtro de respondidos ----
    if df_resp is not None and not df_resp.empty:
        df_filtrado = df_filtrado.merge(
            df_resp[['ID', 'Data Respondido']], on='ID', how='left')

        antes = len(df_filtrado)
        df_filtrado = df_filtrado[
            (df_filtrado['Data Respondido'].isna()) |
            (df_filtrado['Data Respondido'] <= df_filtrado['Alterado Data'])
        ].copy()
        removidos = antes - len(df_filtrado)
        print(f"📊 Total após filtro de respondidos: {len(df_filtrado)} (removidos: {removidos})")

        df_filtrado.drop(columns=['Data Respondido'], inplace=True)

    df_filtrado = df_filtrado.sort_values(by='Responsável')
    df_filtrado.to_excel(ARQUIVO_ACOMPANHAMENTO, index=False)
    print(f"\n✅ '{ARQUIVO_ACOMPANHAMENTO}' gerado ({len(df_filtrado)} linhas)")
    return df_filtrado


# ============================================================
# ETAPA 3: SIMULAÇÃO DE ABERTURA (mock do Programa3)
# ============================================================
def etapa3_simular_abertura():
    print("\n" + "=" * 60)
    print("ETAPA 3 - ABERTURA DE TICKETS (SIMULADA - NENHUMA ABA SERÁ ABERTA)")
    print("=" * 60)
    if not os.path.exists(ARQUIVO_ACOMPANHAMENTO):
        print(f"❌ '{ARQUIVO_ACOMPANHAMENTO}' não encontrado. Rode a Etapa 2 primeiro.")
        return

    df = pd.read_excel(ARQUIVO_ACOMPANHAMENTO)
    status_monitorados = ['Em atendimento', 'Resolvido', 'Aguardando confirmação do usuário']

    total_geral = 0
    for status in status_monitorados:
        sub = df[df['Status'] == status]
        print(f"\n{'=' * 80}")
        print(f"STATUS: {status}  ({len(sub)} tickets)")
        print('=' * 80)
        if sub.empty:
            print("  (nenhum)")
            continue
        for _, linha in sub.iterrows():
            tid = linha['ID']
            url = f'https://spprev.help360.com.br/tickets/{tid}'
            resp = linha.get('Responsável', 'N/A')
            alter = linha.get('Alterado Data', 'N/A')
            if isinstance(alter, pd.Timestamp):
                alter = alter.strftime('%d/%m/%Y %H:%M')
            print(f"  🎫 Ticket {tid:<10} | Resp: {str(resp):<20} | Alterado: {alter}")
            print(f"     ↪ URL: {url}")
        total_geral += len(sub)

    print(f"\n📊 TOTAL DE TICKETS QUE SERIAM ABERTOS: {total_geral}")


# ============================================================
# ORQUESTRADOR
# ============================================================
def main():
    print("╔" + "═" * 58 + "╗")
    print("║" + " PIPELINE HELP360 - MODO TESTE (DRY-RUN) ".center(58) + "║")
    print("║" + " Lê de Downloads | Sem login | Sem abrir abas ".center(58) + "║")
    print("╚" + "═" * 58 + "╝\n")

    # Verifica arquivos de entrada
    if not verificar_arquivos_entrada():
        print("❌ Arquivo(s) de entrada não encontrado(s) na pasta Downloads.")
        print("   Rode o Programa0/Programa1 em produção primeiro para gerá-los.")
        return

    # ETAPA 2: Filtrar (usa os arquivos já existentes)
    etapa2_filtrar()

    # ETAPA 3: Simular abertura
    etapa3_simular_abertura()

    print("\n" + "=" * 60)
    print("✅ TESTE CONCLUÍDO!")
    print("=" * 60)
    print("\nArquivo gerado para inspeção:")
    if os.path.exists(ARQUIVO_ACOMPANHAMENTO):
        print(f"  📄 {ARQUIVO_ACOMPANHAMENTO}  ({os.path.getsize(ARQUIVO_ACOMPANHAMENTO)} bytes)")
    print(f"\n💡 Os arquivos de entrada foram lidos de:")
    print(f"   • {CAMINHO_TICKETS}")
    print(f"   • {CAMINHO_RESPONDIDOS}")
    print(f"\n   Nenhum deles foi modificado.")


if __name__ == "__main__":
    main()