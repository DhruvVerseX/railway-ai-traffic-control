'use client';
import {animate} from 'animejs';
import {useEffect, useRef} from 'react';
import {yardPose} from './yard-motion';

export default function YardTrain({id,name,progress,platform,exitY,color,selected,onSelect,playing,speed}:{
  id:string;name:string;progress:number;platform:number;exitY:number;color:string;
  selected:boolean;onSelect:(id:string)=>void;playing:boolean;speed:number;
}) {
  const element = useRef<SVGGElement>(null);
  const position = useRef({progress});
  const initial = useRef(yardPose(progress, platform, exitY));
  const previousPlatform = useRef(platform);
  const animation = useRef<ReturnType<typeof animate>|null>(null);
  useEffect(()=>{
    const target = element.current;
    if (!target) return;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const render = ()=>{
      const pose = yardPose(position.current.progress, platform, exitY);
      target.setAttribute('transform', `translate(${pose.x},${pose.y}) rotate(${pose.angle})`);
      target.style.visibility = pose.visible ? 'visible' : 'hidden';
    };
    const settle = ()=>{
      animation.current?.cancel();
      animation.current = null;
      position.current.progress = progress;
      render();
    };
    if (media.matches || previousPlatform.current !== platform) settle();
    else animation.current = animate(position.current, {
      progress, duration: Math.min(1100, 1400 / speed), ease: 'linear', onUpdate: render,
    });
    previousPlatform.current = platform;
    const reduceMotion = ()=>{if(media.matches) settle()};
    media.addEventListener('change',reduceMotion);
    return ()=>{animation.current?.cancel();media.removeEventListener('change',reduceMotion)};
  },[progress,platform,exitY,speed]);
  useEffect(()=>{if(!playing) animation.current?.complete()},[playing]);
  const pose = initial.current;
  return <g ref={element} transform={`translate(${pose.x},${pose.y}) rotate(${pose.angle})`}
    style={{visibility:pose.visible?'visible':'hidden'}}
    role="button" tabIndex={0} className="yard-train" aria-label={`Select ${name}`}
    data-train-id={id} data-backend-progress={progress}
    onClick={()=>onSelect(id)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(id)}}}>
    <title>{name}</title>
    {selected&&<rect x="-100" y="-22" width="198" height="44" rx="12" fill="none" stroke="#597c4b" strokeWidth="2" strokeDasharray="4 3"/>}
    <g filter="url(#train-shadow)">{[-90,-45,0,45].map((x,index)=><g key={x}>
      <rect x={x} y="-13" width="40" height="25" rx={index===3?8:4} fill={color}/>
      <rect x={x+3} y="-12" width="34" height="3" rx="2" fill="#fff" opacity=".25"/>
      {[6,20].map(dx=><rect key={dx} x={x+dx} y="-7" width="9" height="7" rx="2" fill="#f9f4df"/>)}
      <circle cx={x+8} cy="13" r="4" fill="#59634e"/><circle cx={x+31} cy="13" r="4" fill="#59634e"/>
    </g>)}</g>
  </g>;
}
