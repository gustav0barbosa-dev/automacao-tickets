# scripts/diagnostico_movimentacoes.py
import sqlite3
import pandas as pd

CAMINHO_DB = 'dados/tickets.db'

conn = sqlite3.connect(CAMINHO_DB)

print("=" * 60)
print("DIAGNÓSTICO DA TABELA MOVIMENTACOES (BANCO)")
print("=" * 60)

# 1. Colunas e amostra
df = pd.read_sql('SELECT * FROM movimentacoes LIMIT 10', conn)
print("\n=== COLUNAS ===")
print(df.columns.tolist())

print("\n=== AMOSTRA ===")
print(df[['ticket_id', 'data_movimentacao', 'autor', 'de_status', 'para_status']].to_string())

# 2. Contagens
total = pd.read_sql('SELECT COUNT(*) as n FROM movimentacoes', conn)['n'].iloc[0]
com_data = pd.read_sql(
    "SELECT COUNT(*) as n FROM movimentacoes WHERE data_movimentacao IS NOT NULL AND data_movimentacao != ''",
    conn
)['n'].iloc[0]
com_de = pd.read_sql(
    "SELECT COUNT(*) as n FROM movimentacoes WHERE de_status IS NOT NULL AND de_status != ''",
    conn
)['n'].iloc[0]
com_para = pd.read_sql(
    "SELECT COUNT(*) as n FROM movimentacoes WHERE para_status IS NOT NULL AND para_status != ''",
    conn
)['n'].iloc[0]

print("\n" + "=" * 60)
print("CONTAGENS")
print("=" * 60)
print(f"Total de movimentações : {total}")
print(f"Com data_movimentacao  : {com_data} ({com_data/total*100:.1f}%)")
print(f"Com de_status          : {com_de} ({com_de/total*100:.1f}%)")
print(f"Com para_status        : {com_para} ({com_para/total*100:.1f}%)")

# 3. Conta reaberturas
print("\n" + "=" * 60)
print("REABERTURAS DETECTADAS")
print("=" * 60)

query_reab = """
SELECT 
    ticket_id,
    COUNT(*) as reaberto_vezes,
    MIN(data_movimentacao) as primeira_reab,
    MAX(data_movimentacao) as ultima_reab
FROM movimentacoes
WHERE de_status IN ('Resolvido', 'Fechado')
  AND para_status IN ('Em atendimento', 'Aguardando confirmação do usuário')
GROUP BY ticket_id
ORDER BY reaberto_vezes DESC
"""
df_reab = pd.read_sql(query_reab, conn)
print(f"Tickets com reabertura : {len(df_reab)}")
print(f"Total de reaberturas   : {df_reab['reaberto_vezes'].sum() if not df_reab.empty else 0}")

if not df_reab.empty:
    print("\nTop 10 tickets mais reabertos:")
    print(df_reab.head(10).to_string(index=False))

conn.close()
print("\n" + "=" * 60)
print("FIM")
print("=" * 60)