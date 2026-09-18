from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token

from .models import (
    Product,
    ProductVariant,
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
)

from .serializers import (
    ProductSerializer,
    CategorySerializer,
)


def is_admin(request):
    return (
        request.user.is_authenticated
        and request.user.is_staff
    )


@api_view(["GET"])
def product_list(request):
    products = Product.objects.filter(is_active=True)

    serializer = ProductSerializer(
        products,
        many=True
    )

    return Response(serializer.data)


@api_view(["GET"])
def category_list(request):
    categories = Category.objects.all()

    serializer = CategorySerializer(
        categories,
        many=True
    )

    return Response(serializer.data)


@api_view(["GET"])
def cart_detail(request):
    session_key = request.session.session_key

    if not session_key:
        return Response({
            "items": [],
            "total": 0
        })

    try:
        cart = Cart.objects.get(
            session_key=session_key
        )
    except Cart.DoesNotExist:
        return Response({
            "items": [],
            "total": 0
        })

    items = cart.items.select_related(
        "variant",
        "variant__product"
    )

    data = []

    for item in items:
        data.append({
            "id": item.id,
            "product": item.variant.product.name,
            "variant_id": item.variant.id,
            "quantity": item.quantity,
            "unit": item.variant.unit,
            "weight": float(item.variant.quantity),
            "price": float(item.variant.price),
            "subtotal": float(
                item.variant.price * item.quantity
            ),
        })

    total = sum(
        item["subtotal"]
        for item in data
    )

    return Response({
        "items": data,
        "total": total
    })


