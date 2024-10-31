import smtplib
from video_stream import VideoStream
from yolo_detection import YOLODetector
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sort import Sort
from datetime import datetime
import cv2
import numpy as np
import time
import threading
import pyodbc
import json
import whatsapp_messaging  
import twilio
import sys
import os
from twilio.rest import Client

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

VIDEO_PATH = "C:\\Users\\Developer\\Downloads\\actual.mp4"
MODEL_PATH = "C:\\computer-vision\\proyecto_contador\\modelo\\model_retrained_with_3_classes.pt"

SCALE_FACTOR = 0.2
COUNTER_LINE_Y = 900  
MARGIN = 10 
ALERTA_INTERVALO_SEGUNDOS = 600

p_c_1kg = 0
p_c_500grs = 0
estancamiento = 0
total_1kg = 0
total_500grs = 0
total_stagnations = 0
last_hour = datetime.now().hour

sort_tracker = Sort(max_age=90, min_hits=4, iou_threshold=0.25)
counted_ids = set()
object_classes = {}
object_scores = {}
last_summary = ""
history = []
last_update_time = time.time()

# Base de datos SQL Server
server = '192.168.31.168,1433'
database = 'db_conteo_entero'
username = 'capturador'
password = 'J7mo6uv97Y0x'

connection = None
try:
    connection = pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    )
    print("Conexión exitosa a la base de datos.")
except Exception as e:
    print("Error al conectar a la base de datos:", e)

def en_horario_turno():
    now = datetime.now()
    dia, hora = now.weekday(), now.hour
    if dia < 5:
        return 8 <= hora < 24
    elif dia in [5, 6]:
        return 8 <= hora < 20
    return False

def enviar_mensaje_whatsapp_async(mensaje_body):
    threading.Thread(target=enviar_mensaje_whatsapp, args=(mensaje_body,)).start()

def enviar_mensaje_whatsapp(mensaje_body):
    try:
        with open("C:\\Users\\56975\\OneDrive\\Escritorio\\proyecto_contador\\config.json", 'r') as f:
            config = json.load(f)
        account_sid = config.get('account_sid')
        auth_token = config.get('auth_token')
        to_whatsapp_list = config.get('to_whatsapp')
        from_whatsapp = "whatsapp:+14155238886"
        
        client = Client(account_sid, auth_token)
        for to_whatsapp in to_whatsapp_list:
            client.messages.create(body=mensaje_body, from_=from_whatsapp, to=to_whatsapp)
    except Exception as e:
        print("Error al enviar el mensaje de WhatsApp:", e)

def enviar_correo_async(p_c_1kg, p_c_500grs, estancamiento):
    threading.Thread(target=enviar_correo, args=(p_c_1kg, p_c_500grs, estancamiento)).start()

def enviar_correo(p_c_1kg, p_c_500grs, estancamiento):
    with open('C:\\computer-vision\\proyecto_contador\\config.json', 'r') as f:
        config = json.load(f)
    smtp_server = config['smtp_server']
    smtp_port = config['smtp_port']
    smtp_username = config['smtp_username']
    smtp_password = config['smtp_password']

    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = ', '.join(config['destinatarios'])
    msg['Cc'] = ', '.join(config['cc'])
    msg['Subject'] = 'Resumen conteo de productos'
    
    body = (f"Este es el resumen del conteo de productos:\n\n"
            f"Paquetes de 1kg: {p_c_1kg}\n"
            f"Paquetes de 500grs: {p_c_500grs}\n"
            f"Estancamientos: {estancamiento}\n\n"
            f"Resumen generado a las {datetime.now().strftime('%H:%M:%S')}.")
    
    msg.attach(MIMEText(body, 'plain'))
    all_recipients = config['destinatarios'] + config['cc']
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg, from_addr=smtp_username, to_addrs=all_recipients)
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
    
    enviar_mensaje_whatsapp_async(body)

def insertar_conteo_async(etiqueta):
    def insertar_conteo():
        sql_query = """
        INSERT INTO ConteoProductos (Etiqueta)
        VALUES (?)
        """
        try:
            cursor = connection.cursor()
            cursor.execute(sql_query, (etiqueta,))
            connection.commit()
            print(f"Datos insertados: {etiqueta}")
        except Exception as e:
            print(f"Error al insertar datos en la base de datos: {e}")
        finally:
            cursor.close()
    threading.Thread(target=insertar_conteo).start()

