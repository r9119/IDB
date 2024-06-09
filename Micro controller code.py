import board
import busio
import digitalio
import time
import neopixel
import adafruit_scd30
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_esp32spi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_esp32spi import adafruit_esp32spi

# Constants
INTERVAL = 15

# Set your Wi-Fi ssid and password
WIFI_SSID = "QL-28923"
WIFI_PASSWORD = ""

# ThingSpeak MQTT credentials
MQTT_SERVER = "mqtt3.thingspeak.com"
MQTT_USERNAME = ""
MQTT_PASSWORD = ""
MQTT_CLIENT_ID = ""
CHANNEL_ID = ""
WRITE_API_KEY = ""

# FeatherWing ESP32 AirLift, nRF52840
cs = digitalio.DigitalInOut(board.D13)
rdy = digitalio.DigitalInOut(board.D11)
rst = digitalio.DigitalInOut(board.D12)

# Getting the I2C object and SCD sensor
i2c = board.I2C()
scd = adafruit_scd30.SCD30(i2c)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
wifi = adafruit_esp32spi.ESP_SPIcontrol(spi, cs, rdy, rst)
socket.set_interface(wifi)

# Define pixels and colour dict
pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.1)

colours = {
    'off': (0, 0, 0),
    'white': (255, 255, 255),
    'red': (255, 0, 0),
    'green': (0, 255, 0),
    'blue': (0, 0, 255),
    'yellow': (255, 255, 0),
    'purple': (255, 0, 255),
    'cyan': (0, 255, 255),
    'orange': (255, 165, 0),
    'dark_green': (0, 50, 0),
    'amber': (255, 191, 0)
}

def change_pixel_colour(colour):
    pixels[0] = colours[colour]

while not wifi.is_connected:
    print("\nConnecting to Wi-Fi...")
    try:
        wifi.connect_AP(WIFI_SSID, WIFI_PASSWORD)
    except ConnectionError as e:
        print("Connection failed, retrying...")
        continue

print("Wi-Fi connected to", str(wifi.ssid, "utf-8"))
print("IP address", wifi.pretty_ip(wifi.ip_address))

def handle_connect(client, userdata, flags, rc):
    print("Connected to {0}".format(client.broker))

def handle_publish(client, userdata, topic, pid):
    print("Published to {0} with PID {1}".format(topic, pid))

mqtt_client = MQTT.MQTT(broker=MQTT_SERVER,
                         username=MQTT_USERNAME,
                         password=MQTT_PASSWORD,
                         client_id=MQTT_CLIENT_ID,
                         socket_pool=socket)

mqtt_client.on_connect = handle_connect
mqtt_client.on_publish = handle_publish

# Connect to MQTT broker
try:
    mqtt_client.connect()
except RuntimeError as e:
    print("MQTT connection failed", e)
    raise Exception("MQTT connection failed")

# Defining CO2 ppm level thresholds
GOOD_TH = 750
OK_TH = 1000
# BAD_TH = 2000

# Main Loop
while True:
    try:
        # Read temp, co2 and humidity?
        temperature = round(scd.temperature, 1)
        relative_humidity = round(scd.relative_humidity, 1)
        co2_ppm_level = round(scd.CO2, 1)

        # data_string = "{\"channel\": \"" + CHANNEL_ID + "\", \"write_api_key\": \"" + WRITE_API_KEY + "\", \"updates\": [{\"field1\": \"" + str(temperature) + "\", \"field2\": \"" + str(relative_humidity) + "\", \"field3\": \"" + str(co2_ppm_level) + "\"}]}"

        print("")
        print(f'Temperature: {temperature}°C')
        print(f'Relative Humidity: {relative_humidity}%')
        print(f'CO2 PPM Level: {co2_ppm_level}ppm')

        # Set led colour to match ppm level
        if co2_ppm_level <= GOOD_TH:
            change_pixel_colour('dark_green')
        elif (co2_ppm_level > GOOD_TH) and (co2_ppm_level <= OK_TH):
            change_pixel_colour('amber')
        elif co2_ppm_level > OK_TH:
            change_pixel_colour('red')

        # Log the readings
        try:
            mqtt_client.publish("channels/" + CHANNEL_ID + "/publish/fields/field1", str(temperature))
            time.sleep(1)
            mqtt_client.publish("channels/" + CHANNEL_ID + "/publish/fields/field2", str(relative_humidity))
            time.sleep(1)
            mqtt_client.publish("channels/" + CHANNEL_ID + "/publish/fields/field3", str(co2_ppm_level))
        except ConnectionError as e:
            print("MQTT publish failed", e)
        
        # Wait out the interval
        time.sleep(INTERVAL)
    except RuntimeError as e:
        print(e)

