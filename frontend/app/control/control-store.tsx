'use client';
import {createContext,useCallback,useContext,useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {controlAdapter,renderStation} from './control-adapter';
import {activeDisruptions,decisionItems,decisionMarkers,disruptionNames,mergeEvents,recordedView,safetyOverride,type Comparison,type ControlEvent,type Disruption,type DisruptionKind,type FeedItem,type Network,type Policy,type PairFrame,type ReplayFrame,type Snapshot,type TimelineMarker} from './control-data';

type View='station'|'section'|'network'|'compare';
function useControlState() {
  const [network,setNetwork]=useState<Network|null>(null);
  const [data,setData]=useState<{snapshot:Snapshot|null;history:Snapshot[];events:ControlEvent[];feed:FeedItem[];session:string;records:ReplayFrame[]}>({snapshot:null,history:[],events:[],feed:[],session:'',records:[]});
  const [comparison,setComparison]=useState<Comparison|null>(null),[cursor,setCursor]=useState<number|null>(null);
  const [policy,setPolicy]=useState<Policy>('ml'),[station,setStation]=useState('MTJ');
  const [playing,setPlaying]=useState(false),[speed,setSpeed]=useState(1),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [view,setViewState]=useState<View>('station');
  const [selected,setSelected]=useState<string|null>(null),[hovered,setHovered]=useState<string|null>(null),[sectionId,setSectionId]=useState('');
  const [focusToken,setFocusToken]=useState(0);
  const [layers,setLayers]=useState({names:true,trains:true,signals:true,occupancy:true});
  const pending=useRef(false),request=useRef<AbortController|null>(null);
  const records=view==='compare'?comparison?.records??[]:data.records;
  const replaying=cursor!==null;

  const connect=useCallback(async()=>{
    request.current?.abort();const controller=new AbortController();request.current=controller;
    try{setError('');const result=await controlAdapter.network(controller.signal);setNetwork(result);setSectionId(result.sections.find(s=>s.from_station==='MTJ'||s.to_station==='MTJ')?.section_id??result.sections[0]?.section_id??'');}
    catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Backend or ngrok tunnel unreachable.');}
  },[]);
  useEffect(()=>{void connect();return()=>request.current?.abort();},[connect]);

  const command=useCallback(async(path:string,extra:object={})=>{
    if(pending.current||(cursor!==null&&path!=='scenario'&&path!=='compare'))return;
    pending.current=true;setBusy(true);setError('');
    const controller=new AbortController();request.current=controller;
    try {
      if(view==='compare') {
        if(path==='compare'||path==='scenario') {
          const policies=(extra as {policies?:[Policy,Policy]}).policies??comparison?.policies??['fifo','ml'];
          const pair=await controlAdapter.createComparison(station,policies,controller.signal);
          setComparison({...pair,policies,verified:true,records:[{...pair,disruptions:[],markers:[]}]});
          setCursor(null);setPlaying(false);setSelected(pair.left.trains[0]?.train_id??null);
        } else if(path==='advance'&&comparison) {
          if(comparison.error)throw new Error('Restart both comparison runs after the recorded failure.');
          const pair=await controlAdapter.advanceComparison(comparison.left,comparison.right,controller.signal);
          const markers:TimelineMarker[]=[...decisionMarkers(pair.left),...decisionMarkers(pair.right),...(pair.error?[{kind:'failure' as const,label:pair.error,source:'backend' as const}]:[])];
          setComparison(previous=>previous?{...previous,...pair,records:[...previous.records,{left:pair.left,right:pair.right,error:pair.error,disruptions:previous.records.at(-1)?.disruptions??[],markers}]}:previous);
          if(pair.error){setError(pair.error);setPlaying(false);}
          if([pair.left,pair.right].every(s=>s.trains.every(t=>t.status==='ARRIVED')))setPlaying(false);
        }
        return;
      }
      const response=await controlAdapter.request<Snapshot>(path,path==='scenario'?{station,count:12,seed:42,policy,...extra}:{session:data.session,policy,...extra},controller.signal);
      const reset=path==='scenario';
      setData(previous=>{
        const events=mergeEvents(reset?[]:previous.events,response.events);
        const history=reset?[]:previous.history.filter(s=>s.time!==response.time);
        const feed=new Map((reset?[]:previous.feed).map(item=>[item.key,item]));
        for(const item of decisionItems(response))feed.set(item.key,item);
        const disruptions=reset?[]:previous.records.at(-1)?.disruptions??[];
        return {snapshot:response,events,history:[...history,response],feed:[...feed.values()].sort((a,b)=>b.time-a.time),session:response.session??previous.session,
          records:[...(reset?[]:previous.records),{snapshot:response,disruptions,markers:decisionMarkers(response)}]};
      });
      setPolicy(response.policy);setStation(response.station);
      if(reset){setCursor(null);setPlaying(false);setSelected(response.trains[0]?.train_id??null);setHovered(null);setFocusToken(0);setSectionId(network?.sections.find(s=>s.from_station===response.station||s.to_station===response.station)?.section_id??'');}
      if(response.trains.every(t=>t.status==='ARRIVED'))setPlaying(false);
    } catch(e) {
      if(!controller.signal.aborted){setError(e instanceof Error?e.message:'Backend or ngrok tunnel unreachable.');setPlaying(false);}
    } finally {pending.current=false;if(!controller.signal.aborted)setBusy(false);}
  },[data.session,policy,station,network,view,comparison,cursor]);

  useEffect(()=>{
    if(!playing||busy)return;
    if(cursor!==null) {
      if(cursor>=records.length-1){setPlaying(false);return;}
      const timer=setTimeout(()=>setCursor(cursor+1),1800/speed);return()=>clearTimeout(timer);
    }
    if(view==='compare'?!comparison:!data.session)return;
    const timer=setTimeout(()=>void command('advance',{minutes:1}),1800/speed);
    return()=>clearTimeout(timer);
  },[playing,busy,data.session,speed,command,cursor,records.length,view,comparison]);

  const replay=useMemo(()=>cursor!==null&&view!=='compare'?recordedView(data.records,cursor):null,[cursor,view,data.records]);
  const shownComparison=useMemo(()=>comparison&&view==='compare'&&cursor!==null?{...comparison,...controlAdapter.seek(comparison.records,cursor),error:comparison.records[cursor].error,records:comparison.records.slice(0,cursor+1)}:comparison,[comparison,view,cursor]);
  const shown=view==='compare'?shownComparison?.left??null:replay?.snapshot??data.snapshot;
  const recordedDisruptions=view==='compare'?shownComparison?.records.at(-1)?.disruptions??[]:replay?.disruptions??data.records.at(-1)?.disruptions??[];
  const disruptions=useMemo(()=>activeDisruptions(recordedDisruptions,shown?.time??0),[recordedDisruptions,shown?.time]);
  const scene=useMemo(()=>shown?renderStation(shown,disruptions):null,[shown,disruptions]);
  const pairFeed=useMemo(()=>view==='compare'&&shownComparison?[...new Map(shownComparison.records.flatMap(f=>[f.left,f.right].flatMap((s,i)=>decisionItems(s).map(item=>({...item,key:`${i}:${item.key}`,runLabel:i===0?'A':'B'})))).map(item=>[item.key,item])).values()]:[],[view,shownComparison]);
  const feed=view==='compare'?pairFeed:replay?.feed??data.feed;
  const shownPolicy=shown?.policy??policy;
  const warnings=shownPolicy==='ml'?[...new Set((shown?.decision?.recommendations??[]).filter(safetyOverride).map(r=>r.train_id))]:[];
  const seek=(index:number)=>{if(busy||!records.length)return;controlAdapter.seek<ReplayFrame|PairFrame>(records,index);setPlaying(false);setCursor(index);setHovered(null);};
  const returnLive=()=>{setPlaying(false);setCursor(null);};
  const setView=(next:View)=>{if((view==='compare')!==(next==='compare')){setPlaying(false);setCursor(null);}setHovered(null);setViewState(next);};
  const togglePlayback=()=>{if(busy&&!playing)return;if(!shown)return;if(cursor===records.length-1&&cursor!==null)setCursor(0);setPlaying(p=>!p);};
  const step=()=>cursor!==null?seek(Math.min(records.length-1,cursor+1)):void command('advance',{minutes:1});
  const changePolicy=(next:Policy)=>{if(replaying||view==='compare')return;if(data.snapshot)void command('decide',{policy:next});else setPolicy(next);};
  const focusTrain=(id:string)=>{
    setSelected(id);setHovered(null);setFocusToken(n=>n+1);
    const train=shown?.trains.find(t=>t.train_id===id);
    const section=train?.current_section??shown?.yard?.platforms.find(p=>p.train_id===id)?.section;
    if(section)setSectionId(section);
  };
  const recordDisruptions=(next:Disruption[],marker:TimelineMarker)=>{
    if(view==='compare')setComparison(previous=>previous?{...previous,records:[...previous.records,{left:previous.left,right:previous.right,error:previous.error,disruptions:next,markers:[marker]}]}:previous);
    else setData(previous=>previous.snapshot?{...previous,records:[...previous.records,{snapshot:previous.snapshot,disruptions:next,markers:[marker]}]}:previous);
  };
  const inject=(kind:DisruptionKind,target?:{sectionId:string;platform:number;trainId:string})=>{
    if(!shown||busy||replaying)return false;
    try {
      const selectedPlatform=shown.yard?.platforms.find(p=>p.train_id===selected);
      const event=controlAdapter.inject(shown,kind,target??{sectionId,platform:selectedPlatform?.platform??1,trainId:selected??shown.trains[0]?.train_id??''});
      if(kind==='track-block'&&!network?.sections.some(s=>s.section_id===event.sectionId))throw new Error('Choose a backend track section.');
      if(kind==='track-block')setSectionId(event.sectionId);
      if(kind==='signal-failure'){const section=shown.yard?.platforms.find(p=>p.platform===event.platform)?.section;if(section)setSectionId(section);}
      if(kind==='breakdown'||kind==='departure-delay')focusTrain(event.trainId);
      if(kind==='track-block'&&view==='station'&&!network?.sections.some(s=>s.section_id===event.sectionId&&(s.from_station===shown.station||s.to_station===shown.station)))setViewState('network');
      recordDisruptions([...disruptions,event],{kind:'disruption',label:`CLIENT MOCK · ${disruptionNames[kind]} · ${kind==='track-block'?event.sectionId:kind==='signal-failure'?`P${event.platform}`:kind==='fog'||kind==='rush-hour'?'preview':event.trainId}`,source:'client-mock'});return true;
    } catch(e){setError(e instanceof Error?e.message:'Invalid disruption target.');return false;}
  };
  const condition=(kind:DisruptionKind,enabled:boolean)=>{if(!shown||busy||replaying)return;if(enabled)inject(kind);else recordDisruptions(disruptions.filter(d=>d.kind!==kind),{kind:'disruption',label:`CLIENT MOCK · ${disruptionNames[kind]} cleared`,source:'client-mock'});};
  const clearDisruptions=()=>{if(shown&&!busy&&!replaying)recordDisruptions([],{kind:'disruption',label:'CLIENT MOCK · all preview conditions cleared',source:'client-mock'});};

  useEffect(()=>{
    const handler=(event:KeyboardEvent)=>{
      if(event.defaultPrevented||event.repeat||event.ctrlKey||event.metaKey||event.altKey||document.querySelector('dialog[open]'))return;
      const target=event.target as HTMLElement|null;
      if(target?.closest('input,select,textarea,button,a,[contenteditable=true],[role=button]'))return;
      if(event.code==='Space'){event.preventDefault();togglePlayback();}
      else if(['1','2','3'].includes(event.key)){event.preventDefault();setView((['station','section','network'] as const)[Number(event.key)-1]);}
      else if(event.key==='['||event.key===']'){event.preventDefault();setSpeed(s=>Math.max(1,Math.min(6,s+(event.key===']'?1:-1))));}
    };
    window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler);
  });
  return {network,snapshot:shown,scene,history:replay?.history??data.history,events:replay?.events??data.events,feed,session:data.session,policy:shownPolicy,station,playing,speed,busy,error,view,selected,hovered,sectionId,focusToken,layers,warnings,
    comparison:shownComparison,records,cursor,replaying,disruptions,mlActive:view==='compare'?!!shownComparison?.policies.includes('ml'):shownPolicy==='ml',
    connect,command,changePolicy,focusTrain,setPlaying,setSpeed,setView,setHovered,setSectionId,setLayers,togglePlayback,step,seek,returnLive,inject,condition,clearDisruptions};
}
const Context=createContext<ReturnType<typeof useControlState>|null>(null);
export function ControlProvider({children}:{children:ReactNode}){const store=useControlState();return <Context.Provider value={store}>{children}</Context.Provider>;}
export function useControl(){const store=useContext(Context);if(!store)throw new Error('Control room components need ControlProvider.');return store;}
