# Change Log

This file was created because the changelog notes in the *boot.py* file were taking up too much room and making the code harder to read. The layout of this file is heavily inspired by the CHANGELOG.md file found [here](https://github.com/othneildrew/Best-README-Template/blob/main/CHANGELOG.md).

All notable changes to this project will be documented within this file.

<!-- New Version! -->
## v0.1.0 [10-FEB-2025]

This is the initial version of the system.

### Added or Changed

- Module Created

<!-- New Version! -->
## v0.1.1 [14-FEB-2025]

This version incorporated some quality of life improvements and fixes small bugs.

### Added or Changed

- Adds a 5 second delay before the main loop begins to help when testing the program. This
    keeps the device from putting itself to sleep, preventing myself from triggering the
    KeyboardInterrupt exception to run commands using the microcontrollers interpreter. THIS
    MAY BE REMOVED IF THIS BEHAVIOR IS NOT DESIRED.
- Adds error loop function consolidates error code.
- Adds push button peripheral that dumps the temporary data to storage when pressed.
- Adds a check for an existing data file when the system starts, removing the annoyance of a 
    a new data file being created each time the program begins, leading to numerous junk files.

### Fixed

- No longer attempts to dump data to storage if no data are passed.

<!-- New Version! -->
## v0.2.0 [17-FEB-2025]

This version added wireless functions and removed unnecessary clutter.

### Added or Changed

- Adds ability to connect to WiFi with SSID/Password.
- Adds function that sets system time using NTP.
- Adds timestamps to measurement data containers.

### Removed

- Removes unnecessary comments.
- Removes unnecessary imports.

### Fixed

- Fixes issue where f2c function was not producing results.

<!-- New Version! -->
## v0.3.0 [18-FEB-2025]

This version

### Added or Changed

- Renames file from "main.py" to "boot.py".
- Separates user settings (those that users may want to edit) from general settings (those
    that in general, should be left alone).
- Adds connection timeout for when device is attempting to connect to WiFi.
- Adds more comprehensive and easier to read print statements.
- Adds a call for garbage collection when...:
    - Program starts
    - Data is dumped to persistent storage
- SPI bus used by the SD card module now uses hardware SPI instead of software SPI.
- Adds check for wake reason when manual data dump button is pressed.
- Simplifies the **Description** header in the *boot.py* file.

### Removed

- Removes **Updated on** header from the *boot.py* file as it is not necessary.
- Removes unnecessary interrupt service routine tied to manual data dump button as it is not
    needed when the device is set to wake on EXT0.
- Removes count_data_files function and moved the single instruction directly into the 
    create_data_file function.

### Fixed

- SPI bus used by the SD card module now uses the VSPI interface as HSPI_MISO (GPIO pin 12)
    was causing issues on boot.
- The lightsleep function call in the main loop now accounts for the duration of time the
    onboard LED is on.

<!-- New Version! -->
## v0.3.1 [19-FEB-2025]

### Added or Changed

- Combined related global variables into a single variable. E.g., the combination of the measure delay in seconds and milliseconds

    What used to be:
        
        > _MEASURE_DELAY_SEC = const(60)
        > _MEASURE_DELAY_MS = const(_MEASURE_DELAY_SEC * 1_000)

    What is now:
    
        > _MEASURE_DELAY_MS(60 * 1_000)
    
    This was done to reduce the total memory used by global variables, and the amount of time the CPU takes to find them.

### Removed

- Removed the unused f2c function.
- Removed duplicate global variable names.
