"""Evalúa reglas locales de DEMO; NO certifica resultados con STT/LLM/TTS reales."""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.agent import respond,Session
from src.tools import check_contact_policy
DATA=json.loads((ROOT/'data/test_scenarios.json').read_text(encoding='utf-8'))
OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
report=[]
for item in DATA:
    if item['execution']=='outbound':
        r=check_contact_policy(consented=True,do_not_call=True,local_hour=14)
        response='DNC: contacto bloqueado' if not r['allowed'] and r['reason']=='DNC' else 'FALLO'
        used=['check_contact_policy']; elapsed=0.; outcome=r['reason']=='DNC'
    else:
        ses=Session();used=[];outcome=False
        for utterance in item['turns']:
            answer,ses=respond(utterance,ses,mode='DEMO')
            used.extend(e['name'] for e in answer.tools)
        response=answer.text;elapsed=answer.elapsed_ms
    expected_tool=item['expected_tool']
    tool_ok=expected_tool is None or expected_tool in used
    text_ok=item['expected_text'].lower() in response.lower()
    success=bool(tool_ok and text_ok and (item['execution']!='outbound' or outcome))
    report.append({'id':item['id'],'scenario':item['scenario'],'group':item['group'],'register':item['register'],
                   'execution':item['execution'],'passes_auto_rules':success,'expected_tool':expected_tool or '',
                   'tools_observed':';'.join(used),'text_rule_ok':text_ok,'tool_rule_ok':tool_ok,
                   'demo_latency_ms_last_turn':elapsed,'tokens_real': '', 'actual_api_cost_usd':'',
                   'evidence_type':'deterministic_offline_demo', 'manual_review_status':'PENDIENTE',
                   'response_abridged':response[:200]})
with (OUT/'demo_evaluation_36.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=report[0].keys());w.writeheader();w.writerows(report)
subgroups=[]
for field in ('scenario','group','register','execution'):
    vals=sorted({str(r[field]) for r in report})
    for v in vals:
        one=[r for r in report if str(r[field])==v]
        subgroups.append({'dimension':field,'value':v,'n':len(one),'auto_rules_passed':sum(r['passes_auto_rules'] for r in one),
                          'auto_rule_pass_rate_pct':round(100*sum(r['passes_auto_rules'] for r in one)/len(one),2),
                          'scope':'Reglas deterministas offline, NO voz ni LLM en vivo'})
with (OUT/'subgroups_demo.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=subgroups[0].keys());w.writeheader();w.writerows(subgroups)
meta={'generated_utc':datetime.now(timezone.utc).isoformat(),'total':len(report),'passed':sum(r['passes_auto_rules'] for r in report),
      'failed':[r['id'] for r in report if not r['passes_auto_rules']],
      'evaluation_scope':'DEMO offline: regla de texto + evento de herramienta. No evalúa audio, WER, Anthropic, Deepgram, Azure ni desempeño comercial real.',
      'limitations':['Casos sintéticos predefinidos','No mide generalización, sesgos demográficos ni precisión de LLM en vivo',
                     'Tiempos de CPU no comparables con latencia de servicios externos','Costo real de API no estimable sin credenciales y consumo.']}
(OUT/'summary_demo.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(f"DEMO OFFLINE: {meta['passed']}/{meta['total']} reglas aprobadas. Fallidas: {meta['failed']}")
