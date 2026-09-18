from django.contrib import admin
from .models import *


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")
    inlines = [ProductImageInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "quantity", "unit", "price")
    list_filter = ("unit",)
    search_fields = ("product__name",)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "image")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "session_key", "created_at")
    search_fields = ("session_key",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "variant", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "phone",
        "total_amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("name", "phone", "email")
    ordering = ("-created_at",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "variant", "quantity", "price")