import cv2

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error al abrir la cámara")
    exit()

while True:
    ret, frame = cap.read()
    
    if not ret:
        print("Error al recibir el frame")
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        message = "100% pilsen"
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(message, font, 1, 2)[0]
        text_x = x + (w - text_size[0]) // 2
        text_y = y - 10
        cv2.putText(frame, message, (text_x, text_y), font, 1, (0, 0, 0), 2)
    
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, binary_frame = cv2.threshold(gray_frame, 95, 255, cv2.THRESH_BINARY)
    
    cv2.imshow('Webcam', binary_frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
