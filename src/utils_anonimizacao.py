# ============================================================
# src/utils_anonimizacao.py — Anonimização LGPD (v3)
# ============================================================
"""
Anonimização de dados pessoais de TERCEIROS.

MUDANÇA v3: SUBSTITUIÇÃO INTELIGENTE
  - CPF → 00000000000 (mantém tamanho)
  - CNPJ → 00000000000000
  - E-mail → email@exemplo.com
  - Telefone → 0000000000
  - Nomes → M.C.A.S. (iniciais)
  - PROTOCOLOS SÃO PRESERVADOS (importantes para busca)

MUDANÇA v4: Adicionado CAMPOS_POR_TABELA para migração SQLite→PostgreSQL
"""
import re


# ==================== PADRÕES DE DOCUMENTOS ====================
PADROES_DOCUMENTOS = {
    'CPF': re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'),
    'CNPJ': re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b'),
    'EMAIL': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
    'TELEFONE': re.compile(
        r'\(?\d{2}\)?\s?'         # DDD (obrigatório)
        r'(?:9\d{4}|\d{4})'       # 9XXXX ou XXXX
        r'[-\s]?\d{4}'            # XXXX
    ),
    'RG': re.compile(r'\b\d{1,2}\.\d{3}\.\d{3}-?[\dXx]\b'),
    'PIS': re.compile(r'\b\d{3}\.\d{5}\.\d{2}-?\d\b'),
    'TITULO_ELEITOR': re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b'),
}

# ⬇️ MÁSCARAS NUMÉRICAS (mantêm estrutura)
MASCARAS = {
    'CPF': '00000000000',
    'CNPJ': '00000000000000',
    'EMAIL': 'email@exemplo.com',
    'TELEFONE': '0000000000',
    'RG': '0000000',
    'PIS': '00000000000',
    'TITULO_ELEITOR': '0000 0000 0000',
}


# ==================== PADRÕES DE NOMES ====================
STOPWORDS_NOMES = {
    'DE', 'DA', 'DO', 'DAS', 'DOS', 'E', 'A', 'O',
    'EM', 'PARA', 'COM', 'POR', 'SOBRE', 'SEM', 'AO', 'AOS',
    # Palavras de negócio
    'TICKET', 'TICKETS', 'TASK', 'PROBLEMA', 'ERRO', 'FALHA',
    'SOLICITAÇÃO', 'SOLICITACAO', 'ATENDIMENTO', 'REATIVAÇÃO', 'REATIVACAO',
    'CANCELAMENTO', 'CRIAÇÃO', 'CRIACAO', 'ANÁLISE', 'ANALISE',
    'REENVIO', 'ENVIO', 'PAGAMENTO', 'PAGAMENTOS', 'BENEFÍCIO', 'BENEFICIO',
    'BENEFICIÁRIO', 'BENEFICIARIO', 'EMPRÉSTIMO', 'EMPRESTIMO',
    'APOSENTADORIA', 'PENSÃO', 'PENSAO', 'AUXÍLIO', 'AUXILIO',
    'AÇÃO', 'ACAO', 'JUDICIAL', 'PROCESSO', 'RECURSO', 'PROTOCOLO',
    'INCLUSÃO', 'INCLUSAO', 'EXCLUSÃO', 'EXCLUSAO',
    'ALTERAÇÃO', 'ALTERACAO', 'CORREÇÃO', 'CORRECAO', 'REVISÃO', 'REVISAO',
    'CADASTRO', 'DADOS', 'INFORMAÇÃO', 'INFORMACAO', 'DOCUMENTO', 'DOCUMENTOS',
    'BANCO', 'AGÊNCIA', 'AGENCIA', 'CONTA', 'CONTRATO', 'SISTEMA',
    'PRODESP', 'SIGEPREV', 'SPPREV', 'DTR', 'DIPM', 'FALA', 'SP',
    'URGENTE', 'ALTA', 'MÉDIA', 'MEDIA', 'BAIXA', 'CRÍTICA', 'CRITICA',
    'NOVO', 'NOVA', 'ANTIGO', 'ANTIGA', 'PRIMEIRO', 'SEGUNDO',
    'TODOS', 'TODAS', 'NENHUM', 'NENHUMA', 'ALGUM', 'ALGUMA',
    'NÃO', 'NAO', 'SIM', 'OK',
    'HTTP', 'HTTPS', 'WWW', 'PDF', 'XLSX', 'DOCX', 'PNG', 'JPG',
}

