export default function TrainConsist({color, type, selected = false, yardShadow = false}: {
  color: string; type: string | null; selected?: boolean; yardShadow?: boolean;
}) {
  const freight=type?.toLowerCase().includes('freight')||type?.toLowerCase().includes('goods');
  const coaches=freight?[-135,-90,-45,0,45]:[-90,-45,0,45];
  return <>
    {selected&&<rect x={coaches[0]-10} y="-23" width={95-coaches[0]} height="46" rx="12" fill="none" stroke="#597c4b" strokeWidth="2" strokeDasharray="4 3"/>}
    <g filter={yardShadow?"url(#train-shadow)":undefined}>{coaches.map((x,index)=><g key={x}>
      <rect x={x} y="-13" width="40" height="25" rx={freight?2:index===coaches.length-1?8:4} fill={color}/>
      <rect x={x+3} y="-12" width="34" height="3" rx="2" fill="#fff" opacity=".25"/>
      {[6,20].map(dx=><rect key={dx} x={x+dx} y="-7" width={freight?2:9} height={freight?17:7} rx={freight?0:2} fill="#f9f4df" opacity={freight?.4:1}/>)}
      <circle cx={x+8} cy="13" r="4" fill="#59634e"/><circle cx={x+31} cy="13" r="4" fill="#59634e"/>
    </g>)}</g>
  </>;
}
