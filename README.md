<!-- HEADER -->
# Fish Tank Monitor

A system that periodically measures environment variables in and surrounding my fish tank.


<!-- ABOUT THE PROJECT -->
## About the Project

A combination of hardware and software, the system uses a combination of the ESP32 microcontroller and various sensors to monitor the fish tanks environment. It displays measured variables using a small OLED display, and will write the measured data to persistent storage at a user defined interval. The user may control how often measurements are taken, how often data is written to storage, and what units the data are shown on the display, all by modifying a few lines of the source code.


### Programmed With

This project was programmed in [MicroPython](https://docs.micropython.org/en/latest/), a language largely compatible with [Python 3](https://www.python.org/) that is optimized to run on a microcontroller.


<!-- GETTING STARTED -->
## Getting Started

The system can be built using off the shelf components, and the software can be uploaded using a free IDE. The behavior can also be easily modified by changing just a few lines of code in the main.py source file.

Once the hardware is put together, the software just needs to be uploaded to the microcontroller through Thonny and the system will then be capable of running.


### Hardware

While there are multiple ways to put the system together, here is one hardware list that was found to work while testing:

| Name | Quantity | Description |
|------|----------|-------------|
| Wroom ESP32 | 1 | Microcontroller used as the "brain" of the system. |
| ESP32 Breakout board | 1 | Additional GPIO connection points for data and power. Not required, but nice to have. |
| 0.96" SSD1306 OLED Display | 1 | Display used to output measurement data. |
| DHT11 Air Temperature & Humidity Sensor | 1 | Sensor used to measure the temperature of the air. |
| DS18B20 Waterproof Temperature Sensor | 2 | Sensor used to measure the temperature of the water. |
| Micro SD Card Module | 1 | Module used to hold the micro SD card and provide an interface with which to send data to/from it. |
| Micro SD Card | 1 | Used to store persistent data sent from the microcontroller. |
| Push button | 1 | Used to trigger a manual data dump. |
| 1k Resistor | 1 | Ties push manual data dump button to 5v when not pressed. |
| 4.7k Resistor | 2 | Connects the data rails of both the DHT11 and DS18B20 sensors to 5v. |
| Jumper wires | a  lot | Connects the different peripherals to power, GPIO pins, etc. |
| Breadboard | 1 | Useful for testing the hardware connections when setting up the system. Not required, but helpful. |

Additional hardware can be used to debounce the push button, like an NE555 IC, but software debouncing can also be implemented relatively easily.


### Software

The [Thonny](https://thonny.org/) IDE was used to program the system and upload the code to the ESP32.


### Packages

There are a handful of packages that need to be installed to the microcontroller to avoid having to write libraries for peripheral devices from scratch. This can be done easily within Thonny by clicking **Tools > Manage Packages** with the microcontroller plugged in and connected to. With the package manager opened, search for the following packages and install them to the device.

| Name | Description |
|------|-------------|
| dht | Wrapper for the DHT sensor family. |
| ds18x20 | Wrapper for the DS18X20 sensor family. |
| onewire | Interfacing with the ds18x20 sensors. |
| sdcard| Wrapper for the SD card module. |
| ssd1306 | Wrapper for the SSD1306 OLED dispaly module. |


<!-- USAGE EXAMPLE -->
## Usage Example


### System Settings

After the system has been set up, there are a handful of settings that the user may want to change. These include:

| Variable Name | Variable Description | Data Type | Default Value |
|---------------|----------------------|-----------|---------------|
| _MEASURE_DELAY_SEC | Time in seconds between measurements. | int | 60 |
| _USE_FAHRENHEIT_UNITS | Displays temperature in degrees F when True, otherwise, degrees C. | bool | True |
| _DATA_QUEUE_MAX_LEN | Number of measurements to hold in temp. storage. When this value is reached, the data will be dumped to persistent storage. | int | 30 |
| _BASE_CPU_FREQ_HZ | Base frequency of the CPU used on the microcontroller being used. This value is not recommended to be changed unless you know what the working values are for your board. | int | 160 MHz for this board |


### Starting the System

There are two ways to start the system:

- Press the play button in Thonny with the file opened. This will save the file to the device and start it.
- Put the code into a file named *boot.py* and it will run any time the board is powered.


<!-- MARKDOWN LINKS & IMAGES -->
[software-debounced-fritzing-diagram]: images/SoftwareDebouncedFritzingDiagram.png
[hardware-debounced-fritzing-diagram]: images/HardwareDebouncedFritzingDiagram.png
