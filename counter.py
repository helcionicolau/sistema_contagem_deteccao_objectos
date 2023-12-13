import cv2
import datetime
import imutils
import numpy as np
from centroidtracker import CentroidTracker
import winsound
import smtplib
from email.mime.text import MIMEText
import requests  # Adicionado para fazer solicitações HTTP

# Configurações de e-mail
email_address = "helcio05nicolau@gmail.com"
email_password = "nfcb nmob jfcb nvis"
recipient_email = "helcio05business@gmail.com"

API_BASE_URL = "http://127.0.0.1:5000"  # Substitua pelo URL real da sua API

protopath = "MobileNetSSD_deploy.prototxt"
modelpath = "MobileNetSSD_deploy.caffemodel"
detector = cv2.dnn.readNetFromCaffe(prototxt=protopath, caffeModel=modelpath)

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

# Funções para enviar dados para a API
def send_entry_to_api(object_id):
    entry_time_str = entry_time[object_id].strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "pessoa_id": object_id,
        "entrada_tempo": entry_time_str,
        # Adicione mais campos conforme necessário
    }
    response = requests.post(f"{API_BASE_URL}/pessoa", json=payload)
    if response.status_code == 200:
        print(f"Entrada registrada para ID {object_id} na API.")
    else:
        print(f"Falha ao registrar entrada para ID {object_id} na API.")

def send_exit_to_api(object_id):
    exit_time_str = exit_time_dict[object_id].strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "pessoa_id": object_id,
        "saida_tempo": exit_time_str,
    }
    response = requests.post(f"{API_BASE_URL}/pessoa", json=payload)
    if response.status_code == 200:
        print(f"Saida registrada para ID {object_id} na API.")
    else:
        print(f"Falha ao registrar saída para ID {object_id} na API.")

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

# def send_email(subject, body):
#     try:
#         msg = MIMEText(body)
#         msg["Assunto"] = subject
#         msg["De"] = email_address
#         msg["Para"] = recipient_email

#         server = smtplib.SMTP("smtp.gmail.com", 587)
#         server.starttls()
#         server.login(email_address, email_password)
#         server.sendmail(email_address, recipient_email, msg.as_string())
#         server.quit()
#     except Exception as e:
#         print("Exception occurred in send_email : {}".format(e))
def log_email(pessoa_id, assunto, corpo):
    try:
        # Registro na tabela logemail
        payload = {
            "pessoa_id": pessoa_id,
            "assunto": assunto,
            "corpo": corpo,
            # Adicione mais campos conforme necessário
        }
        response = requests.post(f"{API_BASE_URL}/logemail", json=payload)
        if response.status_code == 200:
            print("Log de e-mail registrado na API.")
        else:
            print("Falha ao registrar log de e-mail na API.")

        # Envio real do e-mail
        msg = MIMEText(corpo)
        msg["Assunto"] = assunto
        msg["De"] = email_address
        msg["Para"] = recipient_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(email_address, email_password)
        server.sendmail(email_address, recipient_email, msg.as_string())
        server.quit()

    except Exception as e:
        print("Exception occurred in log_email : {}".format(e))

def main():
    # Lista de URLs das câmeras
    urls = [
        "rtsp://admin:Afrizona2022@192.168.1.10:554/Streaming/Channels/0",
        "rtsp://admin:Afrizona2022@192.168.1.3:554/Streaming/Channels/1",
        "rtsp://admin:Afrizona2022@192.168.1.61:554/Streaming/Channels/2",
    ]
    # urls = "rtsp://admin:Afrizona2022@192.168.1.56:554/Streaming/Channels/0"
    cap = cv2.VideoCapture(urls[2])

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
                "Erro: Não foi possível capturar o frame. Verifique a conexão da câmera."
            )
            break

        # Reduzir o tamanho da imagem de entrada
        frame = imutils.resize(frame, width=600)

        total_frames = total_frames + 1

        (H, W) = frame.shape[:2]

        # Reduzir a resolução da imagem de entrada
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (W, H), 127.5)

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
            text = "ID: {}".format(objectId + 1)
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
                    f"ID {objectId + 1} entrou às {entry_time[objectId].strftime('%H:%M:%S')}"
                )
                # Envie um e-mail informando a entrada
                log_email(
                    objectId + 1,
                    f"Entrada - ID {objectId + 1}",
                    f"ID {objectId + 1} entrou às {entry_time[objectId].strftime('%H:%M:%S')}",
                )

                # Envie dados de entrada para a API
                send_entry_to_api(objectId)

                # Registre na tabela pessoa
                pessoa_id = objectId + 1
                # Aqui você precisará adaptar conforme a estrutura da sua tabela pessoa
                # Use o objeto entry_time[objectId] para registrar a entrada
                # entry_time[objectId] contém o tempo de entrada da pessoa

        # Verifique se alguma pessoa saiu
        for objectId in list(entry_time.keys()):
            if objectId not in objects:
                if objectId not in exit_time_dict:
                    # Registre o tempo de saída
                    exit_time_dict[objectId] = datetime.datetime.now()

                    # Calcule o tempo de permanência
                    time_in_frame = exit_time_dict[objectId] - entry_time[objectId]

                    print(
                        f"ID {objectId + 1} saiu às {exit_time_dict[objectId].strftime('%H:%M:%S')}. Tempo de permanência: {time_in_frame}",
                    )
                    # Envie um e-mail informando a saída e o tempo de permanência
                    log_email(
                        objectId + 1,
                        f"Saida - ID {objectId + 1}",
                        f"ID {objectId + 1} saiu às {exit_time_dict[objectId].strftime('%H:%M:%S')}. Tempo de permanência: {time_in_frame}",
                    )

                    # Envie dados de saída para a API
                    send_exit_to_api(objectId)

                    # Registre na tabela pessoa
                    pessoa_id = objectId + 1
                    # Aqui você precisará adaptar conforme a estrutura da sua tabela pessoa
                    # Use o objeto exit_time_dict[objectId] para registrar a saída
                    # exit_time_dict[objectId] contém o tempo de saída da pessoa

                    # Remova o ID da lista, se estiver presente
                    if objectId in object_id_list:
                        object_id_list.remove(objectId)

        fps_end_time = datetime.datetime.now()
        time_diff = fps_end_time - fps_start_time
        if time_diff.seconds == 0:
            fps = 0.0
        else:
            fps = total_frames / time_diff.seconds

        fps_text = "FPS: {:.2f}".format(fps)

        cv2.putText(
            frame, fps_text, (5, 30), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 255, 0), 1
        )

        lpc_count = len(objects)
        opc_count = len(object_id_list)

        lpc_txt = "LPC: {}".format(lpc_count)
        opc_txt = "OPC: {}".format(opc_count)

        cv2.putText(
            frame, lpc_txt, (5, 60), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 255, 0), 1
        )
        cv2.putText(
            frame, opc_txt, (5, 90), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 255, 0), 1
        )

        # Se houver 3 ou mais pessoas, reproduza o som
        if lpc_count >= 3:
            winsound.Beep(1000, 500)  # Exemplo: Frequência 1000 Hz, duração 500 ms

        cv2.imshow("Application", frame)
        key = cv2.waitKey(1)
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

main()
