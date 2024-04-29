
![](https://github.com/geddy11/sysloss/raw/main/docs/sysloss.svg)

<p align="center">
<a href="https://github.com/geddy11/sysloss/actions"><img alt="Actions Status" src="https://github.com/geddy11/sysloss/actions/workflows/ci-cd.yml/badge.svg"></a>
<a href="https://codecov.io/github/geddy11/sysloss"><img src="https://codecov.io/github/geddy11/sysloss/graph/badge.svg?token=9L1ZMN0UET"/></a>
<a><img alt="PyPI" src="https://img.shields.io/pypi/v/sysloss"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://www.conventionalcommits.org"><img alt="Conv. commits" src="https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white"></a>
<a href="https://doi.org/10.5281/zenodo.11086061"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.11086061.svg" alt="DOI"></a>
</p>

# sysLoss
sysLoss is a tool for analyzing system power and losses. From the smallest IoT sensor to large industrial installations. The tool is efficient and easy to use, the analysis result provides a detailed report on voltages, currents, power and efficiency for every component defined in the system. Output format is Pandas DataFrame: Create charts, plots and export to Excel and other formats. 

## Installation
```bash
$ pip install sysloss
```

## Usage
```python
from sysloss.components import *
from sysloss.system import System

bts = System("Bluetooth sensor", Source("CR2032", vo=3.0, rs=10))
bts.add_comp("CR2032", comp=Converter("Buck 1.8V", vo=1.8, eff=0.87))
bts.add_comp("Buck 1.8V", comp=PLoad("MCU", pwr=13e-3))
bts.add_comp("CR2032", comp=Converter("Boost 5V", vo=5.0, eff=0.82))
bts.add_comp("Boost 5V", comp=RLoss("RC filter", rs=6.8))
bts.add_comp("RC filter", comp=ILoad("Sensor", ii=6e-3))
bts.tree()
```
```
Bluetooth sensor
└── CR2032
    ├── Boost 5V
    │   └── RC filter
    │       └── Sensor
    └── Buck 1.8V
        └── MCU
```
```python
bts.solve()
```
![result](https://github.com/geddy11/sysloss/raw/main/docs/bts.png)

## Documentation
The [documentation](https://sysloss.readthedocs.io/en/latest/Getting%20started.html) includes tutorials in the form of Jupyter notebooks, located in docs/nb.

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`sysloss` was created by Geir Drange. It is licensed under the terms of the MIT license.
