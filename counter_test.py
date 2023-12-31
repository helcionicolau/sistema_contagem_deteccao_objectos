import cv2
import datetime
import imutils
import numpy as np
from centroidtracker import CentroidTracker
import winsound
import smtplib
from email.mime.text import MIMEText
from threading import Thread

# Inicializar o mixer do pygame
# pygame.mixer.init()

# Carregar os sons desejados
# sound_3_or_more = pygame.mixer.Sound("sound_3_or_more.wav")

# Configurações de e-mail
email_address = "helcio05nicolau@gmail.com"
email_password = "nfcb nmob jfcb nvis"
recipient_email = "helcio05business@gmail.com"

protopath = "MobileNetSSD_deploy.prototxt"
modelpath = "MobileNetSSD_deploy.caffemodel"
detector = cv2.dnn.readNetFromCaffe(prototxt=protopath, caffeModel=modelpath)

# Only enable it if you are using OpenVino environment
# detector.setPreferableBackend(cv2.dnn.DNN_BACKEND_INFERENCE_ENGINE)
# detector.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

CLASSES = [
    "background",
    "aeroplane",
    "bicycle",
    "bird",
    "boat",
    "bottle",
    "bus",
    "car",
    "cat",
    "chair",
    "cow",
    "diningtable",
    "dog",
    "horse",
    "motorbike",
    "person",
    "pottedplant",
    "sheep",
    "sofa",
    "train",
    "tvmonitor",
]

tracker = CentroidTracker(maxDisappeared=80, maxDistance=90)

# Dicionário para armazenar o tempo de entrada e saída de cada pessoa
entry_time = {}
exit_time_dict = {}
total_objects_count = 0
entered_count = 0
exited_count = 0


def non_max_suppression_fast(boxes, overlapThresh):
    try:
        if len(boxes) == 0:
            return []

        if boxes.dtype.kind == "i":
            boxes = boxes.astype("float")

        pick = []

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]

        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        idxs = np.argsort(y2)

        while len(idxs) > 0:
            last = len(idxs) - 1
            i = idxs[last]
            pick.append(i)

            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])

            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)

            overlap = (w * h) / area[idxs[:last]]

            idxs = np.delete(
                idxs, np.concatenate(([last], np.where(overlap > overlapThresh)[0]))
            )

        return boxes[pick].astype("int")
    except Exception as e:
        print("Exception occurred in non_max_suppression : {}".format(e))