PADRAO_NOME_CAIXA_ALTA = re.compile(
    r'\b[A-ZÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ]{2,}'
    r'(?:\s+(?:DE|DA|DO|DAS|DOS|E\s+)?[A-ZÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ]{2,}){1,5}\b'
)

PADRAO_NOME_TITLE_CASE = re.compile(
    r'(?<=[@\s])([A-ZÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ][a-záàâãäéèêëíìîïóòôõöúùûüç]+'
    r'(?:\s+(?:de|da|do|das|dos|e\s+)?[A-ZÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ][a-záàâãäéèêëíìîïóòôõöúùûüç]+){1,4})'
)


def anonimizar_nomes_caixa_alta(texto: str) -> str:
    """Anonimiza nomes em CAIXA ALTA, MANTENDO AS INICIAIS."""
    if not texto:
        return texto

    def substituir(match):
        nome = match.group(0)
        palavras = nome.split()
        palavras_reais = [p for p in palavras if p.upper() not in STOPWORDS_NOMES]
        if len(palavras_reais) < 2:
            return nome
        # ⬇️ MANTÉM AS INICIAIS: "MARIA CLARICE" → "M. C."
        iniciais = ' '.join(p[0] + '.' for p in palavras_reais)
        return iniciais

    return PADRAO_NOME_CAIXA_ALTA.sub(substituir, texto)


def anonimizar_nomes_title_case(texto: str) -> str:
    """Anonimiza nomes em Title Case, MANTENDO AS INICIAIS."""
    if not texto:
        return texto

    def substituir(match):
        nome = match.group(1)
        palavras = nome.split()
        palavras_reais = [p for p in palavras if p.upper() not in STOPWORDS_NOMES]
        if len(palavras_reais) < 2:
            return match.group(0)
        iniciais = ' '.join(p[0] + '.' for p in palavras_reais)
        return iniciais

    return PADRAO_NOME_TITLE_CASE.sub(substituir, texto)


def remover_nomes_de_arquivos(texto: str) -> str:
    """Remove o conteúdo de [Anexo: ...] antes de anonimizar."""
    if not texto:
        return texto
    return re.sub(r'\[Anexo:[^\]]*\]', '[Anexo: ARQUIVO]', texto)


# ==================== FUNÇÃO PRINCIPAL ====================
def anonimizar_texto(texto, anonimizar_nomes=True):
    """
    Anonimiza dados pessoais, MAS mantém a estrutura semântica.

    Substituições:
      - CPF → 00000000000
      - CNPJ → 00000000000000
      - E-mail → email@exemplo.com
      - Telefone → 0000000000
      - Nomes → M.C.A.S. (iniciais)

    PRESERVADOS:
      - Protocolos (números de 6-10 dígitos)
      - Status
      - Datas
      - Palavras-chave
    """
    if not texto or not isinstance(texto, str):
        return texto

    # 1. Remove nomes de arquivos
    texto = remover_nomes_de_arquivos(texto)

    # 2. ⬇️ ORDEM IMPORTA: substitui ANTES de outros padrões
    # ⚠️ TÍTULO_ELEITOR primeiro (senão é pego por TELEFONE)
    texto = PADROES_DOCUMENTOS['TITULO_ELEITOR'].sub(MASCARAS['TITULO_ELEITOR'], texto)

    # CNPJ antes de CPF (senão é pego por CPF)
    texto = PADROES_DOCUMENTOS['CNPJ'].sub(MASCARAS['CNPJ'], texto)

    # CPF
    texto = PADROES_DOCUMENTOS['CPF'].sub(MASCARAS['CPF'], texto)

    # ⚠️ PIS depois de CPF (senão é pego por CPF)
    texto = PADROES_DOCUMENTOS['PIS'].sub(MASCARAS['PIS'], texto)

    # E-mail
    texto = PADROES_DOCUMENTOS['EMAIL'].sub(MASCARAS['EMAIL'], texto)

    # ⚠️ RG depois de CPF (senão é pego por CPF)
    texto = PADROES_DOCUMENTOS['RG'].sub(MASCARAS['RG'], texto)

    # Telefone (só se tiver formato de telefone)
    texto = PADROES_DOCUMENTOS['TELEFONE'].sub(MASCARAS['TELEFONE'], texto)

    # 3. Anonimiza nomes (mantendo iniciais)
    if anonimizar_nomes:
        texto = anonimizar_nomes_caixa_alta(texto)
        texto = anonimizar_nomes_title_case(texto)

    return texto


