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
  def query_to_data(cls, query):
    data = {}
    for line in query:
      data[line[0]] = line[2]
    return data

  @classmethod
  def data_to_query(cls, data):
    query = []
    for key in data.keys():
      query.append((key,'=',data[key]))
    return query

  @classmethod
  def clean_table(cls, table_name):
    connection = create_connection()
    with connection.cursor() as cursor:
      cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
      cursor.execute("TRUNCATE TABLE {}".format(table_name))
      cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
      connection.commit()
    connection.close()

  @classmethod
  def insert(cls, table_name, data, return_inserted = True):
    connection = create_connection()
    with connection.cursor() as cursor:
      keys = data.keys()
      values = tuple([data[k] for k in keys])
      insert_keys = ', '.join(["`{}`".format(k) for k in keys])
      insert_values = ', '.join(["%s" for k in keys])
      sql = "INSERT INTO `{}` ({}) VALUES ({})".format(table_name, insert_keys, insert_values)
      cursor.execute(sql, values)
      connection.commit()
    connection.close()
    if return_inserted: return cls.find_one(table_name, data)

  @classmethod
  def find_one(cls, table_name, query=[], return_filter = ['*'], insert = False):
    if(type(query) == dict): query = cls.data_to_query(query)
    if(type(query) == tuple): query = [query]
    if(len(query) and type(query[0]) == tuple): query = [query]
    result = None
    connection = create_connection()
    with connection.cursor() as cursor:
      return_filter_values = ', '.join(["`{}`".format(k) for k in return_filter])
      wheres = []
      values = []
      for q in query:
        w = "(" + " AND ".join((["`{}`{}%s".format(s[0],s[1]) for s in q])) + ")"
        v = [s[2] for s in q]
        wheres.append(w)
        values += v
      wheres = " OR ".join(wheres)
      values = tuple(values)
      sql = "SELECT {} FROM `{}` WHERE {}".format(return_filter_values, table_name, wheres)
      cursor.execute(sql, values)
      result = cursor.fetchone()
      if result == None and insert: result = cls.insert(table_name, cls.query_to_data(query))
    connection.close()
    return result

  @classmethod
  def find(cls, table_name, query=[], return_filter = ['*'], page=0, page_count=None):
    if(type(query) == dict): query = cls.data_to_query(query)
    if(type(query) == tuple): query = [query]
    if(len(query) and type(query[0]) == tuple): query = [query]
    result = None
    connection = create_connection()
    with connection.cursor() as cursor:
      return_filter_values = ', '.join(["`{}`".format(k) for k in return_filter])
      wheres = []
      values = []
      for q in query:
        w = "(" + " AND ".join((["`{}`{}%s".format(s[0],s[1]) for s in q])) + ")"
        v = [s[2] for s in q]
        wheres.append(w)
        values += v
      wheres = " OR ".join(wheres)
      values = tuple(values)
      sql = "SELECT {} FROM `{}`".format(return_filter_values, table_name)
      if wheres: sql += " WHERE {}".format(wheres)
      if page_count:
        sql += " LIMIT {},{}".format(page_count*page,page_count*(page+1))
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
      sql = "UPDATE `{}` SET {}".format(table_name, setter)
      if wheres: sql += " WHERE {}".format(wheres)
      cursor.execute(sql, data_values + query_values)
      connection.commit()
    connection.close()

  @classmethod
  def remove(cls, table_name, query):
    connection = create_connection()
    with connection.cursor() as cursor:
      keys = query.keys()
      values = tuple([query[k] for k in keys])
      wheres = " AND ".join((["`{}`=%s".format(k) for k in keys]))
      sql = "DELETE FROM `{}`".format(table_name)
      if wheres: sql += " WHERE {}".format(wheres)
      cursor.execute(sql, values)
      connection.commit()
    connection.close()
