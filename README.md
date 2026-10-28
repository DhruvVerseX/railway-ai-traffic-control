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

## Deploy: Vercel frontend + Render backend

1. Push the deployment files to your GitHub branch. In Render, create a Blueprint
   from this repository and branch using `render.yaml`. Keep the repository root
   as the service root: the API needs `data/`, `simulation/`, and `ml/models/`.
   The Blueprint uses Python 3.12, the free plan, and `/network` for health checks.
2. Wait for Render's `/network` endpoint to return JSON. Copy the service HTTPS URL.
3. Import the repository into Vercel with **Root Directory = `frontend`** and the
   **Next.js** framework preset. Keep the default install/build/output settings.
4. Add `RAILWAY_API_URL=https://YOUR-SERVICE.onrender.com` (no trailing slash) to
   Vercel's Production and Preview environments, then deploy or redeploy.
   This is a server-only variable: do not prefix it with `NEXT_PUBLIC_`.
5. Verify `/api/railway/network` on Vercel, then load a scenario at `/control`,
   advance it, and compare two controllers.

`HOST` and `PORT` configure only the API listener. Local defaults remain
`127.0.0.1:8000`; Render sets `PORT` and the Blueprint sets `HOST=0.0.0.0`.
No simulator or model behavior changes for hosting.

Free Render services sleep when idle and may take about a minute to wake, longer
than the frontend's 30-second API timeout. Retry after the API is awake. Sessions
are stored in process memory and disappear on restart/redeploy; keep one API
instance. This is a public educational demo without authentication, not a live
railway system. An always-running paid instance requires a separate plan choice.

## Present the project

1. Select **Mathura Junction** and a queue size (12 trains by default).
2. Click **Load trains** to load a seeded station queue using project train records and valid outgoing routes.
3. Choose **Analyze** to inspect the selected controller's recommendations and safety checks.
4. **Dispatch** executes permitted moves and starts automatic playback. The controller revisits decisions at readiness times, section completions, dwell completion, and headway expiry. Playback advances one simulated minute per update.
5. **See the difference** reruns arrival-order and optimized dispatch from identical initial queues for 120 minutes. Inspect departures and queue graphs, a synchronized station replay, throughput/waiting bars, and each train's waiting/clearance timeline.

Station throughput means departures from the selected station per hour, distinct from completed journeys across the network. The queue is a staged demonstration, not a real timetable. Delay and waiting accumulate during eligible waiting periods. The station demo supports the trained V2 classifier, FIFO, and a shortest-clearance heuristic with 45-minute aging. None is presented as a global optimum. V3 and the ranking controllers remain separate from this interface.

The underlying section model allows one train per entire section, even when track metadata lists several tracks, and applies headway after section exit. The station yard has four simulated platforms, working departure signals, platform reassignment, and a shared exit switch with one-minute clearance. Occupied platforms reject reassignment, red signals block departure, and outgoing routes stay locked until the train clears its section. The illustrated train leaves the yard before completing its longer section journey. These are educational station constraints, rather than a detailed reconstruction of Mathura Junction. Both comparison policies use these same conservative rules. Improved throughput is measured for each run, not assumed for every scenario.

## Show the backend and trained model

The station demo defaults to **ML · Random Forest V2**. Load trains, choose **Analyze**,
then **Dispatch**. The decision panel shows the Python backend request ID, actual
model inputs, HOLD/RELEASE probabilities, safety checks, and the action the simulator
accepted. Expand **Inspect the backend response** or inspect `/api/railway/execute`
in the browser Network panel for the response and recorded movement events.

The saved `ml/models/train_controller_v2.pkl` drives this mode. It is loaded once
and reused; it is not retrained during the demo. A missing model or dependency
produces an explicit error. FIFO and the shortest-clearance heuristic remain
available; the comparison screen currently compares those two policies, not ML.
The model's HOLD decision is respected, so a queue can remain waiting. Model
probabilities do not guarantee safety: occupancy, headway and station interlocking
still gate movements, including a recheck when executing each release.

This is a frontend connected to a Python simulation backend, not a live railway
control system. The station queues differ from the classifier's generated training
distribution; integrating inference does not establish improved throughput.

## Checks

The station view uses Anime.js to interpolate between backend-confirmed train
positions along the drawn track curves. It does not advance simulation time or
predict movement between API responses. Pause settles to the confirmed position;
reset recreates the scene. Route pulses run only during playback on locked routes,
and reduced-motion preferences disable the animated transitions.

```powershell
.\.venv-ui\Scripts\python.exe backend/test_api.py
.\.venv-ui\Scripts\python.exe backend/test_station_dispatch.py
.\.venv-ui\Scripts\python.exe backend/test_ml_dispatch.py
cd frontend
npm run typecheck
npm run test:motion
npm run build
```

The motion geometry check uses Node.js native TypeScript support (Node 22.18+).

The API uses isolated in-memory simulation sessions, limited to 50; restarting it clears them. This local presentation app has no public deployment authentication. ML initialization errors are reported explicitly; select the heuristic or FIFO to continue without ML. Model pickle compatibility depends on the scikit-learn version used during training.

