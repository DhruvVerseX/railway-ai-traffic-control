import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {mergeEvents,decisionItems,safetyOverride,sectionPosition,sectionTrace,sectionThroughput,networkLayout,initialSignature,recordedView,previewTrain,decisionMarkers,comparisonStats,pairedAdvanceResult,activeDisruptions} from '../app/control/control-data.ts';

const fixture=JSON.parse(readFileSync(new URL('./advance-sample.json',import.meta.url),'utf8'));
const section={section_id:'S03',from_station:'PWL',to_station:'MTJ',distance_km:70};
const train={...fixture.trains.find(t=>t.train_id==='T006'),entry_time_min:0};
const snapshot={...fixture,trains:[train],policy:'ml',metrics:{}};

test('section projection respects direction, holds, readiness and unknown intervals',()=>{
  assert.equal(sectionPosition(snapshot,{...train,current_station:'MTJ',current_section:'S03',progress:.25},section,[]),52.5);
  assert.equal(sectionPosition(snapshot,{...train,current_station:'PWL',current_section:'S03',progress:.25},section,[]),17.5);
  assert.equal(sectionPosition(snapshot,{...train,status:'WAITING',current_section:null,current_station:'MTJ'},section,[]),70);
  assert.equal(sectionPosition(snapshot,{...train,entry_time_min:10},section,[]),null);
  assert.equal(sectionPosition(snapshot,{...train,current_section:'S04'},section,[]),null);
});

test('string-line preserves flat holds and exact crossings during coarse ticks, with gaps after leaving the section',()=>{
  const waiting={...train,status:'WAITING',current_section:null,current_station:'MTJ'};
  const history=[{...snapshot,time:0,trains:[waiting]},{...snapshot,time:1,trains:[waiting]},
    {...snapshot,time:5,trains:[{...train,current_section:'S02',current_station:'PWL'}]}];
  const events=[{event:'SECTION_ENTERED',train_id:train.train_id,section_id:'S03',from_station:'MTJ',time_min:2},
    {event:'SECTION_COMPLETED',train_id:train.train_id,section_id:'S03',station_id:'PWL',time_min:4}];
  assert.deepEqual(sectionTrace(history,events,train.train_id,section),[
    {time:0,distance:70},{time:1,distance:70},{time:2,distance:70},{time:4,distance:0},{time:5,distance:null},
  ]);
  const merged=mergeEvents(events,events);
  assert.equal(merged.length,2);
  assert.equal(sectionThroughput(merged,'S03',0,5),12);
  assert.equal(sectionThroughput(merged,'S04',0,5),0);
  assert.equal(sectionThroughput(merged,'S03',5,5),null);
});

test('safety overrides require a blocked model RELEASE, including execution rechecks',()=>{
  const rec={train_id:train.train_id,ml_action:'RELEASE',final_action:'HOLD',checks:[{name:'Platform, signal and exit switch',passed:false,reason:'Signal held at red.'}]};
  assert.equal(safetyOverride(rec),true);
  assert.equal(safetyOverride({...rec,ml_action:'HOLD'}),false);
  assert.equal(safetyOverride({...rec,checks:[{passed:true}]}),false);
  assert.equal(safetyOverride({...rec,final_action:'RELEASE',executed_action:'HOLD'}),true);
  const items=decisionItems({...snapshot,policy:'fifo',decision:{time_min:2,policy:'fifo',recommendations:[{...rec,ml_action:undefined}]}});
  assert.equal(items[0].policy,'fifo');
});

test('network layout derives finite, distinct positions from connectivity, including disconnected stations',()=>{
  const graph={stations:['MTJ','PWL','BTE','ISOLATED'].map(station_code=>({station_code,station_name:station_code})),sections:[section,{section_id:'S04',from_station:'MTJ',to_station:'BTE',distance_km:33}]};
  const nodes=networkLayout(graph,'MTJ');
  assert.equal(nodes.length,4);
  assert.equal(new Set(nodes.map(n=>`${n.x},${n.y}`)).size,4);
  assert.ok(nodes.every(n=>Number.isFinite(n.x)&&Number.isFinite(n.y)));
  assert.ok(nodes.find(n=>n.station_code==='MTJ').x<nodes.find(n=>n.station_code==='PWL').x);
});

