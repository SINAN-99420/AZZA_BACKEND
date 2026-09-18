from django.urls import path
from .views import *


urlpatterns = [
    path("products/", product_list),
    path("categories/", category_list),

    path("cart/", cart_detail),
    path("cart/add/", add_to_cart),
    path("cart/update/<int:item_id>/", update_cart_item),
    path("cart/remove/<int:item_id>/", remove_from_cart),

    path("orders/create/", create_order),
    path("my-orders/", my_orders),

    path("admin/login/", admin_login),
    path("admin/check/", admin_check),
    path("admin/logout/", admin_logout),
    path("admin/orders/", admin_orders),
    path("admin/orders/<int:order_id>/status/", admin_update_order_status),
    path("csrf/", csrf_token),
    path("admin/categories/", admin_categories),
    path("admin/products/", admin_products),
    path("admin/products/<int:product_id>/",admin_product_update),
    path("admin/products/<int:product_id>/delete/",admin_product_delete),
    path("check-media/", check_media),
]