from app import calculate_fee

def test_fee_boundaries():
    assert calculate_fee(30) == 0
    assert calculate_fee(31) == 50
    assert calculate_fee(120) == 50
    assert calculate_fee(121) == 100
    assert calculate_fee(360) == 100
    assert calculate_fee(361) == 300
