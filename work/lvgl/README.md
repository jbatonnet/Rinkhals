Source: https://github.com/kdschlosser/lv_cpython/issues/14#issuecomment-2561555380

- Create a python virtual environment: python3 -m venv .venv
```
git clone https://github.com/kdschlosser/lv_cpython
git checkout 8d4c1ef262d0eb3c064f3eed750b9dc0b21589db
python -m pip install .
```

. This is required because the most recent commit added git submodules which break the build.
- Install build dependencies: sudo apt install make libudev-dev g++ libsdl2-dev
- cd into .venv and activate
- Updat evnironment packages: python -m pip install --upgrade pip setuptools wheel build
- Install python dev: sudo apt install python3-dev
- Build lvgl: python -m pip install .
- Fix examples: Some examples require "User-Data" parameter in some functions. Just add the python None type.
