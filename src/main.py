"""
File:			boot.py
Author: 		Zachary Milke
Description:	This file controls the behavior of the system that monitors the environment in and
    around my fish tank. It measures the water temperature on opposite sides of the tank, as well
    as the air temperature and humidity outside the tank. Measurements are displayed on a 0.96"
    OLED display and periodically updated at an interval defined below.

Created on: 10-FEB-2025
Updated on: 14-FEB-2025

Changelog
----------
10-FEB-2025: 
    - Module created

14-FEB-2025:
    - Adds a 5 second delay before the main loop begins to help when testing the program. This
        keeps the device from putting itself to sleep, preventing myself from triggering the
        KeyboardInterrupt exception to run commands using the microcontrollers interpreter. THIS
        MAY BE REMOVED IF THIS BEHAVIOR IS NOT DESIRED.
    - Adds error loop function consolidates error code.
    - Adds push button peripheral that dumps the temporary data to storage when pressed.
    - No longer attempts to dump data to storage if no data are passed.
    - Adds a check for an existing data file when the system starts, removing the annoyance of a 
        a new data file being created each time the program begins, leading to numerous junk files.

17-FEB-2025:
    - Removes unnecessary imports.
    - Refines comments.
    - Fixes issue where f2c function was producing incorrect values.
    - Adds ability to connect to WiFi with SSID/Password.
    - Adds function that sets system time using NTP.
    - Adds timestamps to measurement data containers.
"""


# -------------------------------------------------------------------------------------------------
# Required Imports --------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

from micropython import (
    const,                          # Defining constants
    alloc_emergency_exception_buf   # Helpful when debugging. See MicroPython docs for more info
)
from machine import (
    soft_reset,                     # Soft resetting the device
    RTC,                            # Real time clock
    freq,                           # Setting the CPU clock frequency
    Pin,						    # GPIO access
    SoftI2C,					    # Communicating with I2C devices
    lightsleep,					    # Putting device to sleep
    SPI,                            # Required to use SoftSPI 
    SoftSPI                         # Communicating with devices using SoftSPI
)
from utime import (
    sleep_ms,                       # Short duration delays
    localtime                       # Timestamps
)
from os import (
    VfsFat,                         # Unix-like virtual file system
    mount,                          # Mounting the SD card
    listdir,                        # Listing contents of a directory
    chdir,                          # Changing the CWD
    stat                            # Getting file statistics
)
from ssd1306 import SSD1306_I2C	    # Controlling OLED display
from dht import DHT11			    # Controlling air temperature & humidity sensor
from ds18x20 import DS18X20		    # Controlling water temperature sensor
from sdcard import SDCard           # Controlling an SD Card module
from esp32 import (
    wake_on_ext0,                   # Waking the device up with GPIO interrupt
    WAKEUP_ANY_HIGH                 # Wakeup option triggered when pin pulled high
)

import onewire                      # Onewire interface


# -------------------------------------------------------------------------------------------------
# General Settings --------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

# Time in seconds between measurements. This value MUST NOT go below two (2) seconds, as the DHT11 
#   sensor can take up to two (2) seconds to update, and the DS18B20 sensors need at least 750ms to
#   update. These delays are accounted for in the code body. This value is meant to be modified.
_MEASURE_DELAY_SEC: int = const(60)

# Time in milliseconds between measurements. This value is NOT TO BE MODIFIED
_MEASURE_DELAY_MS: int = const(_MEASURE_DELAY_SEC * 1_000)

# Should the system display measurements in Fahrenheit (True) or Celsius (False)?
_USE_FAHRENHEIT_UNITS: bool = True

# Number of data containers to hold in the data queue
_DATA_QUEUE_MAX_LEN: int = const(30)

# Maximum size a data file size in MB
_DATA_FILE_MAX_SIZE_MB: float = const(2.0)

# Path to root tank data dir
_ROOT_DIR_PATH: str = const("/tank_data")

# Path to measurements directory where data files are stored
_MEASUREMENTS_DIR_PATH: str = const(f"{_ROOT_DIR_PATH}/measurements")

# Data file name prefix
_DATA_FILE_NAME_PREFIX: str = const("tank_measurements_")
_DATA_FILE_EXTENSION: str = const(".csv")

# Column headers for the data file
_DATA_FILE_HEADER: str = const("timestamp,air_temp_1,water_temp_1,water_temp_2\n")

# Path to the current data file
current_data_file_path: str = None

