import pymysql.cursors, os

# Connect to the database
def create_connection():
  connection = pymysql.connect(
    host = os.environ.get('MYSQL_HOST', None),
    db = os.environ.get('MYSQL_DB', None),
    user = os.environ.get('MYSQL_USER', None),
    password = os.environ.get('MYSQL_PASSWORD', None),
    port= os.environ.get('MYSQL_PORT', None),
    charset = 'utf8mb4', 
    cursorclass = pymysql.cursors.DictCursor
  )
  return connection

class Database(object): 

    @classmethod
    def clean_table(cls, table_name):
      connection = create_connection()
      with connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE {}".format(table_name))
        connection.commit()
      connection.close()

    @classmethod
    def insert(cls, table_name, data):
      connection = create_connection()
      with connection.cursor() as cursor:
        keys = data.keys()
        values = tuple([data[k] for k in keys])

        insert_keys = ', '.join(["`{}`".format(k) for k in keys])
        insert_values = ', '.join(["%s" for k in keys])

        sql = "INSERT INTO `{}` ({}) VALUES ({})".format(table_name, insert_keys, insert_values)
        cursor.execute(sql, values)

        result = cursor.fetchone()
        connection.commit()
      connection.close()

    @classmethod
    def find_one(cls, table_name, query, return_filter = ['*']):
      result = None
      connection = create_connection()
      with connection.cursor() as cursor:
        keys = query.keys()
        values = tuple([query[k] for k in keys])

        return_filter_values = ', '.join(["`{}`".format(k) for k in return_filter])
        
        wheres = " AND ".join((["`{}`=%s".format(k) for k in keys]))

        sql = "SELECT {} FROM `{}` WHERE {}".format(return_filter_values, table_name, wheres)
        cursor.execute(sql, values)

        result = cursor.fetchone()
      connection.close()
      return result

    @classmethod
    def find(cls, table_name, query, return_filter = ['*']):
      result = None
      connection = create_connection()
      with connection.cursor() as cursor:
        keys = query.keys()
        values = tuple([query[k] for k in keys])

        return_filter_values = ', '.join(["`{}`".format(k) for k in return_filter])
        
        wheres = " AND ".join((["`{}`=%s".format(k) for k in keys]))

        sql = "SELECT {} FROM `{}` WHERE {}".format(return_filter_values, table_name, wheres)
        cursor.execute(sql, values)

        result = cursor.fetchall()
      connection.close()
      return result

    @classmethod
    def update(cls, table_name, query, data):
      connection = create_connection()
      with connection.cursor() as cursor:
        query_keys = query.keys()
        query_values = tuple([query[k] for k in query_keys])
        wheres = " AND ".join((["`{}`=%s".format(k) for k in query_keys]))

        data_keys = data.keys()
        data_values = tuple([data[k] for k in data_keys])

        setter = ', '.join(["{}=%s".format(k) for k in data_keys])

        sql = "UPDATE `{}` SET {} WHERE {}".format(table_name, setter, wheres)

        cursor.execute(sql, data_values + query_values)
        connection.commit()
      connection.close()
