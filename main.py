import os
import json
import requests
import time
import subprocess
import signal
import sys
import atexit
from flask import Flask, jsonify

app = Flask(__name__)

'''
https://isstracker.spaceflight.esa.int/index_portal.php
http://api.wheretheiss.at/v1/satellites/25544
https://mwood77.github.io/ws4kp-international/
'''

# own coordinates (used to check if you're in the zone)
lat = 1
lng = 1
pos = [lat, lng]

a = [40.878224, 17.021383]
b = [40.878224, 18.776449]
c = [39.688173, 18.776449]
d = [39.688173, 17.021383]

# area that will be scanned for planes, still have to plan that. useful if you don't wanna see planes of the entire world


node_process = None

def start_node_app():
    global node_process
    node_process = subprocess.Popen(
        ['npm', 'run', 'start'], 
        cwd='ws4kp',
        preexec_fn=os.setsid
    )
    print(f"Node app started with PID: {node_process.pid}")

def stop_node_app():
    global node_process
    if node_process:
        try:
            os.killpg(os.getpgid(node_process.pid), signal.SIGTERM)
            node_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(node_process.pid), signal.SIGKILL)
        print("Node app stopped")

def aircraft():
    r = requests.get("https://adsbexchange-com1.p.rapidapi.com/v2/lat/4/lon/4/dist/1/", headers = {"x-rapidapi-host": "adsbexchange-com1.p.rapidapi.com", "x-rapidapi-key": "test"})
    r.raise_for_status()
    data = r.json()
    
# not finished, actually this part is barely started

def in_zone():
    return d[0] <= pos[0] <= a[0] and a[1] <= pos[1] <= b[1]

