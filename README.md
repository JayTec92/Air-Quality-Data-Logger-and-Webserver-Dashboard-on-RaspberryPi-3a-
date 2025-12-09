# Air-Quality-Data-Logger-and-Webserver-Dashboard-on-RaspberryPi-3a-
Script to measure temperature, humidity, and particulate matter and save the data in CSV. Second Script "Webserver" for reading the CSV and generate dashboard in your local network
Hardware: RaspberryPi 3A+, DHT22 Sensor, Waveshare HM3301 Sensor.
PiOS - Its Important to install a "Debian Bookworm" version on your Pi. 
With these instruction you can programming your PI trough a SSH-connection if you enable SSH and set up your WiFi access on the installation of your PiOS
Connect DHT22 Sensor with PI. Pin1(3,3v+), Pin7(GPIO 4 for Sensor "out"), Pin9 (GND)
Connect HM3301 Sensor with PI. Pin4(5v+), Pin6(GND), Pin3 (SDA1) and Pin5 (SCL1)


1) Grundsystem aktualisieren

sudo apt update
sudo apt upgrade -y

3) Notwendige Systempakete installieren

sudo apt install -y python3 python3-venv python3-pip python3-serial \
                    i2c-tools pigpiod python3-pigpio
3) I2C aktivieren (HM3301)

sudo raspi-config

Interface Options
 → I2C → Enable

sudo reboot

i2cdetect -y 1
   - sollte Adresse 0x40 zeigen

4) Serial UART aktivieren (für zukünftige Sensoren)

sudo raspi-config

Interface Options
 → Serial Port
Login shell über serial? → Nein

Serial port hardware enable? → Ja

sudo reboot

5) Arbeitsverzeichnis anlegen

mkdir -p ~/Desktop/Sensortest
cd ~/Desktop/Sensortest


6) Python Virtual Environment einrichten

python3 -m venv env
source env/bin/activate

7) Python-Bibliotheken installieren

pip install adafruit-circuitpython-dht
sudo apt install -y libgpiod2

pip install smbus2

pip install pyserial

8) pigpiod aktivieren (für DHT22)

sudo systemctl enable pigpiod
sudo systemctl start pigpiod

systemctl status pigpiod

9) HM3301 Testskript speichern

nano hm_test.py


import smbus2
import time

bus = smbus2.SMBus(1)
addr = 0x40

while True:
    data = bus.read_i2c_block_data(addr, 0x00, 29)

    pm1  = (data[4] << 8) | data[5]
    pm25 = (data[6] << 8) | data[7]
    pm10 = (data[8] << 8) | data[9]

    print(f"PM1.0={pm1}  PM2.5={pm25}  PM10={pm10}")
    time.sleep(1)



Testen: python hm_test.py

10) DHT22 Testskript speichern

nano dht_test.py

import time
import board
import adafruit_dht

dht = adafruit_dht.DHT22(board.D4)

while True:
    try:
        t = dht.temperature
        h = dht.humidity
        print(f"Temp: {t:.1f}°C   Humidity: {h:.1f}%")
    except Exception as e:
        print("Fehler:", e)
    time.sleep(2)


11) Kompletter Sensor-Logger (HM3301 + DHT22)

nano sensor_logger.py

---here Comes Sensor_logger.py

12) Logger starten



cd ~/Desktop/Sensortest
source env/bin/activate
python sensor_logger.py


Logdatei unter: ~/Desktop/Sensortest/sensor_log.csv

WEBSERVER Config:

1. Flask installieren:

cd ~/Desktop/Sensortest
source env/bin/activate
pip install flask

WebserverCode:

----here comes script of webserver_dashboard.py

running:

cd ~/Desktop/Sensortest
source env/bin/activate
python web_dashboard.py

see dashboard:

http://localhost:8000/

http://<IP-des-Pi>:8000/


have fun ()