@api_view(["POST"])
def add_to_cart(request):
    variant_id = request.data.get("variant_id")
    quantity = request.data.get("quantity", 1)

    if not variant_id:
        return Response(
            {
                "error": "variant_id is required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        variant = ProductVariant.objects.get(
            id=variant_id
        )
    except ProductVariant.DoesNotExist:
        return Response(
            {
                "error": "Product variant not found"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response(
            {
                "error": "Invalid quantity"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if quantity < 1:
        return Response(
            {
                "error": "Quantity must be at least 1"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key

    cart, created = Cart.objects.get_or_create(
        session_key=session_key
    )

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant
    )

    if created:
        cart_item.quantity = quantity
    else:
        cart_item.quantity += quantity

    cart_item.save()

    return Response({
        "message": "Product added to cart"
    })


@api_view(["PATCH"])
def update_cart_item(request, item_id):
    session_key = request.session.session_key

    if not session_key:
        return Response(
            {
                "error": "Cart not found"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        item = CartItem.objects.select_related(
            "cart"
        ).get(
            id=item_id,
            cart__session_key=session_key
        )
    except CartItem.DoesNotExist:
        return Response(
            {
                "error": "Cart item not found"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    quantity = request.data.get("quantity")

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response(
            {
                "error": "Invalid quantity"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if quantity < 1:
        return Response(
            {
                "error": "Quantity must be at least 1"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    item.quantity = quantity
    item.save()

    return Response({
        "message": "Cart updated successfully"
    })


@api_view(["DELETE"])
def remove_from_cart(request, item_id):
    session_key = request.session.session_key

    if not session_key:
        return Response(
            {
                "error": "Cart item not found"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        item = CartItem.objects.select_related(
            "cart"
        ).get(
            id=item_id,
            cart__session_key=session_key
        )
    except CartItem.DoesNotExist:
        return Response(
            {
                "error": "Cart item not found"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    item.delete()

    return Response({
        "message": "Product removed from cart"
    })


@api_view(["POST"])
def create_order(request):
    name = request.data.get("name")
    phone = request.data.get("phone")
    email = request.data.get("email", "")
    address = request.data.get("address")
    city = request.data.get("city", "")
    district = request.data.get("district", "")
    pincode = request.data.get("pincode")

    if not name or not phone or not address or not pincode:
        return Response(
            {
                "error": (
                    "Name, phone, address and "
                    "pincode are required"
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    session_key = request.session.session_key

    if not session_key:
        return Response(
            {
                "error": "Cart is empty"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        cart = Cart.objects.get(
            session_key=session_key
        )
    except Cart.DoesNotExist:
        return Response(
            {
                "error": "Cart is empty"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    cart_items = cart.items.select_related(
        "variant",
        "variant__product"
    )

    if not cart_items.exists():
        return Response(
            {
                "error": "Cart is empty"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    total_amount = sum(
        item.variant.price * item.quantity
        for item in cart_items
    )

    order = Order.objects.create(
        name=name,
        phone=phone,
        email=email,
        address=address,
        city=city,
        district=district,
        pincode=pincode,
        total_amount=total_amount
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            price=item.variant.price
        )

    cart.items.all().delete()

    return Response(
        {
            "message": "Order created successfully",
            "order_id": order.id,
            "total": float(order.total_amount),
            "status": order.status
        },
        status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
def my_orders(request):
    phone = request.GET.get("phone")

    if not phone:
        return Response(
            {
                "error": "Phone number is required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    orders = Order.objects.filter(
        phone=phone
    ).prefetch_related(
        "items__variant__product"
    ).order_by(
        "-created_at"
    )

    data = []

    for order in orders:
        items = []

        for item in order.items.all():
            items.append({
                "product": item.variant.product.name,
                "quantity": item.quantity,
                "weight": float(
                    item.variant.quantity
                ),
                "unit": item.variant.unit,
                "price": float(item.price),
                "subtotal": float(
                    item.price * item.quantity
                ),
            })

        data.append({
            "order_id": order.id,
            "name": order.name,
            "phone": order.phone,
            "address": order.address,
            "pincode": order.pincode,
            "total": float(order.total_amount),
            "status": order.status,
            "created_at": order.created_at,
            "items": items,
        })

    return Response({
        "orders": data
    })


@api_view(["GET"])
def csrf_token(request):
    token = get_token(request)

    return Response({
        "csrfToken": token
    })


@api_view(["POST"])
def admin_login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {
                "message": "Username and password are required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(
        request,
        username=username,
        password=password
    )

    if user is None:
        return Response(
            {
                "message": "Invalid username or password"
            },
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_staff:
        return Response(
            {
                "message": "Admin access denied"
            },
            status=status.HTTP_403_FORBIDDEN
        )

    login(request, user)

    return Response({
        "message": "Login successful",
        "username": user.username
    })


@api_view(["GET"])
def admin_check(request):
    if not request.user.is_authenticated:
        return Response(
            {
                "authenticated": False
            },
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not request.user.is_staff:
        return Response(
            {
                "authenticated": False
            },
            status=status.HTTP_403_FORBIDDEN
        )

    return Response({
        "authenticated": True,
        "username": request.user.username
    })


@api_view(["POST"])
def admin_logout(request):
    logout(request)

    return Response({
        "message": "Logout successful"
    })


@api_view(["GET"])
def admin_orders(request):
    if not is_admin(request):
        return Response(
            {
                "message": "Admin access required"
            },
            status=status.HTTP_403_FORBIDDEN
        )

    orders = Order.objects.prefetch_related(
        "items__variant__product"
    ).order_by(
        "-created_at"
    )

    data = []

    for order in orders:
        items = []

        for item in order.items.all():
            items.append({
                "product": item.variant.product.name,
                "quantity": item.quantity,
                "weight": float(
                    item.variant.quantity
                ),
                "unit": item.variant.unit,
                "price": float(item.price),
                "subtotal": float(
                    item.price * item.quantity
                ),
            })

        data.append({
            "order_id": order.id,
            "name": order.name,
            "phone": order.phone,
            "email": order.email,
            "address": order.address,
            "city": order.city,
            "district": order.district,
            "pincode": order.pincode,
            "total": float(order.total_amount),
            "status": order.status,
            "created_at": order.created_at,
            "items": items,
        })

    return Response({
        "orders": data
    })


@api_view(["PATCH"])
def admin_update_order_status(request, order_id):
    if not is_admin(request):
        return Response(
            {
                "message": "Admin access required"
            },
            status=status.HTTP_403_FORBIDDEN
        )

    new_status = request.data.get("status")

    valid_statuses = [
        "pending",
        "confirmed",
        "shipped",
        "delivered",
        "cancelled",
    ]

    if new_status not in valid_statuses:
        return Response(
            {
                "error": "Invalid order status"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        order = Order.objects.get(
            id=order_id
        )
    except Order.DoesNotExist:
        return Response(
            {
                "error": "Order not found"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    order.status = new_status
    order.save()

    return Response({
        "message": "Order status updated successfully",
        "order_id": order.id,
        "status": order.status
    })
    
@api_view(["GET", "POST"])
def admin_categories(request):
    if not is_admin(request):
        return Response(
            {"message": "Admin access required"},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == "GET":
        categories = Category.objects.all().order_by("-id")

        data = []

        for category in categories:
            data.append({
                "id": category.id,
                "name": category.name,
                "product_count": category.products.count()
            })

        return Response({"categories": data})

    name = request.data.get("name", "").strip()

    if not name:
        return Response(
            {"message": "Category name is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if Category.objects.filter(name__iexact=name).exists():
        return Response(
            {"message": "Category already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )

    category = Category.objects.create(name=name)

    return Response(
        {
            "message": "Category created successfully",
            "category": {
                "id": category.id,
                "name": category.name,
                "product_count": 0
            }
        },
        status=status.HTTP_201_CREATED
    )
    
import json
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes

@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def admin_products(request):
    if not is_admin(request):
        return Response(
            {"message": "Admin access required"},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == "GET":
        products = Product.objects.select_related(
            "category"
        ).prefetch_related("variants").order_by("-id")

        data = []

        for product in products:
            variants = []

            for variant in product.variants.all():
                variants.append({
                    "id": variant.id,
                    "quantity": str(variant.quantity),
                    "unit": variant.unit,
                    "price": str(variant.price)
                })

            image_url = None

            if product.image:
                image_url = request.build_absolute_uri(
                    product.image.url
                )

            data.append({
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "category": product.category.name,
                "category_id": product.category.id,
                "image": image_url,
                "is_active": product.is_active,
                "variants": variants
            })

        return Response({"products": data})

    name = request.data.get("name", "").strip()
    description = request.data.get("description", "").strip()
    category_id = request.data.get("category_id")
    image = request.FILES.get("image")

    if not name:
        return Response(
            {"message": "Product name is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not category_id:
        return Response(
            {"message": "Category is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return Response(
            {"message": "Category not found"},
            status=status.HTTP_400_BAD_REQUEST
        )

    variants_data = request.data.get("variants", "[]")

    try:
        variants_data = json.loads(variants_data)
    except json.JSONDecodeError:
        return Response(
            {"message": "Invalid variants data"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not isinstance(variants_data, list):
        return Response(
            {"message": "Variants must be a list"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(variants_data) == 0:
        return Response(
            {"message": "Add at least one variant"},
            status=status.HTTP_400_BAD_REQUEST
        )

    product = Product.objects.create(
        category=category,
        name=name,
        description=description,
        image=image
    )

    for variant in variants_data:
        quantity = variant.get("quantity")
        unit = variant.get("unit", "g")
        price = variant.get("price")

        if not quantity or not price:
            product.delete()

            return Response(
                {"message": "Quantity and price are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ProductVariant.objects.create(
            product=product,
            quantity=quantity,
            unit=unit,
            price=price
        )

    return Response(
        {
            "message": "Product created successfully",
            "product_id": product.id
        },
        status=status.HTTP_201_CREATED
    )
@api_view(["PATCH"])
@parser_classes([MultiPartParser, FormParser])
def admin_product_update(request, product_id):

    if not is_admin(request):
        return Response(
            {"message": "Admin access required"},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {"message": "Product not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    name = request.data.get("name", "").strip()
    description = request.data.get("description", "").strip()
    category_id = request.data.get("category_id")

    if not name:
        return Response(
            {"message": "Product name is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not category_id:
        return Response(
            {"message": "Category is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return Response(
            {"message": "Category not found"},
            status=status.HTTP_400_BAD_REQUEST
        )

    variants_data = request.data.get("variants", "[]")

    try:
        variants_data = json.loads(variants_data)
    except json.JSONDecodeError:
        return Response(
            {"message": "Invalid variants data"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not isinstance(variants_data, list):
        return Response(
            {"message": "Variants must be a list"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(variants_data) == 0:
        return Response(
            {"message": "Add at least one variant"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # --------------------------------
    # UPDATE PRODUCT
    # --------------------------------

    product.name = name
    product.description = description
    product.category = category

    # Update image only if new image selected
    if request.FILES.get("image"):
        product.image = request.FILES.get("image")

    product.save()

    # --------------------------------
    # UPDATE / CREATE VARIANTS
    # --------------------------------

    existing_variant_ids = []

    for variant_data in variants_data:

        variant_id = variant_data.get("id")
        quantity = variant_data.get("quantity")
        unit = variant_data.get("unit", "g")
        price = variant_data.get("price")

        if not quantity or not price:
            return Response(
                {"message": "Quantity and price are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Existing variant
        if variant_id:

            try:
                variant = ProductVariant.objects.get(
                    id=variant_id,
                    product=product
                )
            except ProductVariant.DoesNotExist:
                return Response(
                    {"message": "Variant not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            variant.quantity = quantity
            variant.unit = unit
            variant.price = price

            variant.save()

            existing_variant_ids.append(variant.id)

        # New variant
        else:

            variant = ProductVariant.objects.create(
                product=product,
                quantity=quantity,
                unit=unit,
                price=price
            )

            existing_variant_ids.append(variant.id)

    # --------------------------------
    # IMPORTANT
    # --------------------------------
    # Do NOT delete old ProductVariants here.
    #
    # Some of them may already be used
    # by OrderItem.
    #
    # Therefore we leave them untouched.
    # --------------------------------

    return Response({
        "message": "Product updated successfully"
    })
    
@api_view(["DELETE"])
def admin_product_delete(request, product_id):

    if not is_admin(request):
        return Response(
            {"message": "Admin access required"},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {"message": "Product not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check whether any variant is used in an order
    if product.variants.filter(orderitem__isnull=False).exists():
        return Response(
            {
                "message": "This product cannot be deleted because it is already used in an order."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    product.delete()

    return Response({
        "message": "Product deleted successfully"
    })