import pyodbc
import time

server = 'localhost'  
database = 'ConteoChoritos'

connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes'
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

def insertar_conteo(Cantidad1kg, Cantidad500gr, Estancamientos):
    sql_query = """
    INSERT INTO Conteos (Cantidad1kg, Cantidad500gr, Estancamientos)
    VALUES (?, ?, ?)
    """
    cursor.execute(sql_query, (Cantidad1kg, Cantidad500gr, Estancamientos))
    conn.commit()

while True:
    Cantidad1kg = 12  
    Cantidad500gr = 8  
    Estancamientos = 3  

    try:
        insertar_conteo(Cantidad1kg, Cantidad500gr, Estancamientos)
        print("Datos insertados correctamente.")
    except Exception as e:
        print(f"Ocurrió un error al insertar los datos: {e}")

    time.sleep(1800)
    
cursor.close()  
conn.close()
