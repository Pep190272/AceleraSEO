"""Business classifier — pure rules over a SiteSnapshot. No I/O, fully testable.

This is the first half of the brain: before choosing keywords you must know WHO
you are. A brand-new local plumber and an established e-commerce need opposite
strategies. The output BusinessProfile drives keyword scoring in strategy.py.
"""
from __future__ import annotations

from .models import AuthorityBand, BusinessProfile, BusinessType, Maturity, SiteSnapshot


def _authority_band(snapshot: SiteSnapshot) -> AuthorityBand:
    # Ranking footprint is the honest authority proxy: a site that already ranks
    # for many queries has earned trust; raw page count does not.
    q = snapshot.ranking_query_count
    if q < 50:
        return AuthorityBand.LOW
    if q < 500:
        return AuthorityBand.MID
    return AuthorityBand.HIGH


def _maturity(snapshot: SiteSnapshot) -> Maturity:
    q = snapshot.ranking_query_count
    if q < 30:
        return Maturity.NEW
    if q < 300:
        return Maturity.GROWING
    return Maturity.ESTABLISHED


def _business_type(snapshot: SiteSnapshot) -> BusinessType:
    if snapshot.ecommerce_pages >= 1:
        return BusinessType.ECOMMERCE
    if snapshot.has_local_signals:
        return BusinessType.LOCAL
    # Mostly articles -> content/blog play; otherwise a brochure/corporate site.
    if snapshot.total_pages and snapshot.blog_pages > snapshot.total_pages * 0.5:
        return BusinessType.BLOG
    return BusinessType.CORPORATE


def classify(snapshot: SiteSnapshot) -> BusinessProfile:
    return BusinessProfile(
        type=_business_type(snapshot),
        maturity=_maturity(snapshot),
        authority_band=_authority_band(snapshot),
        is_geo_relevant=snapshot.has_local_signals,
    )
