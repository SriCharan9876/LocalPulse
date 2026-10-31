from typing import List, Dict, Optional
from app.schemas.collaboration import (
    MarginValidationResponse, DiscoverablePartner, ComplementaryProductInfo
)

# Deterministic complementary pairings matrix based on merchant categories
CATEGORY_SYNERGIES = {
    ("Grocery & Daily Essentials", "Cafe & Bakery"): {
        "synergy_type": "Morning Tea & Breakfast Combo",
        "rationale": "Customers stocking daily groceries frequently purchase fresh bakery loaves or premium morning tea blends.",
        "complementary_score": 94,
    },
    ("Grocery & Daily Essentials", "Fresh Fruits & Vegetables"): {
        "synergy_type": "Daily Fresh Kitchen Basket",
        "rationale": "High grocery basket overlap with fresh salads and seasonal fruit buyers.",
        "complementary_score": 91,
    },
    ("Cafe & Bakery", "Traditional Sweets & Snacks"): {
        "synergy_type": "Festive Confectionery & Beverage Hamper",
        "rationale": "Complementary gifting appeal combining artisan bakes with traditional festive savories.",
        "complementary_score": 86,
    },
    ("Grocery & Daily Essentials", "Health & Wellness"): {
        "synergy_type": "Wellness & Immunity Grocery Pack",
        "rationale": "Cross-category synergy combining wholesome staples with pure organic wellness supplements.",
        "complementary_score": 88,
    },
    ("Fashion & Textiles", "Cafe & Bakery"): {
        "synergy_type": "Lifestyle Leisure & Refreshment Perk",
        "rationale": "Shoppers exploring apparel redeem coffee & cookie vouchers next door.",
        "complementary_score": 75,
    },
}

