import {test} from 'node:test';
import assert from 'node:assert/strict';
import {yardPose,arrivalPose} from '../app/yard-motion.ts';
import {stationState,trainLabel,delayColor} from '../app/station-state.ts';
import {readFileSync} from 'node:fs';

test('train poses follow the drawn tracks continuously and never overshoot the confirmed progress',()=>{
  for(let platform=1;platform<=4;platform++) {
    const startY=125+(platform-1)*85;
    assert.deepEqual(yardPose(0,platform,170),{x:405,y:startY,angle:0,visible:true});
    for(const boundary of [.35/3,.65/3]) {
      const before=yardPose(boundary-1e-8,platform,170), after=yardPose(boundary+1e-8,platform,170);
      assert.ok(Math.hypot(before.x-after.x,before.y-after.y)<.001);
      assert.ok(Math.abs(before.angle-after.angle)<.001);
    }
    let lastX=405;
    for(let step=0;step<=100;step++) {
      const pose=yardPose(step/300,platform,170);
      assert.ok(Number.isFinite(pose.angle));
      assert.ok(pose.x>=lastX-1e-8 && pose.x<=1050);
      lastX=pose.x;
    }
    assert.equal(yardPose(1/3,platform,170).visible,false);
    assert.deepEqual(yardPose(1,platform,170),yardPose(1/3,platform,170));
    assert.deepEqual(yardPose(-1,platform,170),yardPose(0,platform,170));
  }
});

test('arrival meets the platform track without a jump',()=>{
  for(let platform=1;platform<=4;platform++) {
    assert.deepEqual(arrivalPose(0,platform),yardPose(0,platform,170));
    assert.equal(arrivalPose(-1,platform).x,-150);
    assert.ok(arrivalPose(-.5,platform).x<arrivalPose(0,platform).x);
  }
});

test('real advance response preserves names, assignments, aspects and outside selection IDs',()=>{
  const response=JSON.parse(readFileSync(new URL('./advance-sample.json',import.meta.url),'utf8'));
  const scene=stationState(response);
  assert.equal(scene.time,response.time);
  assert.deepEqual(scene.events,response.events);
  assert.equal(trainLabel(response.trains.find(t=>t.train_id==='T022')),'Gita Jayanti Express · T022');
  assert.deepEqual(scene.signals,response.yard.platforms.map(p=>({platform:p.platform,aspect:p.aspect})));
  for(const t of scene.trains) {
    assert.equal(t.platform,response.yard.assignments[t.id]??null);
    assert.equal(t.outside,response.yard.outside.includes(t.id));
    assert.equal(t.departing,response.yard.platforms.some(p=>p.train_id===t.id&&p.locked));
  }
  assert.equal(scene.trains.find(t=>t.id==='T012').destination,'BTE');
  assert.equal(scene.trains.find(t=>t.id==='T006').destination,'PWL');
  const skipped=structuredClone(response);
  skipped.time+=5;skipped.yard.platforms.forEach(p=>{if(p.train_id==='T012')p.train_id=null});
  delete skipped.yard.assignments.T012;
  assert.equal(stationState(skipped,scene).trains.find(t=>t.id==='T012').platform,2);
  assert.equal(stationState({...response,yard:null}).platforms.length,0);
  assert.equal(delayColor(0),'#4e8b69');assert.equal(delayColor(5),'#b28235');assert.equal(delayColor(5.1),'#bd6650');
});

test('section occupancy survives platform release and clears only with the backend snapshot',()=>{
  const response=JSON.parse(readFileSync(new URL('./advance-sample.json',import.meta.url),'utf8'));
  const [section,occupant]=Object.entries(response.occupancy)[0];
  assert.ok(occupant);
  const initial=stationState(response);
  const refilled=structuredClone(response);
  refilled.time+=1;
  delete refilled.yard.assignments[occupant];
  refilled.yard.platforms.forEach(p=>{if(p.train_id===occupant){p.train_id=null;p.locked=false;}});
  const scene=stationState(refilled,initial);
  assert.equal(scene.platforms.some(p=>p.train_id===occupant),false);
  assert.equal(scene.occupancy[section],occupant);
  const cleared=structuredClone(refilled);
  delete cleared.occupancy[section];
  assert.equal(stationState(cleared,scene).occupancy[section],undefined);
  assert.equal(stationState(response).occupancy[section],occupant);
});
