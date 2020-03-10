import serial
import pandas as pd
from io import StringIO
import os
import numpy as np
import datetime as dt
BAUD = 115200
DEVICE = "/dev/ttyACM0"

LINE_LIMIT = 10000

FILENAME = 'readings'

FRACTIONS = ['1.0', '2.5', '10.0']

if f'{FILENAME}.csv' not in os.listdir('.'):
    sensor_lines = []
    SERIAL_DEVICE = serial.Serial(DEVICE, BAUD)
    SERIAL_DEVICE.write(b'monitor\r')
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
    sensor_df.to_csv(f'{FILENAME}.csv')

sensor_df = pd.read_csv(filepath_or_buffer=f'{FILENAME}.csv')
number_of_rows = sensor_df.shape[0]
sensor_on_bool, sensor_off_bool = False, False

millis_values_split = {
    'No Change': [],
    'PM Sensor On': [],
    'PM Sensor Off': []
}

for row_index in range(1, number_of_rows - 1):
    if sensor_on_bool or sensor_off_bool:
        sensor_on_bool, sensor_off_bool = False, False
        continue
    pm_values = {}
    off_list = []
    for fraction in FRACTIONS:
        on = (sensor_df.loc[row_index, f'PM {fraction}'] != 'none' and
              sensor_df.loc[row_index - 1, f'PM {fraction}'] == 'none')
        off = (sensor_df.loc[row_index, f'PM {fraction}'] == 'none' and
               sensor_df.loc[row_index - 1, f'PM {fraction}'] != 'none')
        if on:
            sensor_on_bool = True
            continue
        elif off:
            sensor_off_bool = True
            continue

    millis_value = sensor_df.loc[row_index + 1, 'Miliseconds']

    if sensor_on_bool:
        millis_values_split['PM Sensor On'].append(millis_value)
    elif sensor_off_bool:
        millis_values_split['PM Sensor Off'].append(millis_value)
    else:
        millis_values_split['No Change'].append(millis_value)

pre_csv = {
    'Event': [],
    'Mean ms': [],
    'STD ms': [],
    'Min ms': [],
    'Max ms': [],
    'Span ms': []
}
for val, item in millis_values_split.items():
    relevant_info = [val, np.mean(item), np.std(item), min(item), max(item), max(item) - min(item)]
    for index, key in enumerate(pre_csv.keys()):
        pre_csv[key].append(relevant_info[index])
    analysis_csv = pd.DataFrame(data=pre_csv)
    analysis_csv.to_csv('analysis.csv', index=None)