class CollaborationService:
    MIN_MARGIN_THRESHOLD_PCT: float = 12.0

    def validate_bundle_margins(
        self,
        initiator_product: dict,
        initiator_discount_pct: float,
        partner_product: dict,
        partner_discount_pct: float,
        bundle_name: str
    ) -> MarginValidationResponse:
        """
        Deterministic backend arithmetic for bundle margins, unit profits,
        and minimum viability threshold.
        """
        # Initiator calculations
        init_orig_price = float(initiator_product["selling_price"])
        init_cost = float(initiator_product["cost_price"])
        init_disc_rate = max(0.0, min(initiator_discount_pct, 50.0)) / 100.0
        init_discounted_price = round(init_orig_price * (1.0 - init_disc_rate), 2)
        init_profit = round(init_discounted_price - init_cost, 2)
        init_margin_pct = round((init_profit / init_discounted_price * 100.0), 2) if init_discounted_price > 0 else 0.0

        # Partner calculations
        partner_orig_price = float(partner_product["selling_price"])
        partner_cost = float(partner_product["cost_price"])
        partner_disc_rate = max(0.0, min(partner_discount_pct, 50.0)) / 100.0
        partner_discounted_price = round(partner_orig_price * (1.0 - partner_disc_rate), 2)
        partner_profit = round(partner_discounted_price - partner_cost, 2)
        partner_margin_pct = round((partner_profit / partner_discounted_price * 100.0), 2) if partner_discounted_price > 0 else 0.0

        # Bundle totals
        orig_bundle_price = round(init_orig_price + partner_orig_price, 2)
        discounted_bundle_price = round(init_discounted_price + partner_discounted_price, 2)
        effective_disc_pct = round(((orig_bundle_price - discounted_bundle_price) / orig_bundle_price * 100.0), 2) if orig_bundle_price > 0 else 0.0

        # Enforce minimum margin viability
        init_viable = init_margin_pct >= self.MIN_MARGIN_THRESHOLD_PCT
        partner_viable = partner_margin_pct >= self.MIN_MARGIN_THRESHOLD_PCT
        is_viable = init_viable and partner_viable

        if is_viable:
            status_reason = (
                f"Viable: Both merchants maintain healthy positive margins above the {self.MIN_MARGIN_THRESHOLD_PCT}% "
                f"safety threshold (Initiator: {init_margin_pct}%, Partner: {partner_margin_pct}%)."
            )
        elif not init_viable and not partner_viable:
            status_reason = (
                f"Rejected: Both products drop below the minimum required {self.MIN_MARGIN_THRESHOLD_PCT}% margin. "
                "Reduce discounts to protect unit profitability."
            )
        elif not init_viable:
            status_reason = (
                f"Rejected: Initiator discount is too aggressive, resulting in {init_margin_pct}% margin "
                f"(minimum threshold is {self.MIN_MARGIN_THRESHOLD_PCT}%)."
            )
        else:
            status_reason = (
                f"Rejected: Partner discount leaves only {partner_margin_pct}% margin "
                f"(minimum threshold is {self.MIN_MARGIN_THRESHOLD_PCT}%)."
            )

        return MarginValidationResponse(
            bundle_name=bundle_name,
            original_bundle_price=orig_bundle_price,
            discounted_bundle_price=discounted_bundle_price,
            effective_bundle_discount_pct=effective_disc_pct,
            initiator_product_name=initiator_product["name"],
            initiator_original_price=init_orig_price,
            initiator_discounted_price=init_discounted_price,
            initiator_cost=init_cost,
            initiator_margin_pct=init_margin_pct,
            initiator_profit_per_unit=init_profit,
            partner_product_name=partner_product["name"],
            partner_original_price=partner_orig_price,
            partner_discounted_price=partner_discounted_price,
            partner_cost=partner_cost,
            partner_margin_pct=partner_margin_pct,
            partner_profit_per_unit=partner_profit,
            min_required_margin_pct=self.MIN_MARGIN_THRESHOLD_PCT,
            is_financially_viable=is_viable,
            status_reason=status_reason,
        )

    def discover_partners(
        self,
        current_merchant: dict,
        all_merchants: List[dict],
        products_by_merchant: Dict[str, List[dict]]
    ) -> List[DiscoverablePartner]:
        """
        Discover fictional nearby merchants with complementary products and synergy ratings.
        """
        current_id = current_merchant["merchant_id"]
        current_cat = current_merchant.get("category", "")
        partners = []

        for m in all_merchants:
            m_id = m["merchant_id"]
            if m_id == current_id:
                continue

            partner_cat = m.get("category", "")
            
            # Lookup synergy rule or provide standard default
            key1 = (current_cat, partner_cat)
            key2 = (partner_cat, current_cat)
            
            if key1 in CATEGORY_SYNERGIES:
                meta = CATEGORY_SYNERGIES[key1]
            elif key2 in CATEGORY_SYNERGIES:
                meta = CATEGORY_SYNERGIES[key2]
            else:
                meta = {
                    "synergy_type": "Neighborhood Merchant Cross-Promotion",
                    "rationale": "Local co-marketing bundle driving foot traffic between adjacent storefronts.",
                    "complementary_score": 70,
                }

            # Gather top products
            prods = products_by_merchant.get(m_id, [])
            top_products = [
                ComplementaryProductInfo(
                    product_id=p["product_id"],
                    name=p["name"],
                    category=p["category"],
                    selling_price=float(p["selling_price"]),
                    cost_price=float(p["cost_price"]),
                )
                for p in prods[:4]
            ]

            # Real Haversine distance if coordinates exist, else deterministic hash
            lat1 = current_merchant.get("latitude")
            lon1 = current_merchant.get("longitude")
            lat2 = m.get("latitude")
            lon2 = m.get("longitude")

            if lat1 is not None and lon1 is not None and lat2 is not None and lon2 is not None:
                import math
                R = 6371.0
                dlat = math.radians(lat2 - lat1)
                dlon = math.radians(lon2 - lon1)
                a = (math.sin(dlat / 2) ** 2 +
                     math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                     math.sin(dlon / 2) ** 2)
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                dist = round(R * c, 2)
            else:
                dist = round(0.2 + (abs(hash(m_id)) % 25) / 10.0, 1)

            coords = m.get("coordinates")
            if not coords and lat2 is not None and lon2 is not None:
                coords = {"lat": lat2, "lng": lon2}

            partners.append(
                DiscoverablePartner(
                    merchant_id=m_id,
                    business_name=m["business_name"],
                    category=partner_cat,
                    address=m.get("address", "Indiranagar, Bengaluru"),
                    distance_km=dist,
                    latitude=lat2,
                    longitude=lon2,
                    coordinates=coords,
                    synergy_type=meta["synergy_type"],
                    synergy_rationale=meta["rationale"],
                    complementary_score=meta["complementary_score"],
                    top_products=top_products,
                )
            )

        partners.sort(key=lambda p: p.complementary_score, reverse=True)
        return partners

collaboration_service = CollaborationService()
