import psycopg2
class PostgresDatabase:
    def __init__(self):
        self.host = 
        self.port = 
        self.dbname = 
        self.user = 
        self.password = 
        self.connection = None
        self.cursor = None
    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password
            )
            self.cursor = self.connection.cursor()
        except Exception as e:
            print("Error connecting to PostgreSQL:", e)
    def execute_query(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            self.column_names = [desc[0] for desc in self.cursor.description]
            return self.cursor.fetchall() , self.column_names
        except Exception as e:
            print("Error executing query:", e)
            return None
    def execute_non_query(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
        except Exception as e:
            if str(type(e)) == "<class 'psycopg2.errors.UniqueViolation'>":
                self.connection.rollback()
                return 'Username Exists'
    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
