#!/usr/bin/env python3
import json
import sys
import requests
from urllib.parse import urlparse
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FedRAMPDataProcessor:
    def __init__(self, base_url: str = "https://fedramp.github.io/Marketplace-poc/fedramp-packages.json"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'FedRAMP-Data-Processor/1.0'})
        self.session.verify = False
        requests.packages.urllib3.disable_warnings()
    
    def fetch_json(self, url: str):
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def get_field_mapping(self):
        return {
            "frid": "id", 
            "csp_name": "csp", 
            "cso_name": "cso",
            "security_email": "public_security_email", 
            "path": "auth_path",
            "business_function": "business_functions"
        }
    
    def flatten_endpoint_data(self, data):
        flattened = data.copy()
        
        if "assessor" in data and isinstance(data["assessor"], dict):
            flattened["3pao_name"] = data["assessor"].get("name", "")
        
        if "service_model" in flattened and isinstance(flattened["service_model"], str):
            flattened["service_model"] = [flattened["service_model"]]
        
        if "authorized_services" in data:
            flattened["new_auth_services"] = data["authorized_services"]
        
        return flattened
    
    def update_package(self, package, endpoint_data):
        updated = package.copy()
        flattened = self.flatten_endpoint_data(endpoint_data)
        
        for endpoint_field, package_field in self.get_field_mapping().items():
            if endpoint_field in flattened and package_field in updated:
                value = flattened[endpoint_field]
                if value is not None and value != "":
                    original = updated[package_field]
                    if isinstance(original, bool):
                        updated[package_field] = bool(value)
                    elif isinstance(original, list):
                        updated[package_field] = value if isinstance(value, list) else [value] if value else []
                    else:
                        updated[package_field] = str(value) if isinstance(original, str) else value
        
        for key in package.keys():
            if key in flattened and key not in self.get_field_mapping().values():
                value = flattened[key]
                if value is not None and value != "":
                    original = package[key]
                    if isinstance(original, bool):
                        updated[key] = bool(value)
                    elif isinstance(original, list) and isinstance(value, list):
                        updated[key] = value
                    elif isinstance(original, str):
                        updated[key] = str(value)
                    else:
                        updated[key] = value
        
        updated["last_synced"] = datetime.now().isoformat()
        return updated
    
    def process_packages(self):
        main_data = self.fetch_json(self.base_url)
        if not main_data:
            return {}
        
        packages = main_data.get("packages", [])
        updated_count = skipped_count = error_count = 0
        
        for i, package in enumerate(packages):
            package_id = package.get("id", f"Unknown-{i}")
            endpoint = package.get("endpoint", "").strip()
            
            logger.info(f"Processing {i+1}/{len(packages)}: {package_id}")
            
            if not endpoint:
                skipped_count += 1
                continue
            
            endpoint_data = self.fetch_json(endpoint)
            if not endpoint_data:
                error_count += 1
                continue
            
            packages[i] = self.update_package(package, endpoint_data)
            updated_count += 1
        
        logger.info(f"Complete: {updated_count} updated, {skipped_count} skipped, {error_count} errors")
        
        if "metadata" in main_data:
            main_data["metadata"].update({
                "last_processed": datetime.now().isoformat(),
                "packages_updated": updated_count,
                "packages_skipped": skipped_count,
                "packages_errors": error_count
            })
        
        return main_data
    
    def save_results(self, data):
        filename = urlparse(self.base_url).path.split('/')[-1]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data.get('packages', []))} packages to {filename}")
        return filename

def main():
    try:
        processor = FedRAMPDataProcessor()
        data = processor.process_packages()
        
        if not data:
            return 1
        
        filename = processor.save_results(data)
        metadata = data.get("metadata", {})
        
        print(f"\nPROCESSING COMPLETE")
        print(f"Total packages: {len(data.get('packages', []))}")
        print(f"Updated: {metadata.get('packages_updated', 0)}")
        print(f"Skipped: {metadata.get('packages_skipped', 0)}")
        print(f"Errors: {metadata.get('packages_errors', 0)}")
        print(f"Output: {filename}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())