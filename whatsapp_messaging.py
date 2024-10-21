from twilio.rest import Client

# Función para enviar mensajes de WhatsApp
def enviar_mensaje_whatsapp(account_sid, auth_token, to_number, message_body):
    # Crear cliente de Twilio
    client = Client(account_sid, auth_token)
    
    # Número de WhatsApp del sandbox de Twilio
    twilio_whatsapp_number = 'whatsapp:+14155238886'  # El número del sandbox de Twilio

    # Enviar mensaje de WhatsApp
    message = client.messages.create(
        body=message_body,
        from_=twilio_whatsapp_number,
        to=to_number
    )
    
    # Devuelve el SID del mensaje como confirmación
    return message.sid
