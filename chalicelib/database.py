import pymysql.cursors, os

debug = True

table_names = [
  "User","Token","Security",
  "SecurityTimestamp","TokenBalance","TokenHoldings",
  "TokenHolding","Trade","TradeBroker","`Order`",
  "OrderHolding","OrderTrade"
]

# Connect to the database
def create_connection():
  port = os.environ.get('MYSQL_PORT', None)
  if port: port = int(port)
  connection = pymysql.connect(
    host = os.environ.get('MYSQL_HOST', None),
    db = os.environ.get('MYSQL_DB', None),
    user = os.environ.get('MYSQL_USER', None),
    password = os.environ.get('MYSQL_PASSWORD', None),
    port = port,
    charset = 'utf8mb4',
    cursorclass = pymysql.cursors.DictCursor
  )
  return connection

class Database(object):

  @classmethod
  def query_to_data(cls, query):
    data = {}
    for line in query[0]: data[line[0]] = line[2]
    return data

  @classmethod
  def data_to_query(cls, data):
    query = []
    for key in data.keys():
      operator = '='
      if type(data[key]) == tuple:
        operator = data[key][0]
        data[key] = data[key][1]
      query.append((key,operator,data[key]))
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
  def clean_tables(cls):
    for table_name in table_names:
      cls.clean_table(table_name)

  @classmethod
  def insert(cls, table_name, data, return_inserted = True):
    if(type(data) == tuple): data = [data]
    if(type(data) == list): data = data_to_query(data)
    connection = create_connection()
    with connection.cursor() as cursor:
      keys = data.keys()
      values = tuple([data[k] for k in keys])
      insert_keys = ', '.join(["`{}`".format(k) for k in keys])
      insert_values = ', '.join(["%s" for k in keys])
      sql = "INSERT INTO `{}` ({}) VALUES ({})".format(table_name, insert_keys, insert_values)
      if debug: print(sql)
      cursor.execute(sql, values)
      connection.commit()
    connection.close()
    if return_inserted: return cls.find_one(table_name, data)

  @classmethod
  def find_one(cls, table_name, query=[], return_filter = ['*'], insert = False, order_by=None):
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
      if order_by: sql += " ORDER BY {}".format(order_by)
      cursor.execute(sql, values)
      if debug: print(sql)
      result = cursor.fetchone()
    connection.close()
    if result == None and insert: result = cls.insert(table_name, cls.query_to_data(query))
    return result

  @classmethod
  def find(cls, table_name, query=[], return_filter = ['*'], page=0, page_count=None):
    if(page): page = int(page)
    if(page_count): page_count = int(page_count)
    if(type(query) == dict): query = cls.data_to_query(query)
    if(type(query) == tuple): query = [query]
    if(len(query) and type(query[0]) == tuple): query = [query]
    result = None
    total = None
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
        sql += " LIMIT {} OFFSET {}".format(page_count,page_count*page)

        count_sql = "SELECT COUNT(*) FROM `{}`".format(table_name)
        if wheres: count_sql += " WHERE {}".format(wheres)
        cursor.execute(count_sql, values)
        total = cursor.fetchone()['COUNT(*)']

      if debug: print(sql)
      cursor.execute(sql, values)
      result = cursor.fetchall()
    connection.close()
    if page_count: return {"data": result, "total": total}
    return result

  @classmethod
  def update(cls, table_name, query, data, return_updated = False):
    connection = create_connection()
    if(type(query) == dict): query = cls.data_to_query(query)
    if(type(query) == tuple): query = [query]
    if(len(query) and type(query[0]) == tuple): query = [query]
    result = None
    with connection.cursor() as cursor:
      # query_keys = query.keys()
      # query_values = tuple([query[k] for k in query_keys])
      # wheres = " AND ".join((["`{}`=%s".format(k) for k in query_keys]))

      wheres = []
      query_values = []
      for q in query:
        w = "(" + " AND ".join((["`{}`{}%s".format(s[0],s[1]) for s in q])) + ")"
        v = [s[2] for s in q]
        wheres.append(w)
        query_values += v
      wheres = " OR ".join(wheres)
      query_values = tuple(query_values)


      data_keys = data.keys()
      data_values = tuple([data[k] for k in data_keys])
      setter = ', '.join(["{}=%s".format(k) for k in data_keys])
      sql = "UPDATE `{}` SET {}".format(table_name, setter)

      if wheres: sql += " WHERE {}".format(wheres)

      if debug: print(sql)
      cursor.execute(sql, data_values + query_values)
      connection.commit()
    connection.close()
    if result == None and return_updated: result = cls.find(table_name, query)
    return result

  @classmethod
  def remove(cls, table_name, query):
    connection = create_connection()
    with connection.cursor() as cursor:
      keys = query.keys()
      values = tuple([query[k] for k in keys])
      wheres = " AND ".join((["`{}`=%s".format(k) for k in keys]))
      sql = "DELETE FROM `{}`".format(table_name)
      if wheres: sql += " WHERE {}".format(wheres)
      if debug: print(sql)
      cursor.execute(sql, values)
      connection.commit()
    connection.close()
