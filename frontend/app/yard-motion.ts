// Exact cubic Bezier equivalents of the SVG track paths.
export function arrivalPose(progress:number,platform:number) {
  return {x:-150+555*Math.max(0,Math.min(1,progress+1)),y:125+(platform-1)*85,angle:0,visible:true};
}
export function yardPose(progress: number, platform: number, exitY: number) {
  const v = Math.max(0, Math.min(1, progress * 3));
  const startY = 125 + (platform - 1) * 85;
  if (v < .35) return {x: 405 + v / .35 * 245, y: startY, angle: 0, visible: true};
  const firstCurve = v < .65;
  const q = firstCurve ? (v - .35) / .3 : (v - .65) / .35;
  const r = 1 - q;
  const [x0, x1, x2, x3] = firstCurve ? [650, 740, 760, 830] : [830, 900, 900, 1050];
  const fromY = firstCurve ? startY : 250;
  const toY = firstCurve ? 250 : exitY;
  return {
    x: r*r*r*x0 + 3*r*r*q*x1 + 3*r*q*q*x2 + q*q*q*x3,
    y: fromY + (toY - fromY) * q*q*(3 - 2*q),
    angle: Math.atan2(6*q*r*(toY - fromY), 3*r*r*(x1-x0) + 6*r*q*(x2-x1) + 3*q*q*(x3-x2)) * 180 / Math.PI,
    visible: v < 1,
  };
}
