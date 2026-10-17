from swarm_memory.risk import classify


def test_clinical_key_floors_at_high():
    result = classify(fact_key="genome.caller", declared_floor=None, action=None, multi_role=False, has_prior=False, model_class=None)
    assert result.final_class == "high"
    assert result.bar == 0.92


def test_model_cannot_lower_a_clinical_key():
    result = classify(fact_key="clinical.marker", declared_floor=None, action=None, multi_role=False, has_prior=False, model_class="low")
    assert result.final_class == "high"
    assert result.bar == 0.92


def test_model_raise_is_one_step():
    result = classify(fact_key="stack.web", declared_floor=None, action=None, multi_role=False, has_prior=False, model_class="critical")
    assert result.final_class == "high"
    assert result.bar == 0.92


def test_prior_binding_raises_to_high():
    result = classify(fact_key="style.quote", declared_floor="low", action=None, multi_role=False, has_prior=True, model_class=None)
    assert result.final_class == "high"


def test_publish_action_is_critical():
    result = classify(fact_key="note", declared_floor=None, action="publish", multi_role=False, has_prior=False, model_class=None)
    assert result.final_class == "critical"
    assert result.bar == 0.97


def test_declared_low_stays_low_without_a_raise():
    result = classify(fact_key="style.quote", declared_floor="low", action=None, multi_role=False, has_prior=False, model_class=None)
    assert result.final_class == "low"
    assert result.bar == 0.60
