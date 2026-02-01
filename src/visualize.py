import requests
import numpy as np
import plotly.graph_objects as go
from skyfield.api import load, EarthSatellite, Timescale
import os

def load_satellites(url: str, max_sats: int = 30):
    """Fetch TLE data from Celestrak and create EarthSatellite objects."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    lines = response.text.splitlines()
    
    satellites = []
    ts = load.timescale()
    i = 0
    while len(satellites) < max_sats and i + 2 < len(lines):
        name = lines[i].strip()
        line1 = lines[i + 1].strip()
        line2 = lines[i + 2].strip()
        if line1.startswith('1 ') and line2.startswith('2 '):
            sat = EarthSatellite(line1, line2, name, ts)
            satellites.append(sat)
        i += 3
    return satellites

# Configuration
STARLINK_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
MAX_SATS = 30
DURATION_DAYS = 0.1  # ~2.4 hours for smooth animation
NUM_FRAMES = 300

# Load data
ts = load.timescale()
satellites = load_satellites(STARLINK_URL, MAX_SATS)

start_time = ts.utc(2026, 2, 1)  # Fixed start for reproducibility
t = ts.linspace(start_time, start_time + DURATION_DAYS, NUM_FRAMES)

positions = []
names = []
for sat in satellites:
    geocentric = sat.at(t)
    pos = geocentric.position.km
    positions.append(pos)
    names.append(sat.name[:20])  # Truncate long names

# Colors for satellites
colors = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'] * (MAX_SATS // 10 + 1)

# Earth sphere
R_EARTH = 6371
phi, theta = np.mgrid[0:np.pi:30j, 0:2*np.pi:60j]
x_earth = R_EARTH * np.sin(phi) * np.cos(theta)
y_earth = R_EARTH * np.sin(phi) * np.sin(theta)
z_earth = R_EARTH * np.cos(phi)

earth = go.Surface(
    x=x_earth, y=y_earth, z=z_earth,
    colorscale='Blues',
    showscale=False,
    opacity=0.7,
    name='Earth'
)

# Static orbit traces
orbit_traces = []
for i, pos in enumerate(positions):
    orbit_traces.append(go.Scatter3d(
        x=pos[0], y=pos[1], z=pos[2],
        mode='lines',
        line=dict(color=colors[i], width=3),
        name=names[i],
        hoverinfo='name'
    ))

# Initial satellite markers (first position)
initial_markers = []
for i in range(len(satellites)):
    pos = positions[i]
    initial_markers.append(go.Scatter3d(
        x=[pos[0, 0]], y=[pos[1, 0]], z=[pos[2, 0]],
        mode='markers',
        marker=dict(size=8, color=colors[i]),
        name=names[i]
    ))

# Build figure
fig = go.Figure(data=[earth] + orbit_traces + initial_markers)

# Animation frames (update only markers)
frames = []
for frame_num in range(NUM_FRAMES):
    marker_updates = []
    for i in range(len(satellites)):
        pos = positions[i]
        marker_updates.append(go.Scatter3d(
            x=[pos[0, frame_num]], y=[pos[1, frame_num]], z=[pos[2, frame_num]],
            mode='markers',
            marker=dict(size=8, color=colors[i]),
            name=names[i]
        ))
    frames.append(go.Frame(data=marker_updates, name=str(frame_num)))

fig.frames = frames

# Layout and controls
fig.update_layout(
    title="3D Orbit Visualization — Partial Starlink Constellation",
    scene=dict(
        xaxis_title='X (km)',
        yaxis_title='Y (km)',
        zaxis_title='Z (km)',
        aspectmode='data',
        xaxis=dict(range=[-10000, 10000]),
        yaxis=dict(range=[-10000, 10000]),
        zaxis=dict(range=[-10000, 10000]),
    ),
    updatemenus=[dict(
        type="buttons",
        buttons=[dict(label="Play",
                      method="animate",
                      args=[None, dict(frame=dict(duration=50, redraw=True),
                                      transition=dict(duration=0),
                                      fromcurrent=True)]),
                 dict(label="Pause",
                      method="animate",
                      args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")])],
        showactive=False,
        y=1.1,
        x=0.1
    )],
    scene_camera=dict(eye=dict(x=1.5, y=1.5, z=1))
)

# === AUTO EXPORT SECTION ===
os.makedirs("assets", exist_ok=True)
os.makedirs("assets/frames", exist_ok=True)

# Save main static view
fig.write_image("assets/static_overview.png", width=1920, height=1080, scale=2)

# Additional angled views
camera_views = [
    {"eye": {"x": 1.5, "y": 1.5, "z": 1.0}, "name": "default"},
    {"eye": {"x": 0.0, "y": 2.0, "z": 0.0}, "name": "top"},
    {"eye": {"x": 2.0, "y": 0.0, "z": 0.0}, "name": "side"},
    {"eye": {"x": -1.5, "y": -1.5, "z": 1.0}, "name": "opposite"},
]

for view in camera_views:
    fig.update_layout(scene_camera={"eye": view["eye"]})
    fig.write_image(f"assets/static_{view['name']}_view.png", width=1920, height=1080, scale=2)

# Reset camera
fig.update_layout(scene_camera=dict(eye=dict(x=1.5, y=1.5, z=1)))

# Export frames for GIF
print("Exporting animation frames for GIF...")
frame_idx = 0
for frame_num in range(0, NUM_FRAMES, 2):  # Keep skipping every 2nd for speed (~150 frames)
    frame_data = frames[frame_num].data
    fig.update(data=[earth] + orbit_traces + list(frame_data))
    fig.write_image(f"assets/frames/frame_{frame_idx:04d}.png", width=1280, height=720, scale=1)
    frame_idx += 1
       
# Save interactive HTML
fig.write_html("assets/starlink_3d_orbit.html")

print("All done!")
print("   - Static images: assets/static_*.png")
print("   - Animation frames: assets/frames/")
print("   - Interactive: assets/starlink_3d_orbit.html")
