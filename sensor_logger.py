import time
import datetime
import os
import csv

import smbus2
import board
import adafruit_dht

# -----------------------------
# Konfiguration
# -----------------------------

LOG_INTERVAL = 60  # Sekunden zwischen Log-Einträgen

HM_I2C_BUS = 1
HM_ADDR = 0x40

# DHT22 an GPIO4
DHT_PIN = board.D4

LOGFILE = os.path.expanduser("~/Desktop/Sensortest/sensor_log.csv")


# -----------------------------
# Sensor-Initialisierung
# -----------------------------

bus = smbus2.SMBus(HM_I2C_BUS)
dht = adafruit_dht.DHT22(DHT_PIN)

last_pm1 = None
last_pm25 = None
last_pm10 = None
last_temp = None
last_hum = None


def read_hm3301(max_tries=3, delay=2.0):
    """
    Liest den HM3301 bis zu max_tries mal aus und mittelt die Werte.
    Gibt (pm1, pm25, pm10, status) zurück.
    status = "ok" oder "fallback" oder "error"
    """
    global last_pm1, last_pm25, last_pm10

    vals_pm1 = []
    vals_pm25 = []
    vals_pm10 = []

    for i in range(max_tries):
        try:
            data = bus.read_i2c_block_data(HM_ADDR, 0x00, 29)
            pm1  = (data[4] << 8) | data[5]
            pm25 = (data[6] << 8) | data[7]
            pm10 = (data[8] << 8) | data[9]

            vals_pm1.append(pm1)
            vals_pm25.append(pm25)
            vals_pm10.append(pm10)

            # kurze Pause zwischen den Messungen
            time.sleep(delay)
        except Exception as e:
            print(f"[HM3301] Lesefehler (Versuch {i+1}/{max_tries}): {e}")
            time.sleep(delay)

    if vals_pm1:
        pm1_avg = sum(vals_pm1) / len(vals_pm1)
        pm25_avg = sum(vals_pm25) / len(vals_pm25)
        pm10_avg = sum(vals_pm10) / len(vals_pm10)

        last_pm1, last_pm25, last_pm10 = pm1_avg, pm25_avg, pm10_avg
        return pm1_avg, pm25_avg, pm10_avg, "ok"

    # Falls keine gültigen Werte: letzten gültigen Wert nutzen, wenn vorhanden
    if last_pm1 is not None:
        print("[HM3301] Keine neuen gültigen Werte, nutze letzte gültige Messung.")
        return last_pm1, last_pm25, last_pm10, "fallback"

    # Gar nichts vorhanden
    print("[HM3301] Keine Messung möglich, noch kein gültiger Wert vorhanden.")
    return None, None, None, "error"


def read_dht22(max_tries=5, delay=2.0):
    """
    Liest den DHT22 bis zu max_tries mal aus und mittelt die Werte.
    Gibt (temp_c, humidity, status) zurück.
    status = "ok" oder "fallback" oder "error"
    """
    global last_temp, last_hum

    temps = []
    hums = []

    for i in range(max_tries):
        try:
            t = dht.temperature
            h = dht.humidity

            if t is not None and h is not None:
                temps.append(t)
                hums.append(h)
            else:
                print(f"[DHT22] Ungültige Messung (None) Versuch {i+1}/{max_tries}")

        except Exception as e:
            # DHT wirft gerne mal Exceptions, das ist normal
            print(f"[DHT22] Lesefehler (Versuch {i+1}/{max_tries}): {e}")

        time.sleep(delay)

    if temps:
        temp_avg = sum(temps) / len(temps)
        hum_avg = sum(hums) / len(hums)

        last_temp, last_hum = temp_avg, hum_avg
        return temp_avg, hum_avg, "ok"

    # keine neuen Werte, auf letzte gültige zurückfallen
    if last_temp is not None:
        print("[DHT22] Keine neuen gültigen Werte, nutze letzte gültige Messung.")
        return last_temp, last_hum, "fallback"

    print("[DHT22] Keine Messung möglich, noch kein gültiger Wert vorhanden.")
    return None, None, None, "error"


def ensure_logfile():
    """
    Erzeugt die CSV-Datei mit Header, falls sie noch nicht existiert.
    """
    if not os.path.exists(LOGFILE):
        with open(LOGFILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "pm1",
                "pm2_5",
                "pm10",
                "temp_c",
                "humidity",
                "dht_status",
                "hm_status",
            ])
        print(f"[INFO] Neues Logfile erstellt: {LOGFILE}")


def main():
    ensure_logfile()
    last_log_time = 0

    print("[INFO] Starte Sensor-Logger. Abbruch mit STRG+C.")

    try:
        while True:
            now = time.time()

            if now - last_log_time >= LOG_INTERVAL:
                timestamp = datetime.datetime.now().isoformat(timespec="seconds")

                print(f"\n[{timestamp}] Messe Sensoren...")

                temp, hum, dht_status = read_dht22()
                pm1, pm25, pm10, hm_status = read_hm3301()

                # Fürs Log: None durch leere Strings ersetzen
                row_pm1 = f"{pm1:.1f}" if pm1 is not None else ""
                row_pm25 = f"{pm25:.1f}" if pm25 is not None else ""
                row_pm10 = f"{pm10:.1f}" if pm10 is not None else ""
                row_temp = f"{temp:.2f}" if temp is not None else ""
                row_hum = f"{hum:.2f}" if hum is not None else ""

                # In CSV schreiben
                with open(LOGFILE, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        timestamp,
                        row_pm1,
                        row_pm25,
                        row_pm10,
                        row_temp,
                        row_hum,
                        dht_status,
                        hm_status,
                    ])

                print(f"[LOG] PM1={row_pm1}  PM2.5={row_pm25}  PM10={row_pm10}  "
                      f"T={row_temp}°C  H={row_hum}%  "
                      f"(DHT:{dht_status} HM:{hm_status})")

                last_log_time = now

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Beende Logger...")

    finally:
        try:
            bus.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
