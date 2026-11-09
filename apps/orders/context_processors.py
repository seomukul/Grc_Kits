from .cart import SESSION_KEY


def cart(request):
    data = request.session.get(SESSION_KEY) if hasattr(request, "session") else None
    return {"cart_count": len((data or {}).get("items", []))}
