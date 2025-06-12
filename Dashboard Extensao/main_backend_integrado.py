import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
import csv
from datetime import datetime
import os
import paho.mqtt.client as mqtt
import json

# Variáveis globais
timestamps = []
temperaturas = []
umidades = []

buffer_timestamps = []
buffer_temperaturas = []
buffer_umidades = []

# MQTT
broker = "au1.cloud.thethings.network"
port = 1883
username = "lora-teste-02@ttn"
password = "NNSXS.5RDFFZW4OACTQLB2UAEACREAKRO6JABTEI7DLBQ.5IQI4DIWTKWY5VRCNF7LQPCP42VDTMOJSV3G6SEVP35BVAIXG3KA"
topic = "v3/lora-teste-02@ttn/devices/dht-device-01/up"

# Plot
plt.style.use("seaborn-v0_8-darkgrid")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
fig.suptitle("Monitoramento em Tempo Real - TTN MQTT", fontsize=16)

msg_text = fig.text(0.5, 0.01, "", fontsize=10, ha='center', va='bottom',
                    color='green', bbox=dict(facecolor='white', edgecolor='gray'),
                    visible=False)

button_ax = fig.add_axes([0.81, 0.91, 0.1, 0.05])
save_button = Button(button_ax, 'Salvar CSV')

def save_to_csv(event):
    filename = "dados_temperatura_umidade.csv"
    file_exists = os.path.exists(filename)
    write_header = not file_exists or os.stat(filename).st_size == 0

    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if write_header:
            writer.writerow(["Horário", "Temperatura", "Umidade"])
        for t, temp, umi in zip(buffer_timestamps, buffer_temperaturas, buffer_umidades):
            writer.writerow([t.strftime('%Y-%m-%d %H:%M:%S'), temp, umi])

    total = len(buffer_timestamps)
    buffer_timestamps.clear()
    buffer_temperaturas.clear()
    buffer_umidades.clear()

    msg_text.set_text(f"{total} dados salvos em '{filename}'")
    msg_text.set_visible(True)
    fig.canvas.draw()

    def hide_msg():
        msg_text.set_visible(False)
        fig.canvas.draw()

    timer = fig.canvas.new_timer(interval=3000)
    timer.add_callback(hide_msg)
    timer.start()

save_button.on_clicked(save_to_csv)

def update_plot(frame):
    if len(timestamps) == 0:
        return
    print(f"[DEBUG] update_plot() chamado. Total de pontos: {len(timestamps)}")
    ax1.clear()
    ax2.clear()

    timestamps_limit = timestamps[-20:]
    temperaturas_limit = temperaturas[-20:]
    umidades_limit = umidades[-20:]

    ax1.plot(timestamps_limit, temperaturas_limit, label="Temperatura (°C)", color='tab:red')
    ax2.plot(timestamps_limit, umidades_limit, label="Umidade (%)", color='tab:blue')

    ax1.set_ylabel("Temperatura (°C)")
    ax2.set_ylabel("Umidade (%)")
    ax2.set_xlabel("Horário")
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper left")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    fig.autofmt_xdate()

def on_connect(client, userdata, flags, rc):
    print(f"[DEBUG] Conectado ao broker MQTT com código de resultado {rc}")
    client.subscribe(topic)
    print(f"[DEBUG] Inscrito no tópico: {topic}")

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    # print(f"[DEBUG] Payload completo: {json.dumps(payload, indent=2)}")
    try:
        mensagem = payload['uplink_message']['decoded_payload']['message'].split(' ')
        temperatura = float(mensagem[0])
        umidade = float(mensagem[1])
        now = datetime.now()
        timestamps.append(now)
        temperaturas.append(temperatura)
        umidades.append(umidade)
        buffer_timestamps.append(now)
        buffer_temperaturas.append(temperatura)
        buffer_umidades.append(umidade)
        print(f"[DEBUG] Temperatura: {temperatura}, Umidade: {umidade}")
    except Exception as e:
        # print(f"[ERRO] Falha ao processar mensagem: {e}")
        pass

client = mqtt.Client()
client.username_pw_set(username, password)
client.on_connect = on_connect
client.on_message = on_message
client.connect(broker, port, 60)
client.loop_start()

ani = FuncAnimation(fig, update_plot, interval=30000, cache_frame_data=False)
plt.subplots_adjust(bottom=0.15, right=0.95)
plt.show()
