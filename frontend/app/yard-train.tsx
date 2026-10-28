'use client';
import {useEffect,useRef} from 'react';
import {yardPose,arrivalPose} from './yard-motion';

export default function YardTrain({id,name,departing,platform,exitY,color,type,selected,onSelect,playing,speed,aiWarning=false,staticProgress,mockWarning}:{
  id:string;name:string;departing:boolean;platform:number;exitY:number;color:string;type:string|null;
  selected:boolean;onSelect:(id:string)=>void;playing:boolean;speed:number;aiWarning?:boolean;
  staticProgress?:number;mockWarning?:string;
}) {
  const element=useRef<SVGGElement>(null);
  const position=useRef(-1);
  const lastPlatform=useRef(platform);
  const paused=useRef(false);
  const wasPlaying=useRef(playing);
  const rate=useRef(speed);
  rate.current=speed;
  useEffect(()=>{
    if(wasPlaying.current && !playing) paused.current=true;
    if(playing) paused.current=false;
    wasPlaying.current=playing;
  },[playing]);
  useEffect(()=>{
    const target=element.current;
    if(!target)return;
    const media=window.matchMedia('(prefers-reduced-motion: reduce)');
    let frame=0,last=0,dwell=0;
    // shortcut: station motion illustrates confirmed transitions; use measured station progress if the API adds it.
    if(lastPlatform.current!==platform)position.current=-1;
    lastPlatform.current=platform;
    paused.current=false;
    const end=departing?1:0;
    const render=()=>{
      const pose=position.current<0?arrivalPose(position.current,platform):yardPose(position.current/3,platform,exitY);
      target.setAttribute('transform',`translate(${pose.x},${pose.y}) rotate(${pose.angle})`);
      target.style.visibility=pose.visible?'visible':'hidden';
      target.setAttribute('aria-hidden',String(!pose.visible));
      target.setAttribute('tabindex',pose.visible?'0':'-1');
    };
    const tick=(now:number)=>{
      const elapsed=last?now-last:0;last=now;
      if(media.matches)position.current=end;
      else if(!paused.current){
        if(dwell>0)dwell=Math.max(0,dwell-elapsed*rate.current);
        else {
          const before=position.current;
          position.current=Math.min(end,before+elapsed*rate.current/(before<0?1000:1800));
          if(before<0&&position.current>=0){position.current=0;dwell=250;}
        }
      }
      render();
      if(position.current<end)frame=requestAnimationFrame(tick);
    };
    if(staticProgress!==undefined){position.current=mockWarning?Math.min(.97,Math.max(0,staticProgress*3)):Math.max(0,staticProgress*3);render();return;}
    render();frame=requestAnimationFrame(tick);
    return()=>cancelAnimationFrame(frame);
  },[departing,platform,exitY,staticProgress]);
  const freight=type?.toLowerCase().includes('freight')||type?.toLowerCase().includes('goods');
  const coaches=freight?[-135,-90,-45,0,45]:[-90,-45,0,45];
  return <g ref={element} transform={`translate(-150,${125+(platform-1)*85})`}
    role="button" tabIndex={0} className="yard-train" aria-label={`Select ${name} · ${id}`} aria-pressed={selected}
    data-train-id={id} data-departing={departing}
    onClick={()=>onSelect(id)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(id)}}}>
    <title>{name} · {id}{type?` · ${type}`:''}</title>
    {aiWarning&&<ellipse className="control-ai-ring" cx="0" cy="0" rx="112" ry="27"/>}
    {mockWarning&&<g className="mock-train-warning"><title>CLIENT MOCK · {mockWarning}</title><path d="M70 -44L86 -18H54Z" fill="#fff4d6" stroke="#9b6336" strokeWidth="2"/><text x="70" y="-23" textAnchor="middle" fontSize="19" fill="#86532e">!</text></g>}
    {selected&&<rect x={coaches[0]-10} y="-23" width={95-coaches[0]} height="46" rx="12" fill="none" stroke="#597c4b" strokeWidth="2" strokeDasharray="4 3"/>}
    <g filter="url(#train-shadow)">{coaches.map((x,index)=><g key={x}>
      <rect x={x} y="-13" width="40" height="25" rx={freight?2:index===coaches.length-1?8:4} fill={color}/>
      <rect x={x+3} y="-12" width="34" height="3" rx="2" fill="#fff" opacity=".25"/>
      {[6,20].map(dx=><rect key={dx} x={x+dx} y="-7" width={freight?2:9} height={freight?17:7} rx={freight?0:2} fill="#f9f4df" opacity={freight?.4:1}/>)}
      <circle cx={x+8} cy="13" r="4" fill="#59634e"/><circle cx={x+31} cy="13" r="4" fill="#59634e"/>
    </g>)}</g>
  </g>;
}
