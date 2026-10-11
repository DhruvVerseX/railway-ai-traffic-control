# Railwise — railway AI control room

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

1. Choose an everyday railway situation and click **Show me what happens**.
2. Meet the four coloured trains. Select a train on the illustrated railway or its journey card.
3. Click **Ask AI who should go next** to read the actual model decision in plain language.
4. Click **Let AI make this move**, then move time forward or play the railway.
5. Open **See the difference** to understand the saved evaluation results.

The experience guides the viewer through meeting trains, understanding a decision, and watching its effect. Play advances time; AI decisions remain explicit. The map is schematic. Comparisons use saved baseline/V2/V3 results, while the interactive example uses the trained V2 controller. Model training stays in the existing `ml` scripts.

## Checks

```powershell
.\.venv-ui\Scripts\python.exe backend/test_api.py
cd frontend
npm run typecheck
npm run build
```

The API uses isolated in-memory simulation sessions, limited to 50; restarting it clears them. This local presentation app has no public deployment authentication. AI initialization errors appear in the interface while the simulator remains usable. Model pickle compatibility depends on the scikit-learn version used during training.

