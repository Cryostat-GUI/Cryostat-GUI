import visa
from pyvisa.errors import VisaIOError

rm = [visa.ResourceManager(), visa.ResourceManager(r'C:\Windows\System32\agvisa32.dll')]
res = [rm[0].list_resources(), rm[1].list_resources()]

devices = []

for ct, manager in enumerate(res):
    for resource in manager:
        try:
            devices.append(rm.open_resource(resource))
            print(devices[-1].query('*IDN?'), resource)
        except VisaIOError as e1:
            try:
                devices[-1].read_termination = '\r'
                print(resource, devices[-1].query('V'))
            except VisaIOError as e2:
                    print(ct, resource, e2)
            print(ct, resource, e1)

