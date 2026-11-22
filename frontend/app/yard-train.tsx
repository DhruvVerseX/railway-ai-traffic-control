'use client';
import {useEffect,useRef} from 'react';
import {yardPose,arrivalPose} from './yard-motion';
import TrainConsist from './train-consist';

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
  return <g ref={element} transform={`translate(-150,${125+(platform-1)*85})`}
    role="button" tabIndex={0} className="yard-train" aria-label={`Select ${name} · ${id}`} aria-pressed={selected}
    data-train-id={id} data-departing={departing}
    onClick={()=>onSelect(id)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(id)}}}>
    <title>{name} · {id}{type?` · ${type}`:''}</title>
    {aiWarning&&<ellipse className="control-ai-ring" cx="0" cy="0" rx="112" ry="27"/>}
    {mockWarning&&<g className="mock-train-warning"><title>CLIENT MOCK · {mockWarning}</title><path d="M70 -44L86 -18H54Z" fill="#fff4d6" stroke="#9b6336" strokeWidth="2"/><text x="70" y="-23" textAnchor="middle" fontSize="19" fill="#86532e">!</text></g>}
    <TrainConsist color={color} type={type} selected={selected} yardShadow/>
  </g>;
}
