import {test} from 'node:test';
import assert from 'node:assert/strict';
import {yardPose} from '../app/yard-motion.ts';

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
