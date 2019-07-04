import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="measureSequences",
    version="0.1.0",
    author="Benjamin Klebel",
    author_email="klebel.b@hotmail.com",
    description="parse and run QD PPMS sequence files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bklebel/measureSequences",
    download_url='https://github.com/bklebel/measureSequences/archive/v0.1.0.tar.gz',
    # packages=setuptools.find_packages(),
    packages=['measureSequences'],
    install_requires=['numpy', 'PyQt5'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3.0",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research  ",
        "Topic :: Scientific/Engineering  ",
        "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator  ",
        "Topic :: Scientific/Engineering :: Physics  ",
    ],
)
