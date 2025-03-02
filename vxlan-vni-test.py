#!/usr/bin/env python
from ats.log.utils import banner
from genie.conf import Genie
from pyats import aetest
import logging
import os
import json
import pprint

# Logger setup
log = logging.getLogger(__name__)

# Configuration constants
CONFIG = {
    'DEVICE_TIMEOUT': 30,
    'VALID_LAYERS': ['l2', 'l3'],
    'BGP_REQUIRED_KEYS': ['instance', 'default', 'vrf', 'default', 
                         'address_family', 'l2vpn evpn', 'rd']
}

################################################################
###                   COMMON SETUP SECTION                   ###
################################################################

class DeviceSetup(aetest.CommonSetup):
    """Common Setup section for device connection and data gathering"""

    @aetest.subsection
    def connect(self, testbed, steps):
        """Connect to each device in the testbed"""
        try:
            genie_testbed = Genie.init(testbed)
            devices = []
            
            for device in genie_testbed.devices.values():
                with steps.start(f"Connecting to device '{device.name}'"):
                    log.info(banner(f"Connecting to device '{device.name}'"))
                    try:
                        device.connect(timeout=CONFIG['DEVICE_TIMEOUT'])
                        devices.append(device)
                        log.info(f"Successfully connected to {device.name}")
                    except Exception as e:
                        log.error(f"Failed to connect to '{device.name}': {str(e)}")
                        self.failed(f"Failed to establish connection to '{device.name}'")
            
            self.devices = devices
            log.info(f"Successfully connected to {len(devices)} devices")
            
        except Exception as e:
            log.error(f"Failed to initialize testbed: {str(e)}")
            self.failed("Testbed initialization failed")

    def _validate_vnis_structure(self, data):
        """Validate VNIS_IPS data structure"""
        if not isinstance(data, dict):
            raise ValueError("Invalid VNIS_IPS structure: expected dict")
            
        if not any(layer in data for layer in CONFIG['VALID_LAYERS']):
            raise ValueError("Invalid VNIS_IPS structure: missing 'l2' or 'l3' keys")
            
        for layer in CONFIG['VALID_LAYERS']:
            if layer in data:
                if not isinstance(data[layer], dict):
                    raise ValueError(f"Invalid {layer} structure: expected dict")
                    
                for device, vnis in data[layer].items():
                    if not isinstance(vnis, dict):
                        raise ValueError(f"Invalid VNI structure for {device} in {layer}")
                    for vni, ips in vnis.items():
                        if not isinstance(ips, list):
                            raise ValueError(f"Invalid IPs for VNI {vni} on {device} in {layer}")
                        if not all(isinstance(ip, str) for ip in ips):
                            raise ValueError(f"Invalid IP format in VNI {vni} on {device}")

    @aetest.subsection
    def gather_vxlan_vnis(self, steps):
        """Gather VXLAN VNIs and BGP EVPN data"""
        try:
            # Load and validate VNIS_IPS file
            file_name = os.environ.get('VNIS_IPS')
            if not file_name:
                raise ValueError("VNIS_IPS environment variable not set")
            if not os.path.exists(file_name):
                raise FileNotFoundError(f"File not found: {file_name}")

            with open(file_name, 'r') as f:
                data = json.load(f)
            
            self._validate_vnis_structure(data)
            
            # Gather BGP EVPN data
            bgp_evpns = {}
            for device in self.devices:
                with steps.start(f"Gathering BGP EVPN data on '{device.name}'") as device_step:
                    try:
                        bgp_info = device.parse("show bgp l2vpn evpn")
                        bgp_evpns[device.name] = bgp_info
                        device_step.passed(f"Successfully gathered BGP EVPN data")
                    except Exception as e:
                        log.error(f"Failed to parse BGP EVPN: {str(e)}")
                        device_step.failed("Failed to gather BGP EVPN data")

            # Update parameters and log summary
            self.parent.parameters.update(bgp_evpns=bgp_evpns, vnis_ips=data)
            self._log_data_summary(bgp_evpns)

        except Exception as e:
            log.error(f"Error in gather_vxlan_vnis: {str(e)}")
            self.failed(str(e))

    def _log_data_summary(self, bgp_evpns):
        """Log summary of collected data"""
        log.info("Collected BGP EVPN Data Summary:")
        log.info(f"Total devices processed: {len(bgp_evpns)}")
        for device in bgp_evpns:
            rd_count = len(bgp_evpns[device].get('instance', {}).get('default', {})
                         .get('vrf', {}).get('default', {}).get('address_family', {})
                         .get('l2vpn evpn', {}).get('rd', {}))
            log.info(f"Device {device}: {rd_count} RD entries found")
        log.debug("Detailed BGP EVPN Data:\n" + pprint.pformat(bgp_evpns, indent=2))

