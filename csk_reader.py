import serial
import pandas as pd
from io import StringIO
import os
import numpy as np
import datetime as dt


BAUD = 115200  # Baud rate for the CSKs
DEVICE = "/dev/ttyACM0"  # Location of serial device on ubuntu machine

LINE_LIMIT = 15000  # How many measurements to make? Up to 3 fewer measurements may be made

FILENAME = 'readings'

FRACTIONS = ['1.0', '2.5', '10.0']

if f'{FILENAME}.csv' not in os.listdir('.'):  # Checks whether readings have already been made, starts them if not
    sensor_lines = []
    SERIAL_DEVICE = serial.Serial(DEVICE, BAUD)  # Connect to CSK Sensor
    SERIAL_DEVICE.write(b'monitor\r')  # Enable fast measurements
    while len(sensor_lines) < LINE_LIMIT:
        sensor_output = SERIAL_DEVICE.readline().decode("utf-8")[:-2]  # Get latest measurement, minus return chars
        print(f'{len(sensor_lines)}/{LINE_LIMIT}: {sensor_output}')  # Print output
        sensor_lines.append(f'{sensor_output}\n')  # Add output with newline char

    SERIAL_DEVICE.write(b'reset\r')  # Turn off monitor mode by resetting CSK

    monitor_identities = ['SCK > monitor\n', 'monitor\n']  # Commands sent to CSK that were accidentally saved
    for monitor_str in monitor_identities:
        if monitor_str in sensor_lines:
            monitor_index = sensor_lines.index(monitor_str)
            sensor_lines = sensor_lines[monitor_index+1:]

    csv_string = ""  # Initialise string that will contain csv data

    for line in sensor_lines:
        csv_string = f'{csv_string}{line}'

    sensor_df = pd.read_csv(StringIO(csv_string), delimiter='\t')  # Convert saved CSK data to CSV
    sensor_df.to_csv(f'{FILENAME}.csv', index=None)  # Save data

sensor_df = pd.read_csv(filepath_or_buffer=f'{FILENAME}.csv')
number_of_rows = sensor_df.shape[0]
sensor_on_bool, sensor_off_bool = False, False  # Assume that PM sensor isn't turning on or off in 1st line
previous_pm_sensor_shutdown = None  # Initialise the variable for previous sensor shutoff
millis_values_split = {
    'No Change': [],
    'PM Sensor On': [],
    'PM Sensor Off': [],
    'Measurement Length (s)': [],
    'Measurement Length - PM On (s)': [],
    'Measurement Length - PM Off (s)': []
}

measurement_period_indices = list()

for row_index in range(1, number_of_rows - 1):
    if sensor_on_bool or sensor_off_bool:
        # Skip the row after sensor turning on or off. Occasionally sensor would turn off over two measurements which
        # would mess up the program
        sensor_on_bool, sensor_off_bool = False, False
        continue
    pm_values = {}
    off_list = []
    for fraction in FRACTIONS:  # Loop over PM fractions to see if any are switching on/off
        on = (sensor_df.loc[row_index, f'PM {fraction}'] != 'none' and
              sensor_df.loc[row_index - 1, f'PM {fraction}'] == 'none')
        off = (sensor_df.loc[row_index, f'PM {fraction}'] == 'none' and
               sensor_df.loc[row_index - 1, f'PM {fraction}'] != 'none')
        if on:
            sensor_on_bool = True
            break  # Quit out of fractions loop
        elif off:
            sensor_off_bool = True
            break  # Quit out of fractions loop

    millis_value = sensor_df.loc[row_index + 1, 'Miliseconds']  # Milliseconds is spelt wrong in the file given by CSK
    if sensor_on_bool:
        millis_values_split['PM Sensor On'].append(millis_value)
    elif sensor_off_bool:
        millis_values_split['PM Sensor Off'].append(millis_value)
        measurement_period_indices.append(row_index)
    else:
        millis_values_split['No Change'].append(millis_value)


for list_index, table_index in enumerate(measurement_period_indices[:-1]):
    start_index = table_index
    end_index = measurement_period_indices[list_index + 1]

    measurement_millis_str = list(sensor_df.loc[start_index:end_index, 'Miliseconds'])
    measurement_millis_int = [int(millis) for millis in measurement_millis_str]
    measurement_millis_int.sort(reverse=True)
    millis_sum = sum(measurement_millis_int)

    pm_sensor_on = measurement_millis_int[1]  # Assume om sensor turning on is always second highest value, it is
    pm_sensor_off = measurement_millis_int[0]  # Assume pm sensor turning off is always highest value, which it is

    millis_values_split['Measurement Length (s)'].append(np.round(millis_sum / 1000, 3))
    # How long was the measurement?
    millis_values_split['Measurement Length - PM On (s)'].append(np.round((millis_sum - pm_sensor_on) / 1000, 3))
    # How long was the measurement minus the PM sensor turning on
    millis_values_split['Measurement Length - PM Off (s)'].append(np.round((millis_sum - pm_sensor_off) / 1000, 3))
    # How long was the measurement minus the PM sensor turning off

pre_csv = {
    'Event': [],
    'Mean ms': [],
    'STD ms': [],
    'Min ms': [],
    'Max ms': [],
    'Span ms': []
}

for val, item in millis_values_split.items():
    relevant_info = [val, np.round(np.mean(item), 2), np.round(np.std(item), 2), min(item), max(item), max(item) - min(item)]
    for index, key in enumerate(pre_csv.keys()):
        pre_csv[key].append(relevant_info[index])
    analysis_csv = pd.DataFrame(data=pre_csv)
    analysis_csv.to_csv(f'{FILENAME} (analysis).csv', index=None)
