"""
Testa a anonimização com dados CRUS (sem anonimização prévia).
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))

from utils_anonimizacao import anonimizar_texto

# Textos CRUS (com CPF, telefone, nome)
textos = [
    "Alteração Conta Corrente - MARIA CLARICE ALVES DOS SANTOS - Protocolo 80616766 - CPF: 123.456.789-00",
    "No protocolo 80616766, ao tentar abrir a tarefa...",
    "Reenvio de pagamento para João Silva, CPF 987.654.321-00, tel (11) 98765-4321",
    "CPF 15010467801 - ERRO NO SISTEMA",
    "Reenvio bancário para Maria Santos - protocolo 80616766",
]

print('=' * 80)
print('TESTE DE ANONIMIZAÇÃO (dados CRUS)')
print('=' * 80)

for i, texto in enumerate(textos):
    resultado = anonimizar_texto(texto)
    print(f'\n[{i}] ANTES:  {texto}')
    print(f'    DEPOIS: {resultado}')