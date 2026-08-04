from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# --- DATABASE ---
device_data = {
    "MONITOR_001": {
        "credit_units": 10.0,
    }
}

@app.route('/', methods=['GET'])
def home():
    return "Solar PAYG Server is Live!"

@app.route('/api/device-status', methods=['POST'])
def update_status():
    data = request.get_json()
    dev_id = data['device_id']
    battery_v = data['battery_voltage']
    new_usage = data['heater_units']

    state = device_data[dev_id]
    state['credit_units'] -= new_usage

    print(f"Device: {dev_id} | Used: {new_usage} | Balance: {state['credit_units']}")

    return jsonify({
        "status": "ok",
        "remaining_units": state['credit_units']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
