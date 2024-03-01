import psycopg2


class db_logs:
    def __init__(self, user, password):

        self.conn = psycopg2.connect(
            dbname="automacao_logs",
            user=user,
            password=password,
            host="10.0.0.72",
            port="5432",
        )

    def get_alerts(self):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT num_cte, mensagem FROM public.alertas_portal_transportador where mensagem <> 'Não encontrado na base Vega' and data > now() - interval '1 day'"
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def insert_logs(self, num_cte, msg):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO public.alertas_portal_transportador (num_cte, mensagem, data) VALUES (%s, %s, now())",
            (num_cte, msg),
        )
        self.conn.commit()
        cursor.close()