def get_iss_data():
    r = requests.get("https://api.wheretheiss.at/v1/satellites/25544?units=miles", timeout=10)
    data = r.json()
    iss_pos = [float(data["latitude"]), float(data["longitude"])]
       
    r_people = requests.get("http://api.open-notify.org/astros.json", timeout=10)
    people_data = r_people.json()
    people_n = people_data['number']
    names = [person['name'] for person in people_data['people']]
    print(people_n)
    return {
        'position': iss_pos,
        'velocity': float(data['velocity']),
        'altitude': float(data['altitude']),
        'people': people_n,
        'names': names,
        'in_zone': in_zone()
    }

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>WorldTracker V0 - Fullscreen with WeatherStar</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        html, body { 
            height: 100%; 
            margin: 0; 
            padding: 0; 
            background: #0a0a0a; 
            font-family: 'Courier New', monospace; 
            color: #0f0;
            overflow: hidden;
        }
        #map { 
            height: 100vh; 
            width: 100%; 
        }
        .leaflet-container { 
            background: #1a1a1a; 
        }
        .leaflet-tile-pane { 
            filter: invert(12%) hue-rotate(200deg) brightness(90%) contrast(85%); 
        }
        
        /* Info panel - moved to top-left for weather on right */
        #info-panel {
            position: absolute; 
            top: 10px; 
            left: 10px;
            background: rgba(0,20,0,0.9); 
            border: 2px solid #0f0;
            border-radius: 8px; 
            padding: 15px; 
            max-width: 300px;
            backdrop-filter: blur(10px); 
            z-index: 1000; 
            font-size: 14px;
            box-shadow: 0 0 20px rgba(0,255,0,0.3);
        }
        .data-row { 
            margin: 8px 0; 
        }
        .label { 
            color: #0f0; 
            font-weight: bold; 
        }
        .value { 
            color: #fff; 
        }
        .people { 
            color: #ff0; 
        }
        .zone { 
            color: #ff0; 
            font-weight: bold; 
        }

        /* ISS Day/Night status frame */
        .iss-status {
            position: absolute;
            background: rgba(0,20,0,0.95);
            border: 2px solid #0f0;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
            font-weight: bold;
            box-shadow: 0 0 15px rgba(0,255,0,0.4);
            pointer-events: none;
            z-index: 1000;
            white-space: nowrap;
        }
        .day { color: #ff0; }
        .night { color: #00f; }

        /* WeatherStar - Top Right, larger size */
        .weather-embed {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 380px;
            height: 285px;
            z-index: 1001;
            border: 3px solid #0f0;
            border-radius: 12px;
            box-shadow: 0 0 30px rgba(0,255,0,0.5);
            background: rgba(255,255,255,0.95);
            overflow: hidden;
        }
        .weather-embed iframe {
            width: 100%;
            height: 100%;
            border: none;
            border-radius: 8px;
        }
        .weather-label {
            position: absolute;
            top: 5px;
            right: 10px;
            background: rgba(0,20,0,0.9);
            color: #0f0;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
            z-index: 1002;
            border: 1px solid #0f0;
        }
        /* ISS Tracker Toggle Button */
.iss-toggle-btn {
    position: absolute;
    bottom: 20px;
    left: 20px;
    width: 50px;
    height: 50px;
    background: rgba(0,20,0,0.9);
    border: 2px solid #0f0;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    cursor: pointer;
    z-index: 1002;
    box-shadow: 0 0 20px rgba(0,255,0,0.4);
    transition: all 0.3s ease;
}
.iss-toggle-btn:hover {
    background: rgba(0,255,0,0.2);
    transform: scale(1.1);
}

/* Hideable ISS Tracker */
.iss-tracker {
    position: absolute;
    bottom: 80px;
    left: 20px;
    width: 400px;
    height: 200px;
    z-index: 1001;
    border: 3px solid #0f0;
    border-radius: 12px;
    box-shadow: 0 0 30px rgba(0,255,0,0.5);
    background: rgba(10,10,10,0.95);
    transition: all 0.3s ease;
    opacity: 0;
    transform: translateY(20px);
    visibility: hidden;
    overflow: hidden;
}
.iss-tracker.active {
    opacity: 1;
    transform: translateY(0);
    visibility: visible;
}
.iss-tracker iframe {
    width: 100%;
    height: 100%;
    border: none;
    border-radius: 8px;
}
.iss-tracker-label {
    position: absolute;
    top: 5px;
    right: 10px;
    background: rgba(0,20,0,0.9);
    color: #0f0;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: bold;
    z-index: 1;
    border: 1px solid #0f0;
}

    </style>
</head>
<body>
    <div id="map"></div>
    
    <!-- Info Panel -->
    <div id="info-panel">
        <div class="data-row"><span class="label">ISS Position:</span> <span id="position" class="value">Loading...</span></div>
        <div class="data-row"><span class="label">Velocity:</span> <span id="velocity" class="value">-</span></div>
        <div class="data-row"><span class="label">Altitude:</span> <span id="altitude" class="value">-</span></div>
        <div class="data-row"><span class="label">Crew:</span> <span id="people" class="people">-</span></div>
        <div class="data-row"><span id="zone" class="zone">Checking zone...</span></div>
    </div>

    <!-- ISS Day/Night Status Frame -->
    <div id="iss-status" class="iss-status" style="display: none;"></div>

    <!-- WeatherStar 4000+ Top Right -->
    <div class="weather-label">WeatherStar 4000+</div>
    <div class="weather-embed">
        <iframe src="http://127.0.0.1:8080" title="WeatherStar 4000+ International Simulator"></iframe>
    </div>
    <!-- ISS Tracker Toggle Button -->
<div class="iss-toggle-btn" title="Toggle ISS Tracker">
    <span id="iss-toggle-icon">📡</span>
</div>

<!-- Hideable ISS Tracker - Bottom Left -->
<div id="iss-tracker-container" class="iss-tracker">
    <div class="iss-tracker-label">ESA ISS Tracker</div>
    <iframe 
        src="https://isstracker.spaceflight.esa.int/index_portal.php"
        title="ESA ISS Tracker"
        frameborder="0">
    </iframe>
</div>


    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([0, 0], 2);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap | WorldTracker'
        }).addTo(map);

        const issIcon = L.divIcon({
            className: 'iss-icon', 
            html: '🛰️',
            iconSize: [30, 30], 
            iconAnchor: [15, 15]
        });

        let issMarker = L.marker([0, 0], {icon: issIcon}).addTo(map);
        let issPath = L.polyline([],  {color: '#0f0', weight: 3, opacity: 0.7}).addTo(map);
        let issHistory = [];
        let issStatusEl = document.getElementById('iss-status');

        function isDaytime(lat, lng) {
            const now = new Date();
            const utcHours = now.getUTCHours();
            const offset = -utcHours + (lng / 15); // Rough longitude time offset
            const localHour = (utcHours + offset + 24) % 24;
            
            // Simplified: daytime roughly 6AM-6PM local time
            return localHour >= 6 && localHour < 18;
        }

        function getUSState(lat, lng) {
            // Simplified US bounding boxes for major regions
            if (lat >= 25 && lat <= 49 && lng >= -125 && lng <= -66) {
                if (lat >= 40 && lng <= -74) return 'Northeast';
                if (lat >= 30 && lat <= 48 && lng >= -125 && lng <= -100) return 'West';
                if (lat >= 25 && lat <= 40 && lng >= -105 && lng <= -80) return 'South';
                if (lat >= 35 && lat <= 49 && lng >= -100 && lng <= -80) return 'Midwest';
            }
            return 'International';
        }

        function updateData() {
    fetch('/api/iss')  // local Flask endpoint
        .then(r => r.json())
        .then(data => {
            const lat = data.position[0];
            const lng = data.position[1];
            
            issMarker.setLatLng([lat, lng]);
            issHistory.push([lat, lng]);
            if (issHistory.length > 50) issHistory.shift();
            issPath.setLatLngs(issHistory);
            
            issMarker.bindPopup(`
                <b>International Space Station</b><br>
                ${lat.toFixed(4)}°, ${lng.toFixed(4)}°<br>
                ${data.velocity.toFixed(0)} mph<br>
                ${data.altitude.toFixed(0)} miles
            `);

            document.getElementById('position').textContent = `${lat.toFixed(4)}°, ${lng.toFixed(4)}°`;
            document.getElementById('velocity').textContent = `${data.velocity.toFixed(0)} mph`;
            document.getElementById('altitude').textContent = `${data.altitude.toFixed(0)} miles`;
            document.getElementById('people').textContent = `${data.people} astronauts`;
            
            const zoneEl = document.getElementById('zone');
            zoneEl.textContent = data.in_zone ? 'IN ZONE' : 'Live ISS Tracking';
            zoneEl.className = `data-row ${data.in_zone ? 'zone' : ''}`;
            
            const isDay = isDaytime(lat, lng);
            const region = getUSState(lat, lng);
            const statusClass = isDay ? 'day' : 'night';
            issStatusEl.innerHTML = `<span class="${statusClass}">● ${isDay ? 'DAY' : 'NIGHT'}</span> | ${region}`;
            issStatusEl.style.display = 'block';
            
            const point = map.latLngToContainerPoint([lat, lng]);
            issStatusEl.style.left = `${point.x + 35}px`;
            issStatusEl.style.top = `${point.y - 25}px`;
        })
        .catch(e => console.error('Error:', e));
}


        updateData();
        setInterval(updateData, 5000);

        // ISS Tracker toggle functionality
const issToggleBtn = document.querySelector('.iss-toggle-btn');
const issTracker = document.getElementById('iss-tracker-container');
const issToggleIcon = document.getElementById('iss-toggle-icon');

issToggleBtn.addEventListener('click', () => {
    const isActive = issTracker.classList.contains('active');
    
    if (isActive) {
        issTracker.classList.remove('active');
        issToggleIcon.textContent = '📡';
    } else {
        issTracker.classList.add('active');
        issToggleIcon.textContent = '✕';
    }
});

    </script>
</body>
</html>


    '''

# idk why but the index.html wouldn't work if put in another place like a separate file

@app.route('/api/iss')
def iss_api():
    return jsonify(get_iss_data())

atexit.register(stop_node_app)

if __name__ == '__main__':
    start_node_app()
    try:
        app.run(host='0.0.0.0', port=8085, debug=True)
    finally:
        stop_node_app()