def update_summary():
    global last_summary, history, total_1kg, total_500grs, total_stagnations, last_update_time

    current_time = datetime.now().strftime('%H:%M:%S')
    last_summary = f'1kg: {p_c_1kg}, 500grs: {p_c_500grs}, Estancamientos: {estancamiento}'
    total_summary = f'Total 1kg: {total_1kg}, Total 500grs: {total_500grs}, Total Estancamientos: {total_stagnations}'
    summary = f"{current_time} - {last_summary} | {total_summary}"
    history.append(summary)
    
    enviar_correo_async(p_c_1kg, p_c_500grs, estancamiento)
    reset_counts()
    last_update_time = time.time()

def reset_counts():
    global p_c_1kg, p_c_500grs, estancamiento, counted_ids
    p_c_1kg, p_c_500grs, estancamiento = 0, 0, 0
    counted_ids.clear()

def draw_label(frame, text, x, y, color=(0, 255, 255), bg_color=(0, 0, 0, 0.5)):
    font_scale, font_thickness = 1.2, 3
    (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)
    overlay = frame.copy()
    box_coords = ((x, y), (x + text_width + 10, y - text_height - 10))
    cv2.rectangle(overlay, box_coords[0], box_coords[1], bg_color[:3], -1)
    cv2.addWeighted(overlay, bg_color[3], frame, 1 - bg_color[3], 0, frame)
    cv2.putText(frame, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, font_thickness)

def draw_transparent_line(frame):
    overlay = frame.copy()
    alpha = 0.3
    cv2.line(overlay, (0, COUNTER_LINE_Y), (frame.shape[1], COUNTER_LINE_Y), (0, 0, 255), 2)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

def draw_counter_info(frame, last_summary):
    font_scale, font_thickness = 1.5, 4
    margin, line_spacing = 10, 40
    general_lines = [f'Paquetes de 1kg: {p_c_1kg}', f'Paquetes de 500grs: {p_c_500grs}', f'Estancamientos: {estancamiento}']
    text_lines = general_lines + [f"Último resumen: {last_summary}" if last_summary else "Esperando próximo resumen..."]
    max_text_width = max([cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)[0][0] for line in text_lines])
    box_width, box_height = max_text_width + 2 * margin, len(text_lines) * line_spacing + margin
    overlay = frame.copy()
    cv2.rectangle(overlay, (margin, margin), (margin + box_width, margin + box_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    for i, line in enumerate(text_lines):
        color = (0, 255, 0) if '500grs' in line else (0, 255, 255) if '1kg' in line else (0, 0, 255)
        y = margin + (i + 1) * line_spacing
        cv2.putText(frame, line, (margin + 10, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, font_thickness, cv2.LINE_AA)

def main():
    global p_c_1kg, p_c_500grs, estancamiento, last_summary, last_update_time, last_hour

    stream = VideoStream(VIDEO_PATH)
    if not stream.cap.isOpened():
        return

    detector = YOLODetector(MODEL_PATH)

    while stream.cap.isOpened():
        ret, frame = stream.read_frame()
        if not ret: break

        current_time = time.time()
        if current_time - last_update_time >= ALERTA_INTERVALO_SEGUNDOS and en_horario_turno():  
            update_summary()
            reset_counts()
            last_update_time = current_time  

        results = detector.detect_objects(frame)
        detections = [[*map(int, detection.xyxy[0]), float(detection.conf)] for detection in results[0].boxes]

        for detection in detections:
            x1, y1, x2, y2, score = detection
            label = detector.model.names[int(results[0].boxes[0].cls)]
            display_text = f'{label} ({score * 100:.1f}%)'

            if label == '500grs' and score >= 0.5:
                draw_label(frame, display_text, x1, y1, color=(0, 255, 0), bg_color=(0, 0, 0, 0.5))
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            elif label == '1kg' and score >= 0.5:
                draw_label(frame, display_text, x1, y1, color=(0, 255, 255), bg_color=(0, 0, 0, 0.5))
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

        detections = np.array(detections) if detections else np.empty((0, 5))
        tracked_objects = sort_tracker.update(detections)

        for obj in tracked_objects:
            x1, y1, x2, y2, track_id = map(int, obj)
            if track_id not in object_classes:
                object_classes[track_id], object_scores[track_id] = label, score
            fixed_label, fixed_score = object_classes[track_id], object_scores[track_id]

            object_bottom_y = y2  

            if object_bottom_y > (COUNTER_LINE_Y + MARGIN) and track_id not in counted_ids:
                counted_ids.add(track_id)
                insertar_conteo_async(fixed_label)

                if fixed_label == '1kg' and fixed_score >= 0.6:
                    p_c_1kg += 1
                elif fixed_label == '500grs' and fixed_score >= 0.6:
                    p_c_500grs += 1

        draw_transparent_line(frame)
        draw_counter_info(frame, last_summary)
        cv2.imshow('Sistema de vision automatica_Chiloe', cv2.resize(frame, None, fx=SCALE_FACTOR, fy=SCALE_FACTOR))
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    stream.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
