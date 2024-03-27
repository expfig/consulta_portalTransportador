from sqlalchemy import create_engine, text


class Database:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)

    def transaction(self, sql_query: str, **params) -> bool:
        with self.engine.connect() as connection:
            with connection.begin():
                connection.execute(text(sql_query), params)
        return True

    def selection(self, sql_query: str, **params) -> list:
        with self.engine.connect() as connection:
            result = connection.execute(text(sql_query), params)
            return result.all()
