import { ArrowRight, Check, X, Database, ShieldCheck } from "lucide-react";
import {trainLabel} from './station-state';
import {animate, createScope, stagger} from 'animejs';
import {useEffect, useRef} from 'react';

export type Recommendation = {
  train_id: string;
  final_action: string;
  reason: string;
  conflict_reason?: string;
  next_section: string;
  ml_action?: string;
  probabilities?: Record<string, number>;
  features?: Record<string, string | number>;
  checks?: { name: string; passed: boolean; reason: string }[];
  executed_action?: string;
  execution_reason?: string;
};
type Metrics = {
  departed: number;
  cleared: number;
  queue: number;
  throughput_per_hour: number;
  waiting_min: number;
};
export type Decision = {
  time_min: number;
  policy?: string;
  controller?: string;
  model_file?: string | null;
  recommendations?: Recommendation[];
  selected_action?: Recommendation;
  selected_actions?: Recommendation[];
  execution?: {
    reason: string;
    executed?: boolean;
    released?: string[];
    events?: object[];
  };
  metrics_before?: Metrics;
  metrics_after?: Metrics;
  steps?: Decision[];
};
export type BackendReceipt = {
  service: string;
  request_id: string;
  method: string;
  path: string;
  responded_at: string;
};
export type MovementEvent = {
  event: string;
  train_id?: string;
  section_id?: string;
  from_station?: string;
  to_station?: string;
  time_min: number;
};