def send_email(subject, body):
    try:
        msg = MIMEText(body)
        msg["Assunto"] = subject
        msg["De"] = email_address
        msg["Para"] = recipient_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(email_address, email_password)
        server.sendmail(email_address, recipient_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Exception occurred in send_email : {}".format(e))


def process_camera(url, index):
    global total_objects_count, entered_count, exited_count
    cap = cv2.VideoCapture(url)

    fps_start_time = datetime.datetime.now()
    fps = 0
    total_frames = 0
    lpc_count = 0
    op_count = 0
    object_id_list = []

    objects = {}
    while True:
        ret, frame = cap.read()
        if not ret:
            print(
                f"Erro: Não foi possível capturar o frame da câmera {index + 1}. Verifique a conexão da câmera."
            )
            break

        # Reduzir o tamanho da imagem de entrada
        frame = imutils.resize(frame, width=580)

        total_frames = total_frames + 1

        (H, W) = frame.shape[:2]

        # Reduzir a resolução da imagem de entrada
        blob = cv2.dnn.blobFromImage(frame, 0.00365, (W, H), 127.5)

        detector.setInput(blob)
        person_detections = detector.forward()
        rects = []
        for i in np.arange(0, person_detections.shape[2]):
            confidence = person_detections[0, 0, i, 2]
            if confidence > 0.5:
                idx = int(person_detections[0, 0, i, 1])

                if CLASSES[idx] != "person":
                    continue

                person_box = person_detections[0, 0, i, 3:7] * np.array([W, H, W, H])
                (startX, startY, endX, endY) = person_box.astype("int")
                rects.append(person_box)

        boundingboxes = np.array(rects)
        boundingboxes = boundingboxes.astype(int)

        # Aplicar não-máxima supressão
        rects = non_max_suppression_fast(boundingboxes, 0.3)

        # Atualizar o tracker a cada 5 quadros
        if total_frames % 5 == 0:
            objects = tracker.update(rects)

        for objectId, bbox in objects.items():
            x1, y1, x2, y2 = bbox
            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            text = f"ID: {objectId + 1} - Camera: {index + 1}"
            cv2.putText(
                frame,
                text,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_COMPLEX_SMALL,
                1,
                (0, 0, 255),
                1,
            )

            if objectId not in object_id_list:
                # Adicione o ID à lista
                object_id_list.append(objectId)

                # Registre o tempo de entrada
                entry_time[objectId] = datetime.datetime.now()

                print(
                    f"ID {objectId + 1} entrou às {entry_time[objectId].strftime('%H:%M:%S')} - Camera: {index + 1}"
                )
                # Envie um e-mail informando a entrada
                send_email(
                    f"Entrada - ID {objectId + 1}",
                    f"ID {objectId + 1} entrou às {entry_time[objectId].strftime('%H:%M:%S')} - Camera: {index + 1}",
                )

        # Verifique se alguma pessoa saiu
        for objectId in list(entry_time.keys()):
            if objectId not in objects:
                if objectId not in exit_time_dict:
                    # Registre o tempo de saída
                    exit_time_dict[objectId] = datetime.datetime.now()

                    # Calcule o tempo de permanência
                    time_in_frame = (
                        exit_time_dict[objectId] - entry_time[objectId]
                    )

                    print(
                        f"ID {objectId + 1} saiu às {exit_time_dict[objectId].strftime('%H:%M:%S')} - Camera: {index + 1}. Tempo de permanência: {time_in_frame}"
                    )
                    # Envie um e-mail informando a saída e o tempo de permanência
                    send_email(
                        f"Saida - ID {objectId + 1}",
                        f"ID {objectId + 1} saiu às {exit_time_dict[objectId].strftime('%H:%M:%S')} - Camera: {index + 1}. Tempo de permanência: {time_in_frame}",
                    )

                    # Remova o ID da lista, se estiver presente
                    if objectId in object_id_list:
                        object_id_list.remove(objectId)

        fps_end_time = datetime.datetime.now()
        time_diff = fps_end_time - fps_start_time
        if time_diff.seconds == 0:
            fps = 0.0
        else:
            fps = total_frames / time_diff.seconds

        fps_text = f"FPS: {fps:.2f} - Camera: {index + 1}"

        cv2.putText(
            frame,
            fps_text,
            (5, 30),
            cv2.FONT_HERSHEY_COMPLEX_SMALL,
            1,
            (0, 255, 0),
            1,
        )

        lpc_count = len(objects)
        opc_count = len(object_id_list)

        lpc_txt = f"LPC: {lpc_count} - Camera: {index + 1}"
        opc_txt = f"OPC: {opc_count} - Camera: {index + 1}"

        cv2.putText(
            frame,
            lpc_txt,
            (5, 60),
            cv2.FONT_HERSHEY_COMPLEX_SMALL,
            1,
            (0, 255, 0),
            1,
        )
        cv2.putText(
            frame,
            opc_txt,
            (5, 90),
            cv2.FONT_HERSHEY_COMPLEX_SMALL,
            1,
            (0, 255, 0),
            1,
        )

        info_text = f"Total: {total_objects_count}  Entrou: {entered_count}  Saiu: {exited_count}"
        cv2.putText(
            frame,
            info_text,
            (W - 250, 30),
            cv2.FONT_HERSHEY_COMPLEX_SMALL,
            1,
            (0, 255, 0),
            1,
        )

        # Se houver 3 ou mais pessoas, reproduza o som
        # if lpc_count >= 2:
        # sound_3_or_more.play()

        # Se houver 3 ou mais pessoas, reproduza o som
        if opc_count >= 3:
            winsound.Beep(1000, 500)  # Exemplo: Frequência 1000 Hz, duração 500 ms

        cv2.imshow(f"Camera {index + 1}", frame)
        key = cv2.waitKey(1)
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def main():
    # Lista de URLs das câmeras
    urls = [
        'rtsp://admin:Afrizona2022@192.168.1.10:554/Streaming/Channels/0',
        'rtsp://admin:Afrizona2022@192.168.1.3:554/Streaming/Channels/1',
        'rtsp://admin:Afrizona2022@192.168.1.61:554/Streaming/Channels/2',
        # Adicione mais URLs conforme necessário
    ]

    # Inicie uma thread para cada câmera
    threads = []
    for i, url in enumerate(urls):
        thread = Thread(target=process_camera, args=(url, i))
        threads.append(thread)
        thread.start()

    # Aguarde todas as threads terminarem
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
