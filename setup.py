import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="CryostatGUI",
    version="0.1.1",
    author="Benjamin Klebel",
    author_email="klebel.b@hotmail.com",
    description="Drivers and GUI for control of a cryostat",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Cryostat-GUI/Cryostat-GUI",
    # download_url='https://github.com/bklebel/measureSequences/archive/v0.1.0.tar.gz',
    # packages=setuptools.find_packages(),
    packages=["CryostatGUI"],
    install_requires=[
        "numpy",
        "PyQt5",
        "pyvisa",
        "matplotlib",
        "pymeasure",
        "measureSequences",
    ],
    dependency_links=[
        "https://github.com/bklebel/measureSequences/archive/v0.1.7.tar.gz"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research  ",
        "Topic :: Scientific/Engineering  ",
        "Topic :: Scientific/Engineering :: Physics  ",
    ],
)
