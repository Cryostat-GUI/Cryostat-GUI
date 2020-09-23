[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ecbee20c7d914f0e8ae2156ec0d0bac5)](https://www.codacy.com/app/bklebel/Cryostat-GUI?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=bklebel/Cryostat-GUI&amp;utm_campaign=Badge_Grade)
[![DeepSource](https://deepsource.io/gh/Cryostat-GUI/Cryostat-GUI.svg/?label=active+issues&show_trend=true)](https://deepsource.io/gh/Cryostat-GUI/Cryostat-GUI/?ref=repository-badge)
[![DeepSource](https://deepsource.io/gh/Cryostat-GUI/Cryostat-GUI.svg/?label=resolved+issues&show_trend=true)](https://deepsource.io/gh/Cryostat-GUI/Cryostat-GUI/?ref=repository-badge)

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

As this Cryostat will now be used for plain electrical resistivity measurements, this measuring technique is implemented first. In the future, other techniques will possibly be included (e.g. magneto-resistivity, thermal conductivity, specific heat, ...)

Currently it is almost as 'quick and dirty' as possible, while upholding at least some decency.  


#### Sequence Editor 
There is a Sequence editor, which was moved to https://github.com/bklebel/measureSequences/. 
It can read PPMS (resistivity option) sequence files - and abstract class to run those sequences is being built as well. 


## Contributing
Additional Drivers for instruments, as well as control features and GUI enhancements are welcome.
We refrained from using a few existing python packages for instrument control at the start, and wrote custom instrument drivers for some instruments, however including more instruments by virtue of different python packages will occur. 
