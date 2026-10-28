'use client';
import {useMemo} from 'react';
import {ArrowRight,Check,ShieldAlert,X} from 'lucide-react';
import {trainLabel} from '../station-state';
import {policies,safetyOverride} from './control-data';
import {useControl} from './control-store';

export default function DecisionPanel() {
  const {feed,snapshot,policy,selected,focusTrain,mlActive,view}=useControl();
  const items=useMemo(()=>[...feed].reverse().sort((a,b)=>b.time-a.time),[feed]);
  return <aside className="control-decisions" aria-label="AI and policy decision feed">
    <div className="control-panel-heading"><div><span className="control-kicker">DECISION FEED</span><h2>Reason behind the move</h2></div>{snapshot&&mlActive&&<span className="control-ml">ML</span>}</div>
    <p className="control-panel-note">{view==='compare'?'Paired runs · A / B':snapshot?policies[policy]:'Load a queue to start.'}<br/>Recommendations, safety validation, execution.</p>
    <div className="control-feed" aria-live="polite" aria-relevant="additions">
      {!items.length&&<div className="control-feed-empty"><ShieldAlert size={27}/><h3>No decisions yet</h3><p>Load a queue, then analyze or play. Only backend decisions appear here.</p></div>}
      {items.map(item=>{
        const rec=item.recommendation,train=snapshot?.trains.find(t=>t.train_id===rec.train_id);
        const override=item.policy==='ml'&&safetyOverride(rec),failed=rec.checks?.filter(c=>!c.passed)??[];
        const action=rec.executed_action??rec.final_action;
        const probability=item.policy==='ml'&&rec.ml_action?rec.probabilities?.[rec.ml_action]:undefined;
        return <article key={item.key} className={'control-decision '+(selected===rec.train_id?'is-selected ':'')+(override&&mlActive?'model-warning':'')}>
          <div className="control-card-meta"><span>{item.runLabel?`RUN ${item.runLabel} · `:''}{item.time.toFixed(2)} sim min</span><span className={'control-action '+(action==='RELEASE'?'release':'hold')}>{action}</span></div>
          <button className="control-focus-train" aria-pressed={selected===rec.train_id} onClick={()=>focusTrain(rec.train_id)}>{train?trainLabel(train):rec.train_id}<ArrowRight size={15}/></button>
          <div className="control-card-policy">{policies[item.policy]}{item.policy==='ml'&&mlActive&&<span className="control-ml">ML</span>}</div>
          <p className="control-confidence">{probability===undefined?'Confidence not reported by this policy.':`${rec.ml_action} confidence: ${(probability*100).toFixed(1)}%`} {probability!==undefined&&<small>Model probability; not a safety guarantee.</small>}</p>
          {override&&<div className={'control-override '+(mlActive?'is-model':'')} role="note"><ShieldAlert size={16}/><div><strong>Safety override · model RELEASE held</strong><span>Failed: {failed.map(c=>c.name).join('; ')}</span></div></div>}
          <p>{rec.execution_reason||rec.conflict_reason||rec.reason}</p>
          <ul className="control-checks">{rec.checks?.map((check,i)=><li key={i} title={check.reason}><span className={check.passed?'check-pass':'check-blocked'}>{check.passed?<Check size={14}/>:<X size={14}/>}</span><span>{check.name}<small>{check.reason}</small></span></li>)}</ul>
          {!rec.checks?.length&&<p className="control-missing">Safety checklist not returned.</p>}
          <small className="control-card-source">{rec.executed_action?'Execution recorded':'Recommendation only'} · {rec.next_section}</small>
        </article>;
      })}
    </div>
  </aside>;
}

