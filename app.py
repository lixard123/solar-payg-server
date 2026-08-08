from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import os

app = Flask(__name__)

# --- HIVEMQ CREDENTIALS ---
MQTT_HOST = "310c858075bb47c799f6c6c5cb361145.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "tusker123"
MQTT_PASS = "1qaz2wsx"  # <-- REPLACE WITH YOUR REAL PASSWORD
MQTT_TOPIC = "solar/heater/demo/data"

# --- MQTT SETUP ---
mqtt_client = mqtt.Client()
mqtt_client.tls_set()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
try:
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    print("✅ MQTT Connected")
except Exception as e:
    print(f"❌ MQTT Error: {e}")

# ==========================================
# DEVICE DATABASE (INSTALLMENT MODEL)
# ==========================================
device_data = {
    "DEMO_HEATER": {
        "total_lifetime_kwh": 0.0,       # Tracks usage for stats, NOT for power cut-off
        "is_installment_paid": True,     # THE ONLY FLAG THAT CONTROLS POWER
        "is_locked": False               # Lockout flag
    }
}

@app.route('/api/device-status', methods=['POST'])
def device_status():
    data = request.get_json()
    dev_id = data['device_id']
    new_usage = data['total_kwh']
    
    record = device_data.get(dev_id)
    if not record:
        return jsonify({"error": "Device not found"}), 404

    # --- STEP 1: TRACK USAGE (Report only - does NOT cut power) ---
    record["total_lifetime_kwh"] += new_usage

    # --- STEP 2: DECIDE RELAY STATE SOLELY ON INSTALLMENT STATUS ---
    if record["is_installment_paid"]:
        relay_state = 1  # Power ON
        record["is_locked"] = False
        print(f"✅ {dev_id} is PAID. Power ON. (Total usage: {record['total_lifetime_kwh']:.2f} kWh)")
    else:
        relay_state = 0  # Power OFF
        record["is_locked"] = True
        print(f"🚫 {dev_id} is UNPAID. Power OFF.")

    # --- STEP 3: FORWARD TO MQTT (For your live dashboard) ---
    try:
        payload = {**data, "relay_state": relay_state}
        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
    except:
        pass

    # --- STEP 4: REPLY TO THE ESP32 ---
    return jsonify({
        "relay_state": relay_state,
        "is_locked": record["is_locked"]
    })

# ==========================================
# ADMIN ENDPOINT: MARK INSTALLMENT AS PAID
# ==========================================
@app.route('/api/mark-paid/<dev_id>', methods=['POST'])
def mark_paid(dev_id):
    if dev_id in device_data:
        device_data[dev_id]["is_installment_paid"] = True
        device_data[dev_id]["is_locked"] = False
        return jsonify({
            "status": "success", 
            "message": "Installment marked as paid. Power will restore automatically on next ESP32 ping."
        })
    return jsonify({"error": "Device not found"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)