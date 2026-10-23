"""Reproducible token scenario; CLI counters are not subscription credit or API invoices."""
import json,pathlib
R=pathlib.Path(__file__).resolve().parents[1]
def estimate():
    folder=R/'data/model-reviews/v0.3.0';runs=[]
    for name in ['gemini.round1.json','gemini.round2.json','gemini.round3.json','claude.round1.json']:
        item=json.loads((folder/name).read_text(encoding='utf-8'));e=item['execution'];u=e['usage']
        runs.append({'model':item['model'],'conversation_id':e['conversation_id'],'input':u['input_tokens'],'output':u['output_tokens'],'thinking':u.get('thinking_tokens',0)})
    assert len({r['conversation_id'] for r in runs})==len(runs)
    # Gemini API price for this CLI-only model is unverified: GPT rates are an explicit proxy, not a claimed Gemini bill.
    gem=[r for r in runs if r['model'].startswith('gemini')];claude=[r for r in runs if r['model'].startswith('claude')]
    def cost(items,ir,outr,include_thinking=False):return sum(r['input']*ir+(r['output']+(r['thinking'] if include_thinking else 0))*outr for r in items)/1e6
    measured_low=cost(gem,2,10)+cost(claude,5,25)
    measured_high=cost(gem,2,10,True)+cost(claude,5,25,True)
    scale=31000/31
    report={'date':'2026-10-23','scenario_verses':31000,'languages':['ko','en','es'],'observed_chapter_verses':31,'claude_hard_verse_reviews':7,'distinct_cli_runs':runs,'observed_cli_cash_charged_by_project':0,'cli_to_api_cash_equivalence':'not valid; counterfactual only','gemini_pricing_proxy':'GPT-6.1 Sol standard $2/M input, $10/M output; no Gemini API price asserted','claude_counterfactual_rates':'Opus 4.6 $5/M input, $25/M output','thinking_ambiguity':'Lower bound uses reported output only; upper adds thinking because CLI counter inclusion is not independently verified','chapter_external_model_counterfactual_usd':[round(measured_low,4),round(measured_high,4)],'full_bible_external_calls_counterfactual_usd':[round(measured_low*scale),round(measured_high*scale)],'gpt_editorial_assumed_per_31_verse_usd':[0.19,0.42],'full_three_language_review_budget_usd':[2000,5000],'single_pass_draft_scenario_usd':[200,600],'excludes':['human specialist review','direct full manuscript collation','image/data licensing','new language additions','Greek New Testament pipeline development','tax and currency conversion'],'sources':['https://developers.openai.com/api/docs/models/gpt-6.1-sol','https://platform.claude.com/docs/en/about-claude/pricing'],'warning':'Scenario extrapolation, not an invoice or fixed quote. Subscription quota is account-shared and cannot be converted from these token counters.'}
    (R/'automation/cost-estimate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:report[k] for k in ['chapter_external_model_counterfactual_usd','full_bible_external_calls_counterfactual_usd','full_three_language_review_budget_usd']}))
if __name__=='__main__':estimate()
