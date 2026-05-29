from aceleraseo.domain.models import (
    AuthorityBand,
    BusinessProfile,
    BusinessType,
    Keyword,
    Maturity,
)
from aceleraseo.domain.strategy import score_keyword


def _profile(**kw):
    base = dict(
        type=BusinessType.LOCAL,
        maturity=Maturity.NEW,
        authority_band=AuthorityBand.LOW,
        is_geo_relevant=True,
    )
    base.update(kw)
    return BusinessProfile(**base)


def test_new_local_site_prefers_low_difficulty_longtail():
    longtail = Keyword(term="fontanero urgente gracia barcelona", search_volume=200,
                       difficulty=12, intent="transactional")
    head = Keyword(term="fontanero", search_volume=40000, difficulty=85,
                   intent="transactional")
    p = _profile()
    assert score_keyword(longtail, p).opportunity > score_keyword(head, p).opportunity


def test_authority_gap_penalises_low_authority():
    kw = Keyword(term="seo", search_volume=10000, difficulty=70, intent="commercial")
    low = score_keyword(kw, _profile(authority_band=AuthorityBand.LOW)).opportunity
    high = score_keyword(kw, _profile(authority_band=AuthorityBand.HIGH,
                                      maturity=Maturity.ESTABLISHED)).opportunity
    assert high > low
