# VXLAN VNI Validation with pyATS

This Python script uses pyATS and Genie to connect to network devices, gather VXLAN VNI and BGP EVPN data, and validate that specified VNIs and their associated IP addresses are present in the BGP EVPN output. It’s designed for network engineers testing VXLAN configurations in a lab or production environment.

## Features
- Connects to devices defined in a pyATS testbed file.
- Loads VNI and IP configurations from a JSON file.
- Validates VNIs and IPs against BGP EVPN data.
- Provides detailed logging and a summary of passed/failed checks.
- Configurable timeouts and validation parameters via a `CONFIG` dictionary.

## Prerequisites
- **Python**: 3.6 or higher
- **pyATS**: Install via pip:
```bash
pip install pyats[full]
```

* Genie: Included with pyATS; no separate installation required.
* Network Devices: Accessible devices with BGP EVPN and VXLAN configured.
* Testbed File: A pyATS-compatible YAML file defining device connections.

## Setup
1. Clone the Repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install Dependencies:
```bash
pip install -r requirements.txt
```

3. Prepare Testbed File: Create a `testbed.yaml` file with your device details. Example:
```yaml
devices:
  device1:
    type: router
    os: iosxe
    connections:
      cli:
        protocol: ssh
        ip: 192.168.1.1
        username: admin
        password: cisco
```

4. Set Environment Variable: Specify the path to your VNI/IP JSON file:
```bash
export VNIS_IPS=/path/to/vnis_ips.json
```

## Usage
Run the script with your testbed file:
```python
python vxlan_vni_test.py --testbed testbed.yaml
```

## JSON File Format (vnis_ips.json)
The script expects a JSON file with the following structure:
```json
{
    "l2": {
        "device1": {
            "vni1": ["10.0.0.1", "10.0.0.2"]
        }
    },
    "l3": {
        "device2": {
            "vni2": ["192.168.1.1"]
        }
    }
}
```

* `l2/l3`: Layer keys (must match `CONFIG['VALID_LAYERS']`).
* Device Names: Must match names in the testbed file.
* VNIs: Keys mapping to lists of IP addresses (strings).


## Configuration
The `CONFIG` dictionary at the top of the script defines:

`DEVICE_TIMEOUT`: Connection timeout in seconds (default: 30).
`VALID_LAYERS`: Supported layers (`['l2', 'l3']`).
`BGP_REQUIRED_KEYS`: Expected BGP EVPN structure path.
