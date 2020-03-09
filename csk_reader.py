import serial
import pandas as pd
from io import StringIO

BAUD = 115200
DEVICE = "/dev/ttyACM0"

SERIAL_DEVICE = serial.Serial(DEVICE, BAUD)
SERIAL_DEVICE.write(b'monitor\r')

LINE_LIMIT = 10000

sensor_lines = []

while len(sensor_lines) < LINE_LIMIT:
    sensor_output = SERIAL_DEVICE.readline().decode("utf-8")[:-2]
    print(f'{len(sensor_lines)}/{LINE_LIMIT}: {sensor_output}')
    sensor_lines.append(f'{sensor_output}\n')

SERIAL_DEVICE.write(b'reset\r')

monitor_identities = ['SCK > monitor\n', 'monitor\n']
for monitor_str in monitor_identities:
    if monitor_str in sensor_lines:
        monitor_index = sensor_lines.index(monitor_str)
        sensor_lines = sensor_lines[monitor_index+1:]


csv_string = ""
for line in sensor_lines:
    csv_string = f'{csv_string}{line}'

sensor_df = pd.read_csv(StringIO(csv_string), delimiter='\t')
sensor_df.to_csv('readings.csv')

