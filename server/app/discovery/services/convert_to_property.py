def build_property_from_listing(listing: DiscoveredListing, db: Session, owner_agent_id: int) -> Property:
    deal_type = DEAL_TYPE_MAP.get(listing.deal_type, DealType.sale)

    district = None
    if listing.neighborhood_id:
        n = db.get(DiscoveryNeighborhood, listing.neighborhood_id)
        district = n.name if n else None

    details = {}
    if deal_type == DealType.sale and listing.price:
        details["price"] = listing.price
    elif deal_type == DealType.rent:
        if listing.deposit and listing.monthly_rent:
            details["deposit"] = listing.deposit
            details["monthly_rent"] = listing.monthly_rent
        elif listing.deposit:
            # اجاره بدون اجاره‌ماهانه = رهن کامل
            deal_type = DealType.mortgage
            details["deposit_full"] = listing.deposit

    note_lines = [f"وارد شده از ملک‌یاب — منبع: {listing.source}", listing.title or "", listing.url or ""]

    return Property(
        deal_type=deal_type,
        city=listing.city or "مشهد",
        district=district,
        address=listing.raw_address,
        area_m2=listing.area_m2,
        rooms=listing.rooms,
        details=details,
        notes="\n".join(line for line in note_lines if line),
        owner_agent_id=owner_agent_id,
    )