# ==================== HELPERS ====================
def contem_dados_pessoais(texto) -> bool:
    """Verifica se um texto contém dados pessoais."""
    if not texto or not isinstance(texto, str):
        return False

    for padrao in PADROES_DOCUMENTOS.values():
        if padrao.search(texto):
            return True

    texto_sem_arquivos = remover_nomes_de_arquivos(texto)
    if PADRAO_NOME_CAIXA_ALTA.search(texto_sem_arquivos):
        return True
    if PADRAO_NOME_TITLE_CASE.search(texto_sem_arquivos):
        return True

    return False


def contar_dados_pessoais(texto) -> dict:
    """Conta quantos dados pessoais de cada tipo existem em um texto."""
    if not texto or not isinstance(texto, str):
        return {}

    resultado = {}
    for tipo, padrao in PADROES_DOCUMENTOS.items():
        matches = padrao.findall(texto)
        if matches:
            resultado[tipo] = len(matches)

    texto_sem_arquivos = remover_nomes_de_arquivos(texto)
    matches_caixa = PADRAO_NOME_CAIXA_ALTA.findall(texto_sem_arquivos)
    if matches_caixa:
        resultado['NOMES_CAIXA_ALTA'] = len(matches_caixa)
    matches_title = PADRAO_NOME_TITLE_CASE.findall(texto_sem_arquivos)
    if matches_title:
        resultado['NOMES_TITLE_CASE'] = len(matches_title)

    return resultado


def anonimizar_dataframe(df, campos: list, anonimizar_nomes: bool = True):
    """Anonimiza campos específicos de um DataFrame."""
    df = df.copy()
    for campo in campos:
        if campo in df.columns:
            df[campo] = df[campo].apply(
                lambda x: anonimizar_texto(x, anonimizar_nomes)
            )
    return df


# ==================== CONFIGURAÇÃO DE MIGRAÇÃO ====================
# Mapeia cada tabela do banco para os campos que devem ser anonimizados.
# Usado por scripts/migrar_sqlite_para_postgres.py
#
# Baseado no schema real do banco (inspecionado em 2026-10-05):
#   tickets (10235), movimentacoes (20212), mensagens (13735), analistas (363)

CAMPOS_POR_TABELA = {
    # ==================== TICKETS ====================
    # Campos que podem conter nomes, CPFs, telefones de terceiros
    'tickets': [
        'titulo',
        'descricao',
        'solicitante',          # nome do solicitante (terceiro)
        'responsavel_atual',    # nome do responsável (analista)
        'responsavel_empresa',  # nome do responsável da empresa
        'solucao',              # texto de solução pode conter dados
        'diagnostico',          # texto de diagnóstico pode conter dados
        'acao_interna',         # anotações internas
        'pendente_usuario',     # texto sobre pendência com usuário
    ],

    # ==================== MOVIMENTACOES ====================
    # Histórico de mudanças de status
    'movimentacoes': [
        'autor',        # nome de quem fez a movimentação
        'comentario',   # comentário pode conter dados pessoais
    ],

    # ==================== MENSAGENS ====================
    # Mensagens trocadas dentro dos tickets
    'mensagens': [
        'autor',             # nome do autor da mensagem
        'analista_destino',  # nome do analista destinatário
        'conteudo',          # conteúdo da mensagem (pode conter CPF, telefone, etc)
    ],

    # ==================== ANALISTAS ====================
    # Dados dos analistas internos
    'analistas': [
        'nome',
        'email',
        'responsavel_area',  # nome do responsável pela área
    ],

    # ==================== AREAS ====================
    # Tabela vazia, mas mantida por segurança
    'areas': [
        'responsavel_area',
    ],

    # ==================== SNAPSHOTS ====================
    # Metadados de execução — não contém dados pessoais, mas mantido
    'snapshots': [
        'observacao',
    ],
}