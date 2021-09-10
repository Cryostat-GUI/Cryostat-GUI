"""
    Author(s):
        bklebel (Benjamin Klebel)
"""
import visa
from pyvisa.errors import VisaIOError

import re


class jumpingexception(Exception):
    pass


faulty_GPIB = re.compile(r"::[0-9]{1,2}::[0-9]{1,2}::")

rm = [visa.ResourceManager(), visa.ResourceManager(r"C:\Windows\System32\agvisa32.dll")]
res = [
    rm[1].list_resources(),
    # rm[1].list_resources(),
]
for r in res:
    print("----------------------------------------")
    for q in r:
        print(q)
devices = []
print("----------------------------------------")
for ct, manager in enumerate(res):
    for resource in manager:
        # try:
        # devices.append()
        print(resource)
        if re.search(faulty_GPIB, resource):
            continue
        dev = rm[0].open_resource(resource)
        try:
            for q in ("*IDN?", "V"):
                for r_term, r_term_raw in zip(
                    ("\r", "\n", "\r\n", "\n\r"), (r"\r", r"\n", r"\r\n", r"\n\r")
                ):
                    try:
                        dev.read_termination = r_term
                        print(
                            "--", ct, resource, "--", r_term_raw, q, "--", dev.query(q)
                        )
                        raise jumpingexception
                    except VisaIOError as e0:
                        print("||", ct, resource, "--", r_term_raw, q, "--", e0)
        except jumpingexception:
            pass
        dev.close()
        # except VisaIOError as e1:
        #     try:
        #         devices[-1].read_termination = "\r"
        #         print(resource, devices[-1].query("V"))
        #     except VisaIOError as e2:
        #         print(ct, resource, e2)
        #     print(ct, resource, e1)