# Frequency at which the CPU will run. On the ESP32 used for testing, the base frequency is
#   160_000_000 Hz, or 160 MHz. If changing the frequency isn't necessary, this whole section may
#   be commented out to prevent useless variables being created in memory.
#
#   THIS VALUE MUST BE AN INT. Calling freq() with anything else will thrown an exception.
_BASE_CPU_FREQ_HZ: int = const(160_000_000)
_HALF_CPU_FREQ_HZ: int = const(_BASE_CPU_FREQ_HZ // 2)
# _ONE_AND_HALF_CPU_FREQ_HZ: int = const(int(_BASE_CPU_FREQ_HZ * 1.5))

# Call the freq() function using the desired frequency as an input.
# freq(_BASE_CPU_FREQ_HZ)
freq(_HALF_CPU_FREQ_HZ)
# freq(_ONE_AND_HALF_CPU_FREQ_HZ)

# Change the following line to False if you don't want to enable wireless features.
_ENABLE_WIFI: bool = const(True)

# Credentials used to connect to lthe users network. A wireless connection is recommended as it is
#   required for setting the system time at startup. Correct system time is required as it is the
#   driver behind the timestamps taken at the point of each measurement.
_WIFI_SSID: str = const("[INSERT SSID HERE]")
_WIFI_PASS: str = const("[INSERT PASSWORD HERE]")

# Real time clock used for timestamps
rtc: RTC = RTC()

# Offsets used to adjust for time zones
_TIMEZONE_OFFSET_HOUR: float = const(-5.0)
_TIMEZONE_OFFSET_SEC: int = const(int(_TIMEZONE_OFFSET_HOUR * 3600))


# -------------------------------------------------------------------------------------------------
# Peripherals -------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

# Onboard LED setup used to indicate system events ocurring
onboard_led: Pin = Pin(2, Pin.OUT, value=0)

# Button used to manually trigger a data write from temp to persistent storage. In the build used
#   when prototyping the system, this button was debounced using a monostable 555 circuit to 
#   prevent multiple presses being registered in the case of button contact bouncing.
write_button: Pin = Pin(35, Pin.IN, Pin.PULL_DOWN)

# Flag used to tell the system when to dump the data should the dump button be pressed
manual_data_dump_triggered: bool = False

# I2C instance for devices communicating using I2C
i2c: SoftI2C = SoftI2C(sda=Pin(21), scl=Pin(22))

# SPI instance for devices communicating using SPI
spi: SoftSPI = SoftSPI(1, sck=Pin(18), mosi=Pin(23), miso=Pin(19))

# OLED Display - Used to display system information
_OLED_WIDTH: int = const(128)
_OLED_HEIGHT: int = const(64)
display: SSD1306_I2C = SSD1306_I2C(_OLED_WIDTH, _OLED_HEIGHT, i2c)

# DS18B20 Waterproof Temperature Sensors - Used to measure the temperature of the water in the tank
ds_sensor_list: list = []
ds_sensors = DS18X20(onewire.OneWire(Pin(4)))

# DHT11 Air Temperature Sensor - Used to measure the temperature of the air surrounding the tank
dht_sensor = DHT11(Pin(32))

# SD Card Module - Used to act as persistent storage so that data may be read on another device
sd_controller: SDCard = SDCard(spi, Pin(5))
vfs: VfsFat = None


# -------------------------------------------------------------------------------------------------
# Measurement Variables ---------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

# Character used to display temperature units
_TEMP_UNITS: str = const('F') if _USE_FAHRENHEIT_UNITS else const('C')

# Number of readings that have taken place
measurement_count: int = 0

# Number of times the current data file has been written to
data_file_write_count: int = 0

# Value used to indicate an invalid temperature variable
_INVALID_READING_VALUE: float = -999_999.0

# Container used to store individual measurement data for both air and water values
class MeasurementData:
    def __init__(self,
                 _timestamp: str,
                 _air_temp_1: float = None, 
                 _water_temp_1: float = None, _water_temp_2: float = None):
        # Assign class fields by checking if the arguments are None
        self.timestamp: str = _timestamp
        self.air_temp_1: float = _air_temp_1 \
            if _air_temp_1 is not None else _INVALID_READING_VALUE
        self.water_temp_1: float = _water_temp_1 \
            if _water_temp_1 is not None else _INVALID_READING_VALUE
        self.water_temp_2: float = _water_temp_2 \
            if _water_temp_2 is not None else _INVALID_READING_VALUE
    
    def __str__(self) -> tuple:
        """ This function overrides the base string function and outputs class data as a tuple of
        values. """
        
        return self.timestamp, self.air_temp_1, self.water_temp_1, self.water_temp_2
    
    def is_valid(self) -> bool:
        """ Checks if the current fields are valid by comparing them to the invalid value.
        
        returns
        -----
        True when data are valid, False, otherwise.
        """
        
        return self.air_temp_1 != _INVALID_READING_VALUE \
            and self.water_temp_1 != _INVALID_READING_VALUE \
                and self.water_temp_2 != _INVALID_READING_VALUE

# List of data containers to act as temporary storage
data_queue: list[MeasurementData] = []


# -------------------------------------------------------------------------------------------------
# Static Methods ----------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

def c2f(_temp_c: float) -> float:
    """ Convert a temperature in degrees Celsius to degrees Fahrenheit.
    
    params
    -----
    _temp_c [float, required] A temperature in degrees Celsius.
    
    returns
    -----
    Temperature converted to degrees Fahrenheit.
    """
    
    return (_temp_c * 9.0 / 5.0) + 32.0


def f2c(_temp_f: float) -> float:
    """ Convert a temperature in degrees Fahrenheit to degrees Celsius.
    
    params
    -----
    _temp_f [float, required] A temperature in degrees Fahrenheit.
    
    returns
    -----
    Temperature converted to degrees Celsius.
    """
    
    return (_temp_f - 32.0) * (5.0 / 9.0)


def take_measurement(increment_counter: bool = True) -> MeasurementData:
    """ Read the values from the air and water sensors.
    
    params
    -----
    increment_counter [bool, optional] Boolean telling the system if it should increment the 
        measurement counter value.
    
    returns
    -----
    MeasurementData instance with updated values.
    """
    
    # Update the sensors (if necessary)
    dht_sensor.measure()
    ds_sensors.convert_temp()
    
    # Get the timestamp
    _timestamp: str = format_system_time(rtc.datetime())
    
    # Create a new data container
    _data_container: MeasurementData = MeasurementData(_timestamp)
    
    try:
        # Read the sensor values into local variables
        _air_temp_1: float = dht_sensor.temperature()
        _water_temp_1: float = ds_sensors.read_temp(ds_sensor_array[0])
        _water_temp_2: float = ds_sensors.read_temp(ds_sensor_array[1])
    
        # Convert the temperatures to Fahrenheit
        _air_temp_1 = c2f(_air_temp_1)
        _water_temp_1 = c2f(_water_temp_1)
        _water_temp_2 = c2f(_water_temp_2)
    
        # Fill in the data container with the values
        _data_container.air_temp_1 = _air_temp_1
        _data_container.water_temp_1 = _water_temp_1
        _data_container.water_temp_2 = _water_temp_2
    except onewire.OneWireError:
        # Sensors could not be detected, possibly due to a faulty connection
        print("OneWireError occurred, could not read values into the data container.")
    except Exception as err:
        # Some other exception occurred.
        print("Other exception occurred:\n\n" /
            "-" * 25 /
            f"{err}" /
            "-" * 25 /
            "\n\n"
        )
        
    if increment_counter:
        # Get the necessary global variable
        global measurement_count
        
        # Increment the measurement count
        measurement_count += 1
    
    # Return the data container
    return _data_container


def count_data_files() -> int:
    """ Counts the number of data files within the data directory. 
    
    returns
    -----
    The number of data files located within the data directory.
    """
    
    # Return the number of items within the measurements directory
    return len(listdir(_MEASUREMENTS_DIR_PATH))


def create_data_file(check_last_file: bool = False) -> str:
    """ Creates and sets the data file path. 
    
    params
    -----
    check_last_file [bool, optional] Boolean used to indicate if the system should get the last
        data file created. This is helpful when the system first begins, as it prevents it from
        creating a new data file each time it begins.
    
    returns
    -----
    The path to the new data file.
    """
    
    # Count the number of data files currently in the data directory
    _data_file_count: int = count_data_files()
    
    # Manage the check_last_file parameter, only if there are data files present.
    if _data_file_count > 0 and check_last_file:
        # Get the list of files in the current directory and return the last one as it should be
        #   the most recently created data file.
        return listdir()[-1]
    
    # Use the data file prefix to create a new csv file
    _file_name: str = f"{_DATA_FILE_NAME_PREFIX}{_data_file_count}{_DATA_FILE_EXTENSION}"
    
    # Get the full path to the new data file
    _file_path: str = f"{_MEASUREMENTS_DIR_PATH}/{_file_name}"
    
    # Create the file in write mode
    with open(_file_path, 'w', encoding="utf-8") as _f:
        # Write the data file header to the file
        _f.write(_DATA_FILE_HEADER)
    
    # Return the path to the data file
    return _file_path


def dump_to_storage(_data: list[MeasurementData]) -> None:
    """ Writes given data to persistent storage in the form of an SD card.
    
    params
    -----
    _data [list[MeasurementData], required] A list of measurement data to be written.
    """
    
    # Only write to storage if data were passed
    if not _data or len(_data) == 0:
        # No data passed, return
        return
    
    # Get the necessary global variables
    global data_file_write_count
    global current_data_file_path
    
    # Convert the data to a list of strings
    _lines: list[str] = []
    for _d in _data:
        # Format the line as timestamp, air temp 1, water temp 1, water temp 2, newline character
        _line: str = f"{_d.timestamp},{_d.air_temp_1},{_d.water_temp_1},{_d.water_temp_2}\n"
        
        # Insert the line into the list
        _lines.append(_line)
    
    # Get the size of the current data file in bytes
    _current_data_file_size_b: int = stat(current_data_file_path)[6]
    
    # Convert the size in bytes to megabytes
    _current_data_file_size_mb: float = _current_data_file_size_b / (1_024 * 1_024)
    
    # Verify that the size of the current data file doesn't exceed the maximum allowed size in MB
    if _current_data_file_size_mb >= _DATA_FILE_MAX_SIZE_MB:
        # Reset the data file write count
        data_file_write_count = 0
        
        # Create a new data file
        current_data_file_path = create_data_file()
    
    # Open the current data file in append mode
    with open(current_data_file_path, 'a', encoding="utf-8") as _f:
        # Write each data line to the file
        for _line in _lines:
            _f.write(_line)
    
    # Increment the data file write count
    data_file_write_count += 1
    
    # Clear the input list, which will cause the data queue (global scope) to be cleared as well
    _data.clear()
    
    # Flash the onboard LED two times
    for _ in range(2):
        onboard_led.on()
        sleep_ms(250)
        onboard_led.off()
        sleep_ms(500)


def update_display(_data_container: MeasurementData) -> None:
    """ Updates the values shown on the OLED display.
    
    params
    -----
    _data_container [MeasurementData, required] Measurement data container holding updated data.
    """
    
    # Fill the display with black pixels
    display.fill(0)
    
    # Get the values from the data container
    _air_temp_1: float = _data_container.air_temp_1
    _water_temp_1: float = _data_container.water_temp_1
    _water_temp_2: float = _data_container.water_temp_2
    
    # Convert the temperatures to Celsius if necessary
    if not _USE_FAHRENHEIT_UNITS:
        _air_temp_1: float = c2f(_air_temp_1)
        _water_temp_1: float = c2f(_water_temp_1)
        _water_temp_2: float = c2f(_water_temp_2)
    
    # Round the temperature values to fit to display
    _air_temp_1 = round(_air_temp_1)
    _water_temp_1 = round(_water_temp_1)
    _water_temp_2 = round(_water_temp_2)
    
    # Set the air text
    display.text("Air Data", 0, 0)
    display.text(f"T1 {_air_temp_1} {_TEMP_UNITS}", 0, 8)
    
    # Set the water text
    display.text("Water Data", 0, 24)
    display.text(f"T1 {_water_temp_1} {_TEMP_UNITS}", 0, 32)
    display.text(f"T2 {_water_temp_2} {_TEMP_UNITS}", 0, 40)
    
    # Set the measurement count text
    display.text(str(measurement_count), 0, 56)

    # Tell the display to show updated data
    display.show()


def error_loop(blink_count: int) -> None:
    """ This function manages the device in case of an error. 
    
    params
    -----
    blink_count [int, required] The number of times the error indicating LED will blink.
    """
    
    while True:
        # Each "blink cycle" is made up of the onboard LED turning on for one (1) second, then 
        #   turning off for one (1) second, blink_count times, followed by a five (5) second 
        #   pause to indicate the termination of the current cycle.

        for _ in range(blink_count):
            onboard_led.on()
            sleep_ms(1_000)
            onboard_led.off()
            sleep_ms(1_000)
        
        sleep_ms(5_000)


def set_system_time() -> None:
    """ Set the system time using the NTP protocol. """
    
    # Check if WiFi is enabled
    if not _ENABLE_WIFI:
        return
    
    # Get the required global variable
    global rtc
    
    # Import the network and ntp libraries
    import network
    import ntptime
    
    # Enable the station
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(False)

    try:
        # Check if the station is already connected
        if not sta_if.isconnected():
            print(f"Attempting to connect to {_WIFI_SSID}")
            
            # Enable the station
            sta_if.active(True)
            
            # Attempt to connect using the SSID and password
            sta_if.connect(_WIFI_SSID, _WIFI_PASS)
            while not sta_if.isconnected():
                print('.', end='')
                sleep_ms(500)
        
        # Output network configuration information
        print(f"\nNetwork Configuration: {sta_if.ifconfig()}")
        
        # Set the system time using ntp
        sec = ntptime.time() + _TIMEZONE_OFFSET_SEC
        (year, month, day, hours, minutes, seconds, weekday, yearday) = localtime(sec)
        rtc.datetime((year, month, day, 0, hours, minutes, seconds, 0))
    except OSError:
        print("Unable to set system time using WiFi. System resetting.")
        soft_reset()
    
    # De-activate the station as it is no longer needed
    sta_if.active(False)


def format_system_time(_system_time: tuple) -> str:
    """ Format a given system time tuple into a string timestamp. 
    
    params
    -----
    _system_time [tuple, required] A tuple of the following format:
        (year, month, mday, hour, minute, second, weekday, yearday)
    
    returns
    -----
    Timestamp formatted as a string.
    """
    
    year: int = _system_time[0]
    month: int = _system_time[1]
    day: int = _system_time[2]
    time: str = f"{_system_time[4]}:{_system_time[5]}:{_system_time[6]}"
    
    return f"{month}/{day}/{year} {time}"


# -------------------------------------------------------------------------------------------------
# Interrupt Handlers ------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

# The following verbiage comes from the MicroPython docs on ISRs and their rules:
#
#       If an error occurs in and ISR, MicroPython is unable to produce an error report unless a 
#       special buffer is created for the purpose. Debugging is simplified if the following code is
#       included in any program using interrupts.
#
#   Here is where we allocate that buffer.
alloc_emergency_exception_buf(100)


def dump_to_storage_isr(_pin: Pin) -> None:
    """ ISR to handle manual data dumping. """
    
    # Get the required global variable
    global manual_data_dump_triggered
    
    # Set the manual data dump flag HIGH
    manual_data_dump_triggered = True


# Attach the interrupt handler to the data write button
write_button.irq(trigger=Pin.IRQ_RISING, handler=dump_to_storage_isr)


# Tell the device to wake up when interrupted by the data dump button
wake_on_ext0(pin=write_button, level=WAKEUP_ANY_HIGH)


# -------------------------------------------------------------------------------------------------
# Main --------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

# Set the system time using NTP
set_system_time()
print(f"System time set to: {rtc.datetime()}")

# 5 second delay before main loop begins. This could be removed if not desired
sleep_ms(5_000)

# Scan the ds sensor wire to detect any addresses present
ds_sensor_array = ds_sensors.scan()

# We are expecting the line to have two addresses, so verify both are found
if len(ds_sensor_array) != 2:
    # One or both of the sensors can't be detected. Enter the error loop, blinking once / cycle
    error_loop(1)

# Take a test measurement from each of the peripherals to verify proper functionality
_data_container: MeasurementData = take_measurement(increment_counter=False)

# Verify that each value is not the invalid measurement value
if not _data_container.is_valid():
    # Data are invalid. Enter the error loop, blinking twice / cycle
    error_loop(2)

# Create an instance of MicroPython Unix-like Virtual File System (vfs)
vfs = VfsFat(sd_controller)

# Mount the SD card to the project root folder
mount(sd_controller, f"{_ROOT_DIR_PATH}")

# Change directory into the measurements directory
try:
    chdir(_MEASUREMENTS_DIR_PATH)
except OSError as err:
    # Couldn't change to the directory requested. Output message to console and enter error loop.
    print(f"Could not navigate into directory: {_MEASUREMENTS_DIR_PATH}\n\n{err}")
    error_loop(3)

# Create a new data file, if one doesn't exist already.
current_data_file_path = create_data_file(check_last_file=True)

# Loop forever, or until the device is no longer powered.
while True:
    # Take a measurement, updating & reading sensor values into the data container
    _data_container = take_measurement()
    
    # Update the display
    update_display(_data_container)
    
    # Insert the data into the data array
    data_queue.append(_data_container)
    
    # Flash the onboard LED one time
    onboard_led.on()
    sleep_ms(250)
    onboard_led.off()
    
    # Check if the queue has reaced max length
    if len(data_queue) == _DATA_QUEUE_MAX_LEN:
        # Data queue is full, write data to persistent storage
        dump_to_storage(data_queue)
    
    # Put device to sleep until the next reading
    lightsleep(_MEASURE_DELAY_MS)
    
    # Check if a manual data dump was triggered
    if manual_data_dump_triggered:
        # Dump to storage
        dump_to_storage(data_queue)
        
        # Reset the manual dump flag
        manual_data_dump_triggered = False