test('paired initial-condition verification ignores controller and session, but detects changed traffic',()=>{
  assert.equal(initialSignature({...snapshot,session:'A',policy:'fifo'}),initialSignature({...snapshot,session:'B',policy:'ml'}));
  assert.notEqual(initialSignature(snapshot),initialSignature({...snapshot,trains:[{...train,entry_time_min:7}]}));
  assert.notEqual(initialSignature(snapshot),initialSignature({...snapshot,occupancy:{S03:'unexpected'}}));
});

test('client mock projection freezes only the preview, preserving backend truth',()=>{
  const frozen={...train,progress:.2,current_station:'MTJ'};
  const disruption={id:'local',kind:'breakdown',time:1,source:'client-mock',sectionId:'S03',platform:3,trainId:train.train_id,frozen};
  const current={...train,progress:.8};
  assert.equal(previewTrain(current,[disruption]).progress,.2);
  assert.equal(current.progress,.8);
  assert.equal(previewTrain(current,[]),current);
});

test('local replay restores mock conditions at exact frames, excluding future receipts and events',()=>{
  const first={...snapshot,time:0,events:[],decision:null};
  const mock={id:'fog',kind:'fog',time:0,source:'client-mock',sectionId:'S03',platform:1,trainId:train.train_id};
  const future={...snapshot,time:2,events:[{event:'SECTION_COMPLETED',train_id:train.train_id,section_id:'S03',time_min:2}]};
  const records=[{snapshot:first,disruptions:[],markers:[]},{snapshot:first,disruptions:[mock],markers:[]},{snapshot:future,disruptions:[],markers:[]}];
  assert.equal(recordedView(records,0).disruptions.length,0);
  assert.equal(recordedView(records,1).disruptions[0].kind,'fog');
  assert.equal(recordedView(records,1).events.length,0);
  assert.equal(recordedView(records,2).events.length,1);
  assert.equal(recordedView(records,2).disruptions.length,0);
  assert.throws(()=>recordedView(records,-1));assert.throws(()=>recordedView(records,3));
});

test('timeline and comparison include holds, overrides, rejection and unfinished journeys without claiming deadlock',()=>{
  const rec={train_id:train.train_id,ml_action:'RELEASE',final_action:'RELEASE',executed_action:'HOLD',reason:'Signal held',checks:[{name:'Execution recheck',passed:false,reason:'Signal held'}]};
  const blocked={...snapshot,time:11,events:[],decision:{time_min:11,policy:'ml',recommendations:[rec]}};
  assert.deepEqual(decisionMarkers(blocked).map(m=>m.kind),['hold','override']);
  const stats=comparisonStats([{...blocked,time:0},blocked,blocked]);
  assert.equal(stats.holds,1);assert.equal(stats.overrides,1);assert.equal(stats.rejected,1);assert.equal(stats.unfinished,1);assert.equal(stats.stalled,true);
  assert.equal('deadlocked' in stats,false);
});

test('paired steps retain session IDs and pause on partial failure instead of presenting aligned results',()=>{
  const a={...snapshot,session:'A',time:0},b={...snapshot,session:'B',time:0};
  const success={status:'fulfilled',value:{...snapshot,time:1}};
  const aligned=pairedAdvanceResult(a,b,[success,success]);
  assert.equal(aligned.left.session,'A');assert.equal(aligned.right.session,'B');assert.equal(aligned.error,undefined);
  const failed=pairedAdvanceResult(a,b,[success,{status:'rejected',reason:new Error('ngrok unreachable')}]);
  assert.equal(failed.left.time,1);assert.equal(failed.right.time,0);
  assert.match(failed.error,/B: ngrok unreachable/);assert.match(failed.error,/clocks diverged/);
});

test('mock departure delay expires after five sim minutes and reappears when replaying its window',()=>{
  const delay={id:'mock',kind:'departure-delay',time:2,source:'client-mock'};
  assert.equal(activeDisruptions([delay],1).length,0);
  assert.equal(activeDisruptions([delay],2).length,1);
  assert.equal(activeDisruptions([delay],6).length,1);
  assert.equal(activeDisruptions([delay],7).length,0);
  assert.equal(activeDisruptions([delay],3).length,1);
});
