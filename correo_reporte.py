import os
import time
import random
import cv2
import numpy as np
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from video_stream import VideoStream
from yolo_detection import YOLODetector
from sort import Sort
from path import MODEL_PATH, VIDEO_PATH

class correoReporte:
    """Esta clase permite el envío de mensajería mediante correo electrónico"""
    def __init__(self, config_path='config.json'):
        self.config_path    = config_path
        self.creds          = self.load_credentials()
        self.destinatarios  = self.creds.get('destinatarios', [])
        self.cc             = self.creds.get('cc', [])
        self.conteo_total   = 0

    def load_credentials(self):
        """Este método carga las credenciales desde el archivo de configuración para enviar mensajería por correo"""
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: El archivo de configuración '{self.config_path}' no se encontró.")
            raise
        except json.JSONDecodeError:
            print(f"Error: El archivo de configuración '{self.config_path}' no se puede parsear.")
            raise

    def send_email(self, subject, body):
        """Esta función permite enviar correos mediante un servidor y configuración smtp previamente establecida"""
        smtp_server     = self.creds['smtp_server']
        smtp_port       = self.creds['smtp_port']
        smtp_username   = self.creds['smtp_username']
        smtp_password   = self.creds['smtp_password']

        msg = MIMEMultipart()
        msg['From']     = smtp_username
        msg['To']       = ', '.join(self.destinatarios)
        msg['Cc']       = ', '.join(self.cc)
        msg['Subject']  = subject

        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            print(f"Correo enviado: {subject} a {msg['To']} con CC a {msg['Cc']}")
        
        except smtplib.SMTPAuthenticationError:
            print(f"Error: Fallo en la autenticación con el servidor SMTP. Verifica el usuario y la contraseña.")
        
        except smtplib.SMTPConnectError:
            print(f"Error: No se pudo conectar al servidor SMTP. Verifica la configuración del servidor.")
        
        except smtplib.SMTPException as e:
            print(f"Error general al enviar el correo: {e}")
        
        except Exception as e:
            print(f"Error inesperado: {e}")

    def reportes(self, hora, conteo):
        """Genera un reporte mediante correo electrónico para notificar cuántos paquetes han sido contabilizados en cierto horario"""
        subject = f"Reporte conteo {hora} AM" if hora < 12 else f"Reporte conteo {hora % 12} PM"
        body = f"Cantidad de paquetes contabilizados horario {hora} AM: {conteo}" if hora < 12 else f"Cantidad de paquetes contabilizados horario {hora % 12} PM: {conteo}"
        return subject, body

    def enviar_reporte_diario(self, conteo_total):
        """Envía el reporte final al terminar el turno"""
        final_subject = "Reporte final turno diurno 8 AM-18 PM"
        final_body = f"Cantidad total de paquetes contabilizados en el turno diurno: {conteo_total}"
        self.send_email(final_subject, final_body)