################################################################
###                    TESTCASES SECTION                     ###
################################################################

class WorkstationsFind(aetest.Testcase):
    """Testcase to validate VNIs and IPs"""

    def _validate_bgp_structure(self, bgp_evpn):
        """Validate BGP EVPN data structure with detailed path"""
        current_dict = bgp_evpn
        path = ""
        for key in CONFIG['BGP_REQUIRED_KEYS']:
            path += f"/{key}"
            if not isinstance(current_dict, dict) or key not in current_dict:
                raise KeyError(f"Missing or invalid key in path {path}")
            current_dict = current_dict[key]
        return current_dict

    @aetest.test
    def check_vnis(self, steps):
        """Check VNIs and associated IPs in BGP EVPN data"""
        vnis_ips = self.parent.parameters.get('vnis_ips', {})
        bgp_evpns = self.parent.parameters.get('bgp_evpns', {})

        if not vnis_ips or not bgp_evpns:
            self.failed("Required parameters 'vnis_ips' or 'bgp_evpns' not found")

        total_checks = 0
        passed_checks = 0

        for layer in CONFIG['VALID_LAYERS']:
            if layer not in vnis_ips:
                log.info(f"No {layer} configuration found, skipping")
                continue

            for device, bgp_evpn in bgp_evpns.items():
                if device not in vnis_ips[layer]:
                    log.debug(f"No {layer} VNIs configured for {device}, skipping")
                    continue

                for vni, ips in vnis_ips[layer][device].items():
                    with steps.start(
                        f"Device {device}: Analyzing VNI {vni} ({layer})",
                        continue_=True
                    ) as vni_step:
                        total_checks += len(ips)
                        passed_ips = self._check_vni_and_ips(device, vni, ips, bgp_evpn, vni_step)
                        passed_checks += passed_ips

        # Summary
        log.info(f"Summary: {passed_checks}/{total_checks} IP checks passed")
        if passed_checks == total_checks:
            self.passed("All IP checks passed")
        else:
            self.failed(f"{total_checks - passed_checks}/{total_checks} IP checks failed")

    def _check_vni_and_ips(self, device, vni, ips, bgp_evpn, vni_step):
        """Helper method to check VNI and IPs, returns count of passed IPs"""
        if not isinstance(ips, list):
            vni_step.failed(f"Invalid 'ips' data for VNI {vni} on {device}: expected a list")
            return 0

        try:
            evpn_data = self._validate_bgp_structure(bgp_evpn)
        except KeyError as e:
            vni_step.failed(f"Invalid BGP EVPN structure on {device}: {str(e)}")
            return 0

        vni_found = False
        ip_status = {ip: False for ip in ips}
        ip_prefixes = {}

        for edge_info in evpn_data.values():
            if edge_info.get('rd_vrf') == vni:
                vni_found = True
                for ip in ips:
                    for prefix in edge_info.get('prefix', {}):
                        if ip in prefix:
                            ip_status[ip] = True
                            ip_prefixes[ip] = prefix
                            break
                break  # Exit once VNI is found

        if not vni_found:
            vni_step.failed(f"VNI {vni} not found on {device}")
            return 0

        passed_count = 0
        for ip, found in ip_status.items():
            if found:
                log.info(f"IP {ip} found in VNI {vni} on {device} (prefix: {ip_prefixes[ip]})")
                vni_step.passed(f"IP {ip} found in prefix {ip_prefixes[ip]}")
                passed_count += 1
            else:
                log.warning(f"IP {ip} not found in VNI {vni} on {device}")
                vni_step.failed(f"IP {ip} not found in any prefix")

        return passed_count

if __name__ == '__main__':
    aetest.main()
    