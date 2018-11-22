# Cryostat-GUI
Software to enforce control over an Oxford Cryostat, as well as measurment devices, at TU Wien

## Devices to be controlled: 
- [x] Oxford ITC 503
- [x] Oxford ILM 211
- [x] Oxford IPS 120-10
- [x] Lakeshore 350
- [x] Keithley 2182 A
- [x] Keithley 6221
- [ ] Keithley DMM 7510 7 1/2
- [ ] Keithley MM 2700

## Status
Currently in development. 
Low-level functions are fully implemented for 
- Oxford ITC 503
- Oxford ILM 211
- Oxford IPS 120-10
- LakeShore 350

Low-level functions for the Keithley instruments are not being implemented systematically, however most commands for usual control operations are/will be integrated. 
Currently all the GPIB and RS232 addresses are hardcoded in the `mainWindow.py`. A dedicated 'Settings' window, which uses the PyQt5 (Qt) functionality to store values across application closing events is planned, where device hardware addresses can be set. 

As this Cryostat will be used for plain electrical resistivity measurements, this measuring technique is implemented first. In the future, other techniques will possibly included (e.g. magneto-resistivity, thermal conductivity, specific heat, ...)
The way of handling of measuring sequences is based on the implementation of a Quantum Design PPMS, with the possibility to scan across a certain parameter, and perform arbitrary measurements at each point of the scan, contrary to a very basic sequence file format, where every line contains a single instruction (of setting a paramter, or conducting a certain measurement). 
The whole Sequence editor and the sequence files being used are designed to work with a Quantum Design PPMS, using the same commands, for sequence-file compatibility across the two systems. 

## Contributing
Additional Drivers for instruments, as well as control features and GUI enhancements are welcome.
We refrained from using the InstrumentKit python package from the start, however a switch from the custom instrument classes to this framework could be envisioned.
