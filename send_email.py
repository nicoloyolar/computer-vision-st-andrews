import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json

# Cargar la configuración desde config.json
with open('config.json', 'r') as f:
    config = json.load(f)

# Configuración del servidor SMTP
smtp_server = config['smtp_server']
smtp_port = config['smtp_port']
smtp_username = config['smtp_username']
smtp_password = config['smtp_password']

# Crear el mensaje
msg = MIMEMultipart()
msg['From'] = smtp_username
msg['To'] = ', '.join(config['destinatarios'])
msg['Cc'] = ', '.join(config['cc'])
msg['Subject'] = 'Prueba de envío de correo'

# Cuerpo del correo
body = 'Este es un correo de prueba enviado desde Python.'
msg.attach(MIMEText(body, 'plain'))

# Combina destinatarios y CC
all_recipients = config['destinatarios'] + config['cc']

try:
    # Conectar y enviar el correo
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # Iniciar TLS
        server.login(smtp_username, smtp_password)  # Iniciar sesión
        server.send_message(msg, from_addr=smtp_username, to_addrs=all_recipients)
    print("Correo enviado exitosamente.")
except Exception as e:
    print(f"Error al enviar el correo: {e}")
