# ============================================================
# Programa2.py - Filtragem e Preparação dos Tickets (CORRIGIDO v2)
# ============================================================
# https://gemini.google.com/app/45c75210d86b2270?hl=pt-BR
# https://gemini.google.com/app/a40df1f59bbeeda0?hl=pt-BR

import pandas as pd
from datetime import datetime, timedelta
import os
import traceback
from utils_help360 import filtrar_categoria, tratar_datas_excel


def processar_tickets():
    """Processa e filtra os tickets para acompanhamento, excluindo os já respondidos."""
    print("=" * 60)
    print("PROGRAMA 2 - FILTRAGEM DE TICKETS")
    print("=" * 60)

    # Pasta de Downloads (onde os outros arquivos já estão)
    pasta_downloads = os.path.join(os.path.expanduser('~'), 'Downloads')

    # Caminhos absolutos e consistentes
    caminho_origem = os.path.join(pasta_downloads, 'tickets.xlsx')
    caminho_respondido = os.path.join(pasta_downloads, 'tickets_com_respondido.xlsx')
    caminho_saida = os.path.join(pasta_downloads, 'acompanhamento.xlsx')

    # Fallback: se não existir em Downloads, tenta na pasta atual
    if not os.path.exists(caminho_origem):
        caminho_origem = 'tickets.xlsx'
    if not os.path.exists(caminho_respondido):
        caminho_respondido = 'tickets_com_respondido.xlsx'

    print(f"📂 Arquivo de tickets : {caminho_origem}")
    print(f"📂 Arquivo respondidos: {caminho_respondido}")
    print(f"💾 Arquivo de saída   : {caminho_saida}\n")

    try:
        # ==================== CARREGAR TICKETS ====================
        if not os.path.exists(caminho_origem):
            print(f"❌ Arquivo '{caminho_origem}' não encontrado.")
            print("   Execute o Programa1 (download) primeiro.")
            return

        print("📂 Carregando arquivo de tickets...")
        df = pd.read_excel(caminho_origem)

        # Validação de colunas obrigatórias
        colunas_obrigatorias = ['ID', 'Status', 'Alterado Data', 'Previsão', 'Responsável']
        colunas_faltando = [c for c in colunas_obrigatorias if c not in df.columns]
        if colunas_faltando:
            print(f"❌ Colunas obrigatórias ausentes em tickets.xlsx: {colunas_faltando}")
            print(f"   Colunas disponíveis: {list(df.columns)}")
            print("   💡 Verifique se o arquivo foi baixado corretamente pelo Programa1.")
            return

        # Tratar datas
        print("🔄 Convertendo datas...")
        df = tratar_datas_excel(df)

        print("Amostra de Alterado Data:")
        print(df[['ID', 'Alterado Data']].head(5).to_string(index=False))
        print(f"Tipos: {df['Alterado Data'].dtype}")
        print(f"Mínimo: {df['Alterado Data'].min()}")
        print(f"Máximo: {df['Alterado Data'].max()}\n")

        # ==================== CARREGAR RESPONDIDOS ====================
        df_resp = None
        if os.path.exists(caminho_respondido):
            print(f"📂 Carregando planilha de respondidos: {caminho_respondido}")
            df_resp = pd.read_excel(caminho_respondido)

            if 'Data Respondido' in df_resp.columns and 'ID' in df_resp.columns:
                df_resp['Data Respondido'] = pd.to_datetime(
                    df_resp['Data Respondido'], dayfirst=True, errors='coerce')
                df_resp['ID'] = df_resp['ID'].astype(str).str.strip()
                print(f"✅ Planilha de respondidos carregada: {len(df_resp)} registros")

                # Diagnóstico útil: quantos respondidos reais vieram
                respondidos_reais = df_resp['Data Respondido'].notna().sum()
                pendentes_reais = len(df_resp) - respondidos_reais
                print(f"   -> {respondidos_reais} com data, {pendentes_reais} sem data (pendentes)")
            else:
                print("⚠️ Coluna 'Data Respondido' ou 'ID' não encontrada. Ignorando filtro.")
                df_resp = None
        else:
            print(f"⚠️ '{caminho_respondido}' não encontrado. Continuando sem filtro de respondidos.")

        # ==================== DATAS DE REFERÊNCIA ====================
        hoje = pd.Timestamp.today().normalize()

        # Identifica o dia da semana (Sexta-feira = 4)
        if hoje.weekday() == 4:
            dias_postergar = 4
        else:
            dias_postergar = 2

        try:
            entrada = input('Digite a quantidade de dias para retroceder o filtro (ex.: 2): ').strip()
            dias_antecipar = int(entrada) if entrada else 1
        except (ValueError, EOFError):
            dias_antecipar = 1
            print(f"⚠️ Valor inválido. Usando padrão: {dias_antecipar}")

        # Datas de referência
        data_inicial_resolvido = hoje - timedelta(days=dias_antecipar)
        data_final_previsao = hoje + timedelta(days=dias_postergar) - timedelta(seconds=1)

        # Data mínima da Previsão - dinâmica (evita tickets muito antigos "Em atendimento")
        # 1 ano atrás, rolando automaticamente
        DATA_MINIMA_PREVISAO = hoje - pd.Timedelta(days=365)

        print(f"📅 Data inicial (alterações)    : {data_inicial_resolvido}")
        print(f"📅 Data final   (previsão)      : {data_final_previsao}")
        print(f"📅 Data mínima  (previsão)      : {DATA_MINIMA_PREVISAO}\n")

        # ==================== FILTROS ====================
        # Filtro 1: Status temporais (Resolvido / Aguardando confirmação)
        # IMPORTANTE: NÃO usa 'Previsão' aqui, pois esses status geralmente
        # vêm com a Previsão vazia. O critério é apenas 'Alterado Data'.
        regra_status_temporais = (
            df['Status'].isin(['Aguardando confirmação do usuário', 'Resolvido']) &
            (df['Alterado Data'] >= data_inicial_resolvido)
        )
        print(f"✅ Tickets com status temporais: {regra_status_temporais.sum()}")

        # Filtro 2: Em atendimento com previsão válida (dentro da janela)
        # Aqui SIM usa Previsão, porque é o campo que define o prazo.
        regra_em_atendimento = (
            (df['Status'] == 'Em atendimento') &
            (df['Previsão'] <= data_final_previsao) &
            (df['Previsão'] >= DATA_MINIMA_PREVISAO)
        )
        print(f"✅ Tickets em atendimento: {regra_em_atendimento.sum()}")

        # Juntar os dois filtros (OU)
        df_filtrado = df[regra_status_temporais | regra_em_atendimento].copy()
        print(f"📊 Total após filtros iniciais: {len(df_filtrado)}")

        # Filtro 3: Categorias que não são monitoradas
        df_filtrado = filtrar_categoria(df_filtrado)
        print(f"📊 Total após filtro de categorias: {len(df_filtrado)}")

        # ==================== VERIFICAR RESPONDIDOS ====================
        # Regra de negócio:
        #   - Ticket SEM Data Respondido (NaN) → DEVE SER ABERTO
        #     (ainda não foi respondido, ou não está na Tabela fato)
        #   - Ticket COM Data Respondido > Alterado Data → DEVE SER REMOVIDO
        #     (já foi respondido e não teve nova movimentação)
        #   - Ticket COM Data Respondido <= Alterado Data → DEVE SER MANTIDO
        #     (foi respondido, mas voltou a ter movimentação)
        # ================================================================
        if df_resp is not None and not df_resp.empty:
            # Padronizar tipo do ID para o merge - AMBOS OS LADOS
            df_filtrado['ID'] = df_filtrado['ID'].astype(str).str.strip()
            df_resp['ID'] = df_resp['ID'].astype(str).str.strip()

            df_filtrado = df_filtrado.merge(
                df_resp[['ID', 'Data Respondido']], on='ID', how='left')

            antes = len(df_filtrado)

            # Diagnóstico: quantos em cada categoria
            sem_data = df_filtrado['Data Respondido'].isna().sum()
            resp_antes = (
                df_filtrado['Data Respondido'].notna() &
                (df_filtrado['Data Respondido'] <= df_filtrado['Alterado Data'])
            ).sum()
            resp_depois = (
                df_filtrado['Data Respondido'].notna() &
                (df_filtrado['Data Respondido'] > df_filtrado['Alterado Data'])
            ).sum()

            print(f"   ├─ Sem Data Respondido (abrir)           : {sem_data}")
            print(f"   ├─ Respondidos antes da alteração (abrir): {resp_antes}")
            print(f"   └─ Respondidos após a alteração (fechar) : {resp_depois}")

            # Aplica o filtro
            df_filtrado = df_filtrado[
                (df_filtrado['Data Respondido'].isna()) |
                (df_filtrado['Data Respondido'] <= df_filtrado['Alterado Data'])
            ].copy()

            removidos = antes - len(df_filtrado)
            df_filtrado.drop(columns=['Data Respondido'], inplace=True)
            print(f"📊 Total após filtro de respondidos: {len(df_filtrado)} (removidos: {removidos})")
        else:
            print("⚠️ Sem planilha de respondidos válida. TODOS os tickets filtrados serão mantidos.")

        # ==================== ORDENAR ====================
        if 'Responsável' in df_filtrado.columns:
            df_filtrado = df_filtrado.sort_values(by='Responsável')

        # ==================== SALVAR ====================
        print(f"\n💾 Salvando arquivo em: {caminho_saida}")
        df_filtrado.to_excel(caminho_saida, index=False)

        if os.path.exists(caminho_saida):
            tamanho_kb = os.path.getsize(caminho_saida) / 1024
            print(f"✅ Arquivo 'acompanhamento.xlsx' gerado com sucesso! ({tamanho_kb:.1f} KB, {len(df_filtrado)} linhas)")
        else:
            print("❌ ERRO: O arquivo não foi criado. Verifique permissões da pasta.")

    except FileNotFoundError as e:
        print(f"❌ Arquivo não encontrado: {e}")
        print("   Execute o Programa0 ou Programa1 primeiro.")
    except Exception as e:
        print(f"\n❌ Erro durante o processamento: {e}")
        print("\n🔍 Traceback completo:")
        traceback.print_exc()


if __name__ == "__main__":
    processar_tickets()