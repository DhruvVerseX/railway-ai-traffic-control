'use client';
import {useControl} from './control-store';
export default function ReplayBar() {
  const {records,cursor,replaying,busy,seek,returnLive}=useControl();
  const index=cursor??Math.max(0,records.length-1);
  return <section className="replay-bar" aria-label="Recorded simulation replay">
    <div className="replay-heading"><span><b>{replaying?'REPLAY · client recording':'LIVE · recording locally'}</b> · frame {records.length?index+1:0}/{records.length}</span><span>◆ disruption · ‖ hold · ✧ override · × failure</span><button disabled={!replaying||busy} onClick={returnLive}>Return to live</button></div>
    <div className="replay-controls"><button aria-label="Previous recorded frame" disabled={busy||!records.length||index===0} onClick={()=>seek(index-1)}>‹</button><div className="replay-track"><input aria-label="Replay frame" type="range" min="0" max={Math.max(0,records.length-1)} value={index} disabled={busy||records.length<2} onChange={e=>seek(Number(e.target.value))}/>
      <div className="replay-markers">{records.flatMap((frame,i)=>frame.markers.map((marker,j)=><button key={`${i}-${j}`} className={'replay-marker '+marker.kind} style={{left:`${records.length>1?i/(records.length-1)*100:0}%`}} title={`${marker.label} · frame ${i+1} · ${marker.source}`} aria-label={`Jump to frame ${i+1}: ${marker.label}`} disabled={busy} onClick={()=>seek(i)}>{marker.kind==='disruption'?'◆':marker.kind==='hold'?'‖':marker.kind==='override'?'✧':'×'}</button>))}</div>
    </div><button aria-label="Next recorded frame" disabled={busy||index>=records.length-1} onClick={()=>seek(index+1)}>›</button></div>
    <span className="replay-note">Local playback only; no Python seek/restore. Return to live before sending commands. Recording is cleared on reset or page reload.</span>
  </section>;
}
