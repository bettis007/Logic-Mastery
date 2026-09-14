"""Separately authored policy-contract tests, not external scientific validation.

Fixed feature/probability inputs intentionally challenge the policy itself.
This file neither imports the original synthetic generator nor fits a model.
Expected outcomes derive from named policy contracts. Cases are not a blinded,
independently labeled real-world corpus and accuracy is not generalization.
"""
import itertools

FEATURES=('source_authority','direct_observation','reproducibility',
          'independent_corroboration','provenance_completeness',
          'explicit_simulation_label','narrative_symbolism','contradiction_score',
          'hazard_score','ambiguity_score','numeric_specificity','tamper_score',
          'authority_consent','uncertainty_disclosed','mechanism_defined',
          'metadata_integrity','unsupported_existence_claim')

def corpus():
    cases=[]
    def add(family,values,expected,prob=None):
        base=dict(source_authority=.95,direct_observation=.95,reproducibility=.95,
            independent_corroboration=.95,provenance_completeness=.95,
            explicit_simulation_label=0,narrative_symbolism=0,contradiction_score=0,
            hazard_score=0,ambiguity_score=0,numeric_specificity=.5,tamper_score=0,
            authority_consent=1,uncertainty_disclosed=1,mechanism_defined=.95,
            metadata_integrity=.95,unsupported_existence_claim=0)
        base.update(values)
        cases.append({'id':f'{family}-{len(cases):04d}','family':family,
            'features':[base[k] for k in FEATURES],
            'probabilities':prob or [.96,.01,.01,.01,.01], 'expected':expected})
    for authority,precision in itertools.product([0,.5,1],repeat=2):
        nuisance={'source_authority':authority,'numeric_specificity':precision}
        add('supported',nuisance,'ACCEPT')
        add('explicit_simulation',{**nuisance,'explicit_simulation_label':1,'direct_observation':.2},'SIMULATED')
        add('explicit_narrative',{**nuisance,'narrative_symbolism':1,'direct_observation':.2},'NARRATIVE')
        add('contradiction',{**nuisance,'contradiction_score':1},'QUARANTINE')
        add('tampered',{**nuisance,'tamper_score':1},'QUARANTINE')
        add('unauthorized_hazard',{**nuisance,'hazard_score':1,'authority_consent':0},'QUARANTINE')
        add('unsupported_existence',{**nuisance,'unsupported_existence_claim':1,'direct_observation':0},'QUARANTINE')
        add('weak_evidence',{**nuisance,'direct_observation':.1,'independent_corroboration':0},'QUALIFY')
        add('quarantine_priority',{**nuisance,'explicit_simulation_label':1,'narrative_symbolism':1,'direct_observation':.2,'tamper_score':1},'QUARANTINE')
    # Immediately below, exactly at, and immediately above fixed boundaries.
    for value in [.719999,.72,.720001]:
        add('tamper_boundary',{'tamper_score':value},'QUARANTINE' if value>=.72 else 'ACCEPT')
    for value in [.899999,.90,.900001]:
        add('contradiction_boundary',{'contradiction_score':value},'QUARANTINE' if value>=.90 else 'ACCEPT')
    for value in [.419999,.42,.420001]:
        add('corroboration_boundary',{'independent_corroboration':value},'QUALIFY' if value<.42 else 'ACCEPT')
    add('low_confidence',{},'QUARANTINE',[.24,.19,.19,.19,.19])
    add('low_confidence_qualify',{},'QUALIFY',[.19,.24,.19,.19,.19])
    return cases
