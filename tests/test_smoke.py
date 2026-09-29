import energy


def test_version_is_string():
    assert isinstance(energy.__version__, str)


def test_default_zone_is_german_bidding_zone():
    assert energy.DEFAULT_ZONE == "DE-LU"
