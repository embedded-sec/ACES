# README #

The STM32CUBEF4 library is needed with these source files to compile. Some dependencies need to be addressed: 

- In the makefile, mbed_tls command includes paths that need to be changed since they are not relative 
- Might have to create "mbed_tls" folder in Debug

### Summary ###

The first application for testing security on RESIST. The application asks the user for a pin in the UART, after passing the security step an LED turns on.