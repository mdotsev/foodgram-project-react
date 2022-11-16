from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (Favorite, Follow, Ingredient, Recipe, RecipeIngredients,
                     ShoppingCart, Tag, User)


class UserAdmin(UserAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
    )
    list_filter = (
        'email',
        'first_name'
    )


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'author',
        'favorite'
    )

    readonly_fields = ('favorite',)
    list_filter = (
        'name',
        'author',
        'tags'
    )

    def favorite(self, obj):
        return obj.favorites.count()


class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit',
    )
    list_filter = ('name',)


class TagAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
        'color'
    )


class FollowAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'author',
    )


admin.site.register(Follow, FollowAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Favorite)
admin.site.register(RecipeIngredients)
admin.site.register(ShoppingCart)
