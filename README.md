# hud-installer
A cross-platform python script for installing TF2 huds

1. install the requirements (currently, just a VDF parser)
```sh
# optional: use a virtual environment
python3 -m venv .venv
source .venv/bin/activate
# or on windows
py -3 -m venv .venv
.\.venv\scripts\activate

# install requirements
pip install -r requirements.txt
```

2. run the installer script with a configuration for the hud you want
   (see budhud.cfg for an example and format documentation)
```sh
# run the installer
python3 main.py install budhud
```
