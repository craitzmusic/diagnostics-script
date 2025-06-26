# diagnostics.py

import argparse
import json
import sys
import psycopg2

# FUNÇÃO 1: Conexão Segura
def get_db_connection(db_args):
    """Estabelece uma conexão segura com o banco de dados."""
    try:
        conn = psycopg2.connect(
            dbname=db_args.dbname,
            user=db_args.user,
            password=db_args.password,
            host=db_args.host,
            port=db_args.port
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"ERRO: Falha na conexão com o banco de dados. {e}", file=sys.stderr)
        sys.exit(1)

# FUNÇÃO 2: Execução de Queries
def execute_query(conn, query):
    """
    Executa uma query de forma segura e retorna os resultados como uma lista de dicionários.
    """
    results = []
    try:
        # Usar 'with' garante que o cursor seja fechado automaticamente
        with conn.cursor() as cursor:
            cursor.execute(query)
            
            # Se a query não for do tipo que retorna resultados (ex: DDL), saia
            if cursor.description is None:
                return []

            # Pega o nome das colunas a partir da descrição do cursor
            colnames = [desc[0] for desc in cursor.description]
            
            # Busca todas as linhas e as transforma em uma lista de dicionários
            for row in cursor.fetchall():
                results.append(dict(zip(colnames, row)))
        return results
    except psycopg2.Error as e:
        # Captura erros específicos do banco de dados e os reporta
        print(f"ERRO ao executar query: {query[:100]}... | Erro: {e}", file=sys.stderr)
        # Retorna uma lista vazia em caso de erro para não quebrar o fluxo
        return []

# FUNÇÃO 3: Coleta de Diagnósticos
def collect_diagnostics(conn):
    """Orquestra a coleta de todas as métricas de diagnóstico."""
    diagnostics = {
        "version": None,
        "pg_stat_statements": [],
        # Adicionar mais chaves aqui no futuro
    }

    # Query 1: Obter a versão do PostgreSQL
    diagnostics["version"] = execute_query(conn, "SELECT version();")[0]

    # Nova query aprimorada
    pg_stat_query = """
    SELECT 
        query, 
        calls, 
        total_exec_time, 
        mean_exec_time,
        rows
    FROM 
        pg_stat_statements
    WHERE 
        -- Filtra por queries executadas pelo usuário logado (o nosso user de diagnóstico é excluído implicitamente se for diferente)
        -- E foca nos tipos de query que mais importam para a performance da aplicação
        query NOT ILIKE '%%pg_stat_statements%%' AND
        (query ILIKE 'SELECT%%' OR query ILIKE 'INSERT%%' OR query ILIKE 'UPDATE%%' OR query ILIKE 'DELETE%%')
    ORDER BY 
        total_exec_time DESC
    LIMIT 10;
    """

    diagnostics["pg_stat_statements"] = execute_query(conn, pg_stat_query)

    return diagnostics

# FUNÇÃO PRINCIPAL: Orquestração e I/O
def main():
    """Ponto de entrada do script que analisa os argumentos e orquestra o diagnóstico."""
    parser = argparse.ArgumentParser(
        description="QueryMetrix Diagnostics Script - Coleta dados de performance de um banco de dados PostgreSQL.",
        epilog="Exemplo: python diagnostics.py --host localhost --user myuser --dbname mydb"
    )
    
    # Definição de cada argumento esperado
    parser.add_argument('--host', required=True, help='Endereço do servidor do banco de dados.')
    parser.add_argument('--port', type=int, default=5432, help='Porta do servidor do banco de dados (padrão: 5432).')
    parser.add_argument('--user', required=True, help='Nome do usuário para a conexão.')
    parser.add_argument('--password', required=True, help='Senha para o usuário do banco de dados.')
    parser.add_argument('--dbname', required=True, help='Nome do banco de dados para conectar.')

    # Analisa os argumentos fornecidos na linha de comando
    args = parser.parse_args()

    # O restante da lógica permanece o mesmo
    conn = get_db_connection(args)
    
    try:
        diagnostic_data = collect_diagnostics(conn)
        print(json.dumps(diagnostic_data, indent=4, default=str))
    finally:
        conn.close()

if __name__ == "__main__":
    main()