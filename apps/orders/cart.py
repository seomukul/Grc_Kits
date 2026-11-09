"""Session cart. Digital goods: one line per (product, license tier), quantity is always 1."""

from dataclasses import dataclass
from decimal import Decimal

from apps.catalog.models import LicenseTier, Product
from apps.core.models import SiteSettings
from apps.marketing import coupons as coupon_rules

SESSION_KEY = "cart"


@dataclass
class CartLine:
    product: Product
    tier: str
    price: Decimal
    discount: Decimal = Decimal("0")

    @property
    def key(self):
        return f"{self.product.pk}:{self.tier}"

    @property
    def tier_label(self):
        return LicenseTier(self.tier).label

    @property
    def gross(self):
        return self.price

    @property
    def total(self):
        return self.price - self.discount

    def as_coupon_line(self):
        return coupon_rules.Line(key=self.key, product_id=self.product.pk, gross=self.price)


class Cart:
    def __init__(self, request):
        self.session = request.session
        data = self.session.get(SESSION_KEY) or {}
        self.items = list(data.get("items", []))  # [{"product": id, "tier": "single"}]
        self.coupon_code = data.get("coupon", "")
        self._lines = None
        self.coupon = None
        self.coupon_error = ""

    # --- persistence ----------------------------------------------------
    def save(self):
        self.session[SESSION_KEY] = {"items": self.items, "coupon": self.coupon_code}
        self.session.modified = True
        self._lines = None

    def clear(self):
        self.items, self.coupon_code = [], ""
        self.save()

    # --- mutations ------------------------------------------------------
    def add(self, product, tier=LicenseTier.SINGLE):
        product.price_for(tier)  # raises ValueError if the tier isn't offered
        # One license per product: choosing another tier replaces the old line.
        self.items = [i for i in self.items if i["product"] != product.pk]
        self.items.append({"product": product.pk, "tier": tier})
        self.save()

    def remove(self, product_id):
        self.items = [i for i in self.items if i["product"] != int(product_id)]
        self.save()

    def set_coupon(self, code):
        self.coupon_code = (code or "").strip().upper()
        self.save()

    # --- reading ----------------------------------------------------------
    def __len__(self):
        return len(self.items)

    def product_ids(self):
        return [i["product"] for i in self.items]

    def lines(self, email=None):
        """Priced lines with coupon discounts applied. Drops products that are no longer purchasable."""
        if self._lines is not None and email is None:
            return self._lines
        s = SiteSettings.load()
        products = Product.objects.purchasable().in_bulk(self.product_ids())
        lines = []
        for item in self.items:
            product = products.get(item["product"])
            if not product:
                continue
            try:
                lines.append(CartLine(product, item["tier"], product.price_for(item["tier"], s)))
            except ValueError:
                lines.append(CartLine(product, LicenseTier.SINGLE, product.price))
        self._apply_coupon(lines, email)
        if email is None:
            self._lines = lines
        return lines

    def _apply_coupon(self, lines, email):
        self.coupon, self.coupon_error = None, ""
        if not self.coupon_code or not lines:
            return
        try:
            coupon = coupon_rules.find_coupon(self.coupon_code)
            coupon_lines = [line.as_coupon_line() for line in lines]
            coupon_rules.validate(coupon, coupon_lines, email=email)
        except coupon_rules.CouponError as exc:
            self.coupon_error = str(exc)
            return
        self.coupon = coupon
        shares = coupon_rules.allocate(coupon, coupon_lines)
        for line in lines:
            line.discount = shares.get(line.key, Decimal("0"))

    def totals(self, email=None):
        lines = self.lines(email)
        subtotal = sum((line.price for line in lines), Decimal("0"))
        discount = sum((line.discount for line in lines), Decimal("0"))
        return {"subtotal": subtotal, "discount": discount, "total": subtotal - discount}
