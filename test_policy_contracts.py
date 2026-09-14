"""Execute the separately authored synthetic policy contracts."""
from challenge_suite import corpus
from decision_reporting import decisions

cases=corpus()
records=decisions([c['probabilities'] for c in cases],
                  [c['features'] for c in cases],.36,.62)
failed=[c['id'] for c,r in zip(cases,records) if c['expected']!=r['final_policy_label']]
assert not failed, failed
print(f'{len(cases)}/{len(cases)} synthetic policy contracts pass')
