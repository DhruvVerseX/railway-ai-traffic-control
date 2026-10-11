# Railwise — visual railway station simulation

A Next.js interface around the existing Python railway project. The original Streamlit interface remains available in `website/app.py`.

## Start locally

Use Python 3.12+ and Node.js 20.9+ in two terminals, from this directory.

```powershell
py -m venv .venv-ui
.\.venv-ui\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv-ui\Scripts\python.exe backend/server.py
```

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:3000. The API listens only on 127.0.0.1:8000; Next.js forwards requests through `/api/railway`. Set `RAILWAY_API_URL` in `frontend/.env.local` if using a different backend port.

## Present the project

1. Select **Mathura Junction** and a queue size (12 trains by default).
2. Click **Show me what happens** to load a seeded station queue using real project train records and valid outgoing routes.
3. Click **Find the next safe moves** to inspect throughput-focused dispatch explanations.
4. **Apply this dispatch plan** releases compatible trains and starts automatic playback. The controller revisits decisions at readiness times, section completions, dwell completion, and headway expiry. Playback advances one simulated minute per update.
5. **See the difference** reruns arrival-order and optimized dispatch from identical initial queues for 120 minutes. Inspect departures and queue graphs, a synchronized station replay, throughput/waiting bars, and each train's waiting/clearance timeline.

Station throughput means departures from the selected station per hour, distinct from completed journeys across the network. The queue is a staged demonstration, not a real timetable. Delay and waiting accumulate during eligible waiting periods. The new dispatcher is a transparent shortest-clearance heuristic with 45-minute aging; it does not claim a global optimum or impersonate the earlier trained V2/V3 models. Those models and evaluation scripts remain available separately.

The underlying section model allows one train per entire section, even when track metadata lists several tracks, and applies headway after section exit. The station yard has four simulated platforms, working departure signals, platform reassignment, and a shared exit switch with one-minute clearance. Occupied platforms reject reassignment, red signals block departure, and outgoing routes stay locked until the train clears its section. The illustrated train leaves the yard before completing its longer section journey. These are educational station constraints, rather than a detailed reconstruction of Mathura Junction. Both comparison policies use these same conservative rules. Improved throughput is measured for each run, not assumed for every scenario.

## Checks

```powershell
.\.venv-ui\Scripts\python.exe backend/test_api.py
.\.venv-ui\Scripts\python.exe backend/test_station_dispatch.py
cd frontend
npm run typecheck
npm run build
```

The API uses isolated in-memory simulation sessions, limited to 50; restarting it clears them. This local presentation app has no public deployment authentication. AI initialization errors appear in the interface while the simulator remains usable. Model pickle compatibility depends on the scikit-learn version used during training.

