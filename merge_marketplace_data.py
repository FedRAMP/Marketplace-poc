import json
import requests
import os

# Define file paths
INPUT_JSON_PATH = 'marketplace_data.json'
OUTPUT_JSON_PATH = 'master_marketplace_data.json'

def merge_data(input_path, output_path):
    merged_entries = []

    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        return

    with open(input_path, 'r') as f:
        marketplace_data = json.load(f)

    for entry in marketplace_data:
        if entry.get('is_legacy'):
            # Legacy entries are already complete
            merged_entries.append(entry)
        elif entry.get('json_link'):
            # Non-legacy entries need to fetch data from the link
            marketplace_id = entry['id']
            json_link = entry['json_link']
            try:
                print(f"Fetching data for {marketplace_id} from {json_link}...")
                response = requests.get(json_link, timeout=10)
                response.raise_for_status() # Raise an exception for HTTP errors
                non_legacy_details = response.json()

                # Merge the details into a new entry
                merged_entry = {
                    'id': marketplace_id,
                    'email': non_legacy_details.get('email'),
                    'name': non_legacy_details.get('name'),
                    'is_legacy': False
                }
                merged_entries.append(merged_entry)
                print(f"Successfully merged {marketplace_id}.")
            except requests.exceptions.RequestException as e:
                print(f"Error fetching data for {marketplace_id} from {json_link}: {e}")
                # Optionally, add the original entry or an error placeholder
                merged_entries.append({
                    'id': marketplace_id,
                    'error': f"Failed to fetch details: {e}",
                    'is_legacy': False
                })
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {json_link}")
                merged_entries.append({
                    'id': marketplace_id,
                    'error': "Invalid JSON from link",
                    'is_legacy': False
                })
        else:
            print(f"Warning: Entry {entry.get('id')} is neither legacy nor has a json_link.")
            merged_entries.append(entry) # Add as is, or handle as an error

    # Write the merged data to the output file
    with open(output_path, 'w') as f:
        json.dump(merged_entries, f, indent=2)
    print(f"Merged data successfully written to '{output_path}'.")

if __name__ == "__main__":
    merge_data(INPUT_JSON_PATH, OUTPUT_JSON_PATH)
