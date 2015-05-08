# Hydro Conductor

This repository hosts a set of Python scripts and modules written to couple a hydrologic model with a regional glacier model. It is written for the University of Washington's [Variable Infiltration Capacity](https://github.com/UW-Hydro/VIC) hydrologic model and [UBC's](http://www.eos.ubc.ca/research/glaciology/index.html) Regional Glacier Model.

The "conductor" executes each model as a subprocess while translating inputs and outputs from each model to match the scale and requirements of the other.

## How to set up a dev environment

* Install Python 3
* Set up a virtual environment

```bash
$ virtualenv -p python3 env
```

* Activate the environment

```bash
$ source env/bin/activate
```

* Install the requirements

```bash
$ pip install -r requirements.txt
```

## How to run the tests

We haven't yet written any tests, but once we do, do this:

* Install [`pytest`](http://pytest.org/latest/)

```bash
$ pip install pytest
```

* Run `pytest`

```bash
$ py.test tests/
```
