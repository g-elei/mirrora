# in tests/test_validator.py
def test_rejects_wildcard_addresses():
    bad = {"id": "p_test", "themes": ["time"],
           "addresses": ["envy"], "expresses": []}
    from scripts.validate_corpus import validate_passage
    assert validate_passage(bad), "validator should reject envy backed only by 'time'"