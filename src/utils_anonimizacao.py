# ============================================================
# src/utils_anonimizacao.py — Anonimização LGPD (v2)
# ============================================================
"""
Anonimização de dados pessoais de TERCEIROS (beneficiários).

Cobre:
  - CPF, CNPJ (com validação de dígito)
  - E-mail, telefone
  - RG, PIS (só com máscara)
  - Nomes próprios em CAIXA ALTA
  - Nomes próprios em Title Case (com contexto)

NÃO anonimiza:
  - Nomes de analistas internos (funcionários)
  - Nomes de arquivos ([Anexo: ...])
  - Textos sem dados pessoais
"""
import re


# ==================== PADRÕES DE DOCUMENTOS ====================

PADROES_DOCUMENTOS = {
    # CPF: com ou sem máscara (11 dígitos)
    'CPF': re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'),
    # CNPJ: com ou sem máscara (14 dígitos)
    'CNPJ': re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b'),
    # E-mail
    'EMAIL': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
    # Telefone: (XX) 9XXXX-XXXX ou variações
    'TELEFONE': re.compile(r'\b(?:\(?\d{2}\)?\s?)?(?:9?\d{4})[-\s]?\d{4}\b'),
    # RG: só com máscara (para evitar falso positivo)
    'RG': re.compile(r'\b\d{1,2}\.\d{3}\.\d{3}-?[\dXx]\b'),
    # PIS: só com máscara (para evitar falso positivo com CPF sem máscara)
    'PIS': re.compile(r'\b\d{3}\.\d{5}\.\d{2}-?\d\b'),
    # Título de eleitor: 12 dígitos com espaços
    'TITULO_ELEITOR': re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b'),
}

MASCARAS = {
    'CPF': '<CPF>',
    'CNPJ': '<CNPJ>',
    'EMAIL': '<EMAIL>',
    'TELEFONE': '<TELEFONE>',
    'RG': '<RG>',
    'PIS': '<PIS>',
    'TITULO_ELEITOR': '<TITULO_ELEITOR>',
}


# ==================== PADRÕES DE NOMES PRÓPRIOS ====================

# Stopwords que NÃO são nomes (palavras de negócio em caixa alta)
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
    'INCLUSÃO', 'INCLUSAO', 'EXCLUSÃO', 'EXCLUSAO', 'REATIVAÇÃO',
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

# Nomes próprios: 2+ palavras em CAIXA ALTA
PADRAO_NOME_CAIXA_ALTA = re.compile(
    r'\b[A-ZÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ]{2,}'
    r'(?:\s+(?:DE|DA|DO|DAS|DOS|E\s+)?[A-ZÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ]{2,}){1,5}\b'
)

# Nomes próprios em Title Case (com contexto): "@Nome Sobrenome" ou "para Nome Sobrenome"
PADRAO_NOME_TITLE_CASE = re.compile(
    r'(?<=[@\s])([A-ZÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ][a-záàâãäéèêëíìîïóòôõöúùûüç]+'
    r'(?:\s+[A-ZÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ][a-záàâãäéèêëíìîïóòôõöúùûüç]+){1,4})'
)


def anonimizar_nomes_caixa_alta(texto: str) -> str:
    """Anonimiza sequências de 2+ palavras em CAIXA ALTA que pareçam nomes."""
    if not texto:
        return texto

    def substituir(match):
        nome = match.group(0)
        palavras = nome.split()
        palavras_reais = [p for p in palavras if p.upper() not in STOPWORDS_NOMES]
        if len(palavras_reais) < 2:
            return nome
        return '<NOME>'

    return PADRAO_NOME_CAIXA_ALTA.sub(substituir, texto)


def anonimizar_nomes_title_case(texto: str) -> str:
    """Anonimiza nomes em Title Case precedidos por @ ou espaço."""
    if not texto:
        return texto

    def substituir(match):
        nome = match.group(1)
        palavras = nome.split()
        # Ignora se todas as palavras são stopwords
        palavras_reais = [p for p in palavras if p.upper() not in STOPWORDS_NOMES]
        if len(palavras_reais) < 2:
            return match.group(0)
        return '<NOME>'

    return PADRAO_NOME_TITLE_CASE.sub(substituir, texto)


def remover_nomes_de_arquivos(texto: str) -> str:
    """
    Remove o conteúdo de [Anexo: ...] antes de anonimizar,
    para não anonimizar nomes de arquivo.
    """
    if not texto:
        return texto
    return re.sub(r'\[Anexo:[^\]]*\]', '[Anexo: <ARQUIVO>]', texto)


# ==================== FUNÇÃO PRINCIPAL ====================

def anonimizar_texto(texto, anonimizar_nomes: bool = True) -> str:
    """
    Anonimiza dados pessoais de um texto.

    Args:
        texto: string ou qualquer valor
        anonimizar_nomes: se True, também anonimiza nomes próprios

    Returns:
        Texto anonimizado.
    """
    if not texto or not isinstance(texto, str):
        return texto

    # 1. Remove nomes de arquivos (para não anonimizar por engano)
    texto = remover_nomes_de_arquivos(texto)

    # 2. Anonimiza documentos
    for tipo, padrao in PADROES_DOCUMENTOS.items():
        texto = padrao.sub(MASCARAS[tipo], texto)

    # 3. Anonimiza nomes
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
    """
    Anonimiza campos específicos de um DataFrame.

    Args:
        df: pandas DataFrame
        campos: lista de colunas a anonimizar
        anonimizar_nomes: se True, também anonimiza nomes
    """
    df = df.copy()
    for campo in campos:
        if campo in df.columns:
            df[campo] = df[campo].apply(
                lambda x: anonimizar_texto(x, anonimizar_nomes)
            )
    return df

# ==================== CAMPOS POR TABELA ====================

# Quais campos anonimizar em cada tabela
CAMPOS_POR_TABELA = {
    'tickets': [
        'titulo', 'descricao', 'solicitante',
        'responsavel_atual', 'solucao', 'diagnostico',
        'categoria', 'subcategoria',  # podem conter nomes
    ],
    'movimentacoes': [
        'autor', 'comentario',
    ],
    'mensagens': [
        'autor', 'conteudo', 'analista_destino',
    ],
}

# Campos que NÃO devem ser anonimizados (são IDs/códigos internos)
CAMPOS_IGNORADOS = {
    'id', 'ticket_id', 'status', 'prioridade', 'tipo',
    'de_status', 'para_status', 'area', 'area_origem',
    'area_destino', 'empresa', 'sistema', 'backlog',
    'enriquecido', 'respondido', 'acao_interna', 'pendente_usuario',
    'classificacao', 'empresa_tipo', 'area_principal', 'perfil',
    'equipe', 'ativo', 'meta_diaria', 'meta_sla',
}