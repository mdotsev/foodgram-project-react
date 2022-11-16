from django.contrib.auth import get_user_model
from django.db.models import F
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.fields import IntegerField, SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField

from recipes.models import (Follow, Ingredient, Recipe,
                            RecipeIngredients, Tag,)

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'color',
            'slug'
        )


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit'
        )


class CreateUserSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = (
            User.USERNAME_FIELD,
            'password',
            'id',
        ) + tuple(User.REQUIRED_FIELDS)


class CustomUserSerializer(UserSerializer):
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, author=obj).exists()


class RecipeIngredientsSerializer(serializers.ModelSerializer):
    id = IntegerField(write_only=True)
    name = serializers.SlugRelatedField(
        slug_field='name',
        source='ingredient',
        read_only=True
    )
    measurement_unit = serializers.SlugRelatedField(
        slug_field='measurement_unit',
        source='ingredient',
        read_only=True
    )

    class Meta:
        model = RecipeIngredients
        fields = (
            'id',
            'name',
            'amount',
            'measurement_unit'
        )
        read_only_fields = (
            'name',
            'measurement_unit'
        )


class RecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientsSerializer(
        many=True,
    )

    class Meta:
        model = Recipe

        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def validate_ingredients(self, value):
        ingredients = value

        if not ingredients:
            raise serializers.ValidationError({
                'ingredients': (
                    'Выберите хотя бы один ингредиент для создания рецепта'
                )
            })

        ingredient_list = []

        for ingredient_item in ingredients:
            ingredient = get_object_or_404(
                Ingredient, id=ingredient_item['id']
            )

            if ingredient in ingredient_list:
                raise serializers.ValidationError({
                    'ingredients': (
                        'Выбранный ингредиент уже добавлен в рецепт'
                    )
                })

            ingredient_list.append(ingredient)

        return value

    def validate_tags(self, value):
        tags = value

        if not tags:
            raise serializers.ValidationError({
                'tags': (
                    'Выберите хотя бы один tag для создания рецепта'
                )
            })

        tags_list = []

        for tag in tags:
            if tag in tags_list:
                raise serializers.ValidationError({
                    'tags': (
                        'Выбранный tag уже прикреплен к рецепту'
                    )
                })
            tags_list.append(tag)

        return value

    def create_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            RecipeIngredients.objects.create(
                recipe=recipe,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount'),
            )

    def create(self, validated_data):
        image = validated_data.pop('image')
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(image=image, **validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)

        return recipe

    def update(self, instance, validated_data):
        instance.tags.clear()
        tags_data = self.initial_data.get('tags')
        instance.tags.set(tags_data)
        RecipeIngredients.objects.filter(recipe=instance).delete()
        self.create_ingredients(validated_data.pop('ingredients'), instance)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}

        return ReadOnlyRecipeSerializer(instance, context=context).data


class ReadOnlyRecipeSerializer(serializers.ModelSerializer):

    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField()

    ingredients = SerializerMethodField()
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe

        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_ingredients(self, obj):
        ingredients = obj.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=F('recipe__amount')
        )
        return ingredients

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.favorites.filter(recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.shopping_cart.filter(recipe=obj).exists()


class RecipeInfoSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )
        read_only_fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )


class FollowSerializer(serializers.ModelSerializer):

    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')

    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count'
        )

    def get_is_subscribed(self, obj):
        return Follow.objects.filter(
            user=obj.user, author=obj.author
        ).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = Recipe.objects.filter(author=obj.author)
        if limit:
            queryset = queryset[:int(limit)]
        return RecipeInfoSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()