class ObjectCounter:
    """Esta clase permite detectar, identificar, clasificar y contar distintos tipos de productos en una línea de producción mediante un sistema de visión artificial"""
    def __init__(self, model_path, video_path):
        self.model_path             = model_path
        self.video_path             = video_path
        self.scale_factor           = 0.6
        self.counter_line_y         = 1000
        self.product_count_1kg      = 0
        self.product_count_500grs   = 0
        self.stagnation_count       = 0
        self.sort_tracker           = Sort(max_age=3, min_hits=2, iou_threshold=0.3)
        self.counted_ids            = set()
        self.object_classes         = {}
        self.object_scores          = {}
        self.reporte                = correoReporte()  # Integración del sistema de correo
        self.time_interval           = 60  # Intervalo de tiempo para el envío de correos (60 segundos)

        self.check_files()

    def check_files(self):
        """Este método comprueba la existencia de los archivos especificados y lanza una excepción si alguno falla"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"El modelo no se encuentra en {self.model_path}")
        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"El video no se encuentra en {self.video_path}")

    def draw_label(self, frame, text, x, y, color=(0, 255, 255), bg_color=(0, 0, 0, 0.5)):
        """Este método dibuja un cuadro de texto en el marco"""
        font_scale, font_thickness = 1.2, 3
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)[0]
        box_coords = ((x, y), (x + text_size[0] + 10, y - text_size[1] - 10))
        cv2.rectangle(frame, box_coords[0], box_coords[1], bg_color[:3], -1)
        cv2.putText(frame, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, font_thickness)

    def highlight_critical(self, frame, text, x, y):
        """Este método destaca mensajes críticos en rojo"""
        self.draw_label(frame, text, x, y, color=(0, 0, 255), bg_color=(0, 0, 0, 0.7))

    def count_products(self, track_id, label):
        """Este método cuenta la cantidad de productos detectados"""
        if track_id not in self.counted_ids:
            self.counted_ids.add(track_id)
            if label == '1kg':
                self.product_count_1kg += 1
            elif label == '500grs':
                self.product_count_500grs += 1

    def process_frame(self, frame, detector):
        """Este método maneja la detección de objetos, actualiza el seguimiento y llama al método de conteo de productos"""
        results = detector.detect_objects(frame)
        detections = [[*map(int, detection.xyxy[0]), float(detection.conf)] for detection in results[0].boxes if detection.conf >= detector.confidence_threshold]

        for detection in detections:
            x1, y1, x2, y2, score = detection
            label = detector.model.names[int(results[0].boxes[0].cls)]
            display_text = f'{label} ({score * 100:.1f}%)'

            if label == 'estancamiento':
                self.highlight_critical(frame, display_text, x1, y1)
                if label not in self.counted_ids:
                    self.stagnation_count += 1
                    self.counted_ids.add(label)
            else:
                self.draw_label(frame, display_text, x1, y1)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        detections = np.array(detections) if detections else np.empty((0, 5))
        tracked_objects = self.sort_tracker.update(detections)

        for obj in tracked_objects:
            x1, y1, x2, y2, track_id = map(int, obj)
            if track_id not in self.object_classes:
                self.object_classes[track_id] = label
                self.object_scores[track_id] = score

            self.count_products(track_id, self.object_classes[track_id])

    def display_info(self, frame):
        """Este método dibuja información en el marco, como el conteo de productos y los estancamientos"""
        cv2.line(frame, (0, self.counter_line_y), (frame.shape[1], self.counter_line_y), (0, 0, 255), 2)
        cv2.putText(frame, f'Paquetes de 1kg: {self.product_count_1kg}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        cv2.putText(frame, f'Paquetes de 500grs: {self.product_count_500grs}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        cv2.putText(frame, f'Estancamiento: {self.stagnation_count}', (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

    def reset_count(self):
        """Este método reinicia el conteo al finalizar un turno"""
        self.product_count_1kg = 0
        self.product_count_500grs = 0
        self.stagnation_count = 0
        self.counted_ids.clear()
        print("Conteo reiniciado.")

    def run(self):
        """Este método ejecuta la captura de video y el conteo de productos"""
        cap = VideoStream(self.video_path).start()
        detector = YOLODetector(self.model_path)

        start_time = time.time()
        while True:
            frame = cap.read()
            if frame is None:
                break

            self.process_frame(frame, detector)
            self.display_info(frame)

            # Mostrar el cuadro
            cv2.imshow("Conteo de productos", frame)

            # Manejo de tiempo para enviar reportes
            current_time = time.time()
            elapsed_time = current_time - start_time

            if elapsed_time >= self.time_interval:
                hour = int((current_time // 3600) % 24)
                subject, body = self.reporte.reportes(hour, self.product_count_1kg + self.product_count_500grs)
                self.reporte.send_email(subject, body)
                start_time = current_time

            # Salir si se presiona 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.stop()
        cv2.destroyAllWindows()
        self.reporte.enviar_reporte_diario(self.product_count_1kg + self.product_count_500grs)

# Llamar a la clase ObjectCounter y ejecutar el método run
if __name__ == "__main__":
    try:
        contador = ObjectCounter(MODEL_PATH, VIDEO_PATH)
        contador.run()
    except Exception as e:
        print(f"Ocurrió un error: {e}")
