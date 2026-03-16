import urllib.request
import urllib.error
import json

url = "https://arbitra-cloud.vercel.app/api/stats"
try:
    response = urllib.request.urlopen(url)
    print("Success:", response.read().decode())
except urllib.error.HTTPError as e:
    body = e.read().decode()
    try:
        data = json.loads(body)
        print("TRACEBACK:\n" + data.get("traceback", "No traceback found"))
        print("\nERROR:\n" + data.get("error", "No error found"))
    except:
        print("Raw HTTP Error Body:\n" + body)
except Exception as e:
    print("Other error:", str(e))
