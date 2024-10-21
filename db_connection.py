from config import DB_CONFIG
import mysql.connector
from mysql.connector import Error
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_connection():
    """Crea una conexión a la base de datos y retorna el objeto de conexión."""
    conn = None
    try:
        conn = mysql.connector.connect(
            host        = DB_CONFIG['host'],
            port        = DB_CONFIG['port'],
            user        = DB_CONFIG['user'],
            password    = DB_CONFIG['password'],
            database    = DB_CONFIG['database']
        )
        
        if conn.is_connected():
            logger.info("Conexión exitosa a la base de datos SQL Server")
    
    except Error as err:
        logger.error(f"Error al conectar a la base de datos: {err}")
    
    return conn

def close_connection(conn):
    """Cierra la conexión a la base de datos."""
    if conn and conn.is_connected():
        conn.close()
        logger.info("Conexión cerrada")

if __name__ == "__main__":
    connection = create_connection()
    close_connection(connection)
