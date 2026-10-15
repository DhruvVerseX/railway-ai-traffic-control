import { NextRequest, NextResponse } from 'next/server';
const allowed = new Set(['network', 'analysis', 'compare', 'scenario', 'advance', 'decide', 'execute', 'release', 'platform', 'signal', 'state']);
async function proxy(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const {path} = await context.params;
  if (!allowed.has(path[0]) || path.length > 2 || (path.length === 2 && (path[0] !== 'state' || !/^[\da-f-]{36}$/.test(path[1])))) return NextResponse.json({error:'Unknown endpoint'}, {status:404});
  try {
    const response = await fetch(`${process.env.RAILWAY_API_URL || 'http://127.0.0.1:8000'}/${path.join('/')}`, {method: request.method, headers:{'Content-Type':'application/json'}, ...(request.method === 'POST' ? {body:await request.text()} : {}), cache:'no-store', signal:AbortSignal.timeout(30000)});
    return NextResponse.json(await response.json(), {status:response.status});
  } catch { return NextResponse.json({error:'Cannot connect to the railway backend. Start it with: py backend/server.py'}, {status:503}); }
}
export {proxy as GET, proxy as POST};
