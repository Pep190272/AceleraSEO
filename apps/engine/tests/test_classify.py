from aceleraseo.domain.classify import classify
from aceleraseo.domain.models import (
    AuthorityBand,
    BusinessType,
    Maturity,
    SiteSnapshot,
)


def test_new_low_authority_site():
    p = classify(SiteSnapshot(ranking_query_count=10, total_pages=5))
    assert p.maturity is Maturity.NEW
    assert p.authority_band is AuthorityBand.LOW


def test_established_high_authority_site():
    p = classify(SiteSnapshot(ranking_query_count=900, total_pages=400))
    assert p.maturity is Maturity.ESTABLISHED
    assert p.authority_band is AuthorityBand.HIGH


def test_ecommerce_detected_over_other_types():
    p = classify(SiteSnapshot(ranking_query_count=100, total_pages=50,
                              ecommerce_pages=20, blog_pages=40))
    assert p.type is BusinessType.ECOMMERCE


def test_local_business_sets_geo_relevant():
    p = classify(SiteSnapshot(ranking_query_count=20, has_local_signals=True))
    assert p.type is BusinessType.LOCAL
    assert p.is_geo_relevant is True


def test_blog_when_articles_dominate():
    p = classify(SiteSnapshot(ranking_query_count=100, total_pages=10, blog_pages=8))
    assert p.type is BusinessType.BLOG


def test_corporate_is_the_fallback():
    p = classify(SiteSnapshot(ranking_query_count=100, total_pages=10, blog_pages=1))
    assert p.type is BusinessType.CORPORATE
