import psycopg2

try:
    conn = psycopg2.connect(
        host="iriguchi.proxy.rlwy.net",
        port=12044,
        database="railway",
        user="postgres",
        password="GthcruwJeZwovJWmEoUhOwsGxgfFZYZS",
        sslmode="require"
    )
    print("OK conectado")
    conn.close()
except Exception as e:
    print(f"ERRO: {e}")