export default function DecisionEvidence({
  decision,
  backend,
  policy,
  trains,
  selected,
  onSelect,
  metrics,
  events,
}: {
  decision: Decision | null;
  backend?: BackendReceipt;
  policy: string;
  trains: { train_id: string; train_name: string }[];
  selected: string | null;
  onSelect: (id: string) => void;
  metrics: { departed: number; queue: number; throughput_per_hour: number };
  events: MovementEvent[];
}) {
  const steps = decision ? [...(decision.steps || []), decision] : [];
  const trace =
    [...steps].reverse().find((step) => step.execution?.executed) || decision;
  const recommendations = trace?.recommendations || [];
  const rec =
    selected ? recommendations.find((item) => item.train_id === selected) : recommendations[0];
  const safetyRows=rec?.checks?.flatMap(check=>{
    const labels=check.name==='Section occupancy, direction and headway'
      ? ['Occupancy','Direction','Headway']
      : check.name==='Platform, signal and exit switch'
        ? ['Platform availability','Signal / switch'] : [check.name];
    return labels.map(name=>({...check,name,grouped:labels.length>1}));
  })??[];
  const held=rec?.executed_action==='HOLD'||rec?.final_action!=='RELEASE';
  const verdict=held?`Held: ${rec?.execution_reason||rec?.conflict_reason||rec?.reason||'waiting for a safe move'}`:'Permitted: movement checks clear';
  const controller =
    trace?.controller ||
    (policy === "ml"
      ? "Random Forest V2"
      : policy === "fifo"
        ? "FIFO"
        : "Shortest-clearance heuristic");
  const executed = trace?.execution !== undefined;
  const movement = [...events]
    .reverse()
    .find((event) => event.event === "SECTION_ENTERED");
  const panel = useRef<HTMLElement>(null);
  useEffect(()=>{
    if(!rec)return;
    const scope=createScope({root:panel,mediaQueries:{reduceMotion:'(prefers-reduced-motion: reduce)'}}).add(self=>{
      if(self&&!self.matches.reduceMotion) animate('.decision-pipeline article',{
        opacity:[.45,1],y:[10,0],delay:stagger(75),duration:400,ease:'outQuad',
      });
    });
    return()=>scope.revert();
  },[rec?.train_id,trace?.policy]);
  return (
    <section ref={panel} className="backend-evidence" aria-labelledby="evidence-title">
      <div className="evidence-heading">
        <div>
          <span className="chapter-label">FROM INPUT TO MOVEMENT</span>
          <h2 id="evidence-title">The decision behind the animation.</h2>
        </div>
        <span className="backend-receipt">
          <Database size={15} />
          {backend
            ? "Response from Python backend"
            : "Waiting for backend response"}
        </span>
      </div>
      <p className="evidence-note">
        A simulation-based research prototype. Traffic state is processed in
        Python; this is not connected to live railway control systems.
      </p>
      <div className="evidence-summary">
        <span>
          Controller <b>{controller}</b>
        </span>
        <span>
          Departed <b>{metrics.departed}</b>
        </span>
        <span>
          Ready queue <b>{metrics.queue}</b>
        </span>
        <span>
          Station departures/hour{" "}
          <b>{metrics.throughput_per_hour.toFixed(2)}</b>
        </span>
      </div>
      {movement && (
        <p className="evidence-note">
          <b>Latest recorded movement:</b> {trains.find(t=>t.train_id===movement.train_id)?trainLabel(trains.find(t=>t.train_id===movement.train_id)!):movement.train_id} entered{" "}
          {movement.section_id} at {movement.time_min.toFixed(2)} simulated min.
          Source: backend event log.
        </p>
      )}
      {!trace ? (
        <p className="evidence-empty">
          Choose Analyze to send the queue to the backend. Dispatch applies
          permitted recommendations and records actual movements.
        </p>
      ) : (
        <>
          <div className="evidence-select">
            <label htmlFor="evidence-train">Inspect a train</label>
            <select
              id="evidence-train"
              value={selected || rec?.train_id || ""}
              disabled={!trains.length}
              onChange={(event) => onSelect(event.target.value)}
            >
              {trains.map((item) => (
                <option key={item.train_id} value={item.train_id}>
                  {trainLabel(item)}
                </option>
              ))}
            </select>
            <span>
              Decision at {trace.time_min.toFixed(2)} simulated min
              {trace !== decision ? " · latest dispatch in this update" : ""}
            </span>
          </div>
          {rec ? (
            <div className="decision-pipeline">
              <article>
                <span className="pipeline-step">01 / INPUT</span>
                <h3>Traffic state</h3>
                {rec.features ? (
                  <dl>
                    <div>
                      <dt>Train delay</dt>
                      <dd>{Number(rec.features.delay_min).toFixed(1)} min</dd>
                    </div>
                    <div>
                      <dt>Priority</dt>
                      <dd>{rec.features.priority}</dd>
                    </div>
                    <div>
                      <dt>Next section</dt>
                      <dd>{rec.next_section}</dd>
                    </div>
                    <div>
                      <dt>Section occupied</dt>
                      <dd>
                        {rec.features.next_section_occupied ? "Yes" : "No"}
                      </dd>
                    </div>
                    <div>
                      <dt>Competing trains</dt>
                      <dd>{rec.features.same_section_competitors}</dd>
                    </div>
                  </dl>
                ) : (
                  <p>
                    Next section: {rec.next_section}. This policy does not use
                    ML features.
                  </p>
                )}
              </article>
              <article>
                <span className="pipeline-step">02 / RECOMMENDATION</span>
                <h3>
                  {rec.ml_action
                    ? `Model: ${rec.ml_action}`
                    : `Policy: ${rec.final_action}`}
                </h3>
                {rec.probabilities ? (
                  <>
                    <p>
                      RELEASE probability{" "}
                      <strong>
                        {(rec.probabilities.RELEASE * 100).toFixed(1)}%
                      </strong>
                    </p>
                    <p className="evidence-note">
                      Model probability is not a safety guarantee.
                    </p>
                    <code>{trace.model_file}</code>
                  </>
                ) : (
                  <p>{controller} produced this recommendation.</p>
                )}
              </article>
              <article>
                <span className="pipeline-step">03 / SAFETY</span>
                <h3>
                  <ShieldCheck size={17} /> {verdict}
                </h3>
                <ul className="safety-checks">
                  {safetyRows.map((check, index) => (
                    <li key={index}>
                      <b
                        className={
                          check.passed ? "check-pass" : "check-blocked"
                        }
                      >
                        {check.passed ? (
                          <Check size={13} />
                        ) : (
                          <X size={13} />
                        )}
                        {check.name}
                      </b>
                      <span>
                        {check.grouped ? 'Shared group result' : check.reason}
                      </span>
                    </li>
                  ))}
                </ul>
                {!safetyRows.length&&<p>Safety checklist not returned by this policy.</p>}
                {[...new Set(safetyRows.filter(row=>row.grouped&&!row.passed).map(row=>row.reason))].map(reason=><p key={reason}>{reason}</p>)}
                <p className="evidence-note">Rows repeat two grouped backend verdicts: occupancy / direction / headway, and platform / signal / switch. Individual check results are not reported.</p>
              </article>
              <article>
                <span className="pipeline-step">04 / EXECUTION</span>
                <h3>
                  {executed
                    ? rec.executed_action === "RELEASE"
                      ? "Train released"
                      : "Train held"
                    : "Not executed yet"}
                </h3>
                <p>{rec.execution_reason || rec.reason}</p>
                {trace.metrics_before && trace.metrics_after && (
                  <p>
                    Station departures: {trace.metrics_before.departed}{" "}
                    <ArrowRight size={12} /> {trace.metrics_after.departed}
                  </p>
                )}
                {executed && rec.executed_action === "RELEASE" && (
                  <p className="check-pass">Movement recorded by simulator.</p>
                )}
              </article>
            </div>
          ) : (
            <p className="evidence-empty">
              No recommendation for the selected train in this decision. Select another train or analyze the current queue.
            </p>
          )}
        </>
      )}
      {backend && (
        <div className="request-receipt">
          <code>
            {backend.method} {backend.path}
          </code>
          <span>Request {backend.request_id}</span>
          <time dateTime={backend.responded_at}>
            {new Date(backend.responded_at).toLocaleString("en-IN", {
              timeZone: "Asia/Kolkata",
              hour12: false,
            })}{" "}
            IST
          </time>
        </div>
      )}
      <details className="evidence-raw">
        <summary>Inspect the backend response</summary>
        <pre>
          {JSON.stringify(
            { backend, policy, decision, metrics, events },
            null,
            2,
          )}
        </pre>
      </details>
    </section>
  );
}
