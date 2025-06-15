import requests
import json

DOC_ID = "7b174f2cde12417d1c70c59c"
WORKSPACE_ID = "72a5e2993aa999323f2ba650"
ASSEMBLY_ID = "ea5bd637ddfce7d24d94764b"

BASE_URL = "https://cad.onshape.com/api"

# Assemble the URL for the API call
api_url = f"{BASE_URL}/assemblies/d/{DOC_ID}/w/{WORKSPACE_ID}/e/{ASSEMBLY_ID}/export/step"

# Optional query parameters can be assigned
params = {

}

# Use the keys from the developer portal
access_key = "9tQVtt2G40R3hXiMQ2HNcpQe"
secret_key = "klVucLFinR3AYZo6mBMl4aNUYY6I58d8tvpCzLueloWWcZ9R"

# Define the header for the request
headers = {'Accept': 'application/json;charset=UTF-8;qs=0.09',
           'Content-Type': 'application/json'}

payload = {
    "meshParams": {
        "angularTolerance": 0.001,
        "distanceTolerance": 0.001,
        "maximumChordLength": 0.01,
        "resolution": "FINE",
        "unit": "MILLIMETER"
    },
    "storeInDocument": True
}

# Putting everything together to make the API request
response = requests.post(api_url,
                        auth=(access_key, secret_key),
                        headers=headers,
                        json=payload
                         )

# Convert the response to formatted JSON and print the `name` property
print(json.dumps(response.json(), indent=4))