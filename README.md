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

## Sample Console Output
Below is what you might see in the terminal when running the script (`python vxlan_vni_test.py`):

```bash
INFO:__main__: 
================================================================================
                    Connecting to device 'device1'                    
================================================================================
INFO:__main__:Successfully connected to device1
INFO:__main__: 
================================================================================
                    Connecting to device 'device2'                    
================================================================================
INFO:__main__:Successfully connected to device2
INFO:__main__:Successfully connected to 2 devices
INFO:__main__: 
================================================================================
                    Gathering BGP EVPN data on 'device1'                    
================================================================================
INFO:__main__:Successfully gathered BGP EVPN data
INFO:__main__: 
================================================================================
                    Gathering BGP EVPN data on 'device2'                    
================================================================================
INFO:__main__:Successfully gathered BGP EVPN data
INFO:__main__:Collected BGP EVPN Data Summary:
INFO:__main__:Total devices processed: 2
INFO:__main__:Device device1: 1 RD entries found
INFO:__main__:Device device2: 2 RD entries found
DEBUG:__main__:Detailed BGP EVPN Data:
  {'device1': {'instance': {'default': {'vrf': {'default': {'address_family': {'l2vpn evpn': {'rd': {'100': {'rd_vrf': '100', 'prefix': {'10.0.0.0/24': {}}}}}}}}}},
   'device2': {'instance': {'default': {'vrf': {'default': {'address_family': {'l2vpn evpn': {'rd': {'300': {'rd_vrf': '300', 'prefix': {}}, '400': {'rd_vrf': '400', 'prefix': {}}}}}}}}}}
INFO:__main__: 
================================================================================
                    Device device1: Analyzing VNI 100 (l2)                    
================================================================================
INFO:__main__:IP 10.0.0.1 found in VNI 100 on device1 (prefix: 10.0.0.0/24)
WARNING:__main__:IP 10.0.0.2 not found in VNI 100 on device1
INFO:__main__: 
================================================================================
                    Device device2: Analyzing VNI 200 (l2)                    
================================================================================
INFO:__main__:VNI 200 not found on device2
INFO:__main__:Summary: 1/3 IP checks passed
```

## Notes on Output
1. Logging Levels:
    * INFO: Connection success, data summary, passed checks.
    * WARNING: Failed IP checks.
    * DEBUG: Detailed BGP data (only if logging level is set to DEBUG).
    * ERROR: Would appear if connections or parsing failed (not shown here).

2. pyATS Results:
    * The self.failed call in check_vnis marks the test as failed since not all IPs passed.
    * Individual steps use vni_step.passed or vni_step.failed for granular reporting.

3. Variations:
    * If all IPs matched, the summary would be "3/3 IP checks passed," and the test would end with self.passed.
    * If a device connection failed, you’d see an ERROR log and a FAILED setup result, halting execution.
