# RedSky MyE911 Checkup
Web GUI tool that takes CSV reports from RedSky and verifies MyE911 Users have a device mapped. If a user has no device mapped it will try to match devices to users and create a MyE911 Device Mapping CSV import file.

## Table of contents
- [Installation](#installation)
- [Usage](#usage)
## Installation
A) Either download the executable from the [latest release](https://github.com/pdjohntony/redsky-mye911-checkup/releases) section.

OR

B) Run the tool with Python.
1. Clone the repository
```
git clone https://github.com/pdjohntony/redsky-mye911-checkup
```

2. Install the python requirements
```python
pip install -r requirements.txt
```

3. Start with
```python
python app_flask.py
```

## Usage
1. Run the executable, click allow if prompted by firewall
2. A browser window should open automatically, if not go to http://localhost:5001

![Alt text](screenshots/gui_pre_upload.png "Beginning")
![Alt text](screenshots/gui_post_upload.png "End")