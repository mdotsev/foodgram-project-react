from datetime import datetime

from api.pagination import LimitPageNumberPagination

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend

from djoser.views import UserViewSet as BaseUserViewSet

from recipes.models import (Favorite, Follow, Ingredient, Recipe,
                            RecipeIngredients, ShoppingCart, Tag)

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from .serializers import (FollowSerializer, IngredientSerializer,
                          ReadOnlyRecipeSerializer, RecipeInfoSerializer,
                          RecipeSerializer, TagSerializer, UserSerializer)

User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()

    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()

    serializer_class = IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filterset_class = (IngredientFilter)
    filter_backends = (DjangoFilterBackend,)


class UserViewSet(BaseUserViewSet):
    queryset = User.objects.all()

    serializer_class = UserSerializer
    pagination_class = LimitPageNumberPagination

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        user = request.user
        queryset = Follow.objects.filter(user=user)
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages,
            many=True,
            context={'request': request}
        )

        return self.get_paginated_response(serializer.data)


class SubscribeViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    serializer_class = FollowSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination

    def get_data(self):
        author_id = self.kwargs.get('id')
        author = get_object_or_404(User, pk=author_id)
        user = self.request.user
        follow = Follow.objects.filter(user=user, author=author)

        return (author, user, follow)

    def create(self, request, *args, **kwargs):

        author, user, follow = self.get_data()

        if user == author:
            return Response(
                {'errors': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        follow, created = Follow.objects.get_or_create(
            user=user,
            author=author,
        )
        if created:
            serializer = FollowSerializer(
                follow,
                context={'request': request}
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(
            {'errors': 'Вы уже подписаны на этого пользователя'},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, *args, **kwargs):
        author, user, follow = self.get_data()

        if user == author:
            return Response(
                {'errors': 'Нельзя отписаться от себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if follow.exists():
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {'errors': 'Вы уже отписаны от этого пользователя'},
            status=status.HTTP_400_BAD_REQUEST
        )


class RecipeViewSet(viewsets.ModelViewSet):

    queryset = Recipe.objects.all()

    permission_classes = [IsAuthorOrReadOnly]
    pagination_class = LimitPageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ReadOnlyRecipeSerializer
        return RecipeSerializer

    def add_recipe(self, model, user, pk, message):
        if model.objects.filter(user=user, recipe__id=pk).exists():
            return Response(
                {'errors': f'Рецепт уже добавлен в список {message}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        recipe = get_object_or_404(Recipe, id=pk)
        model.objects.create(user=user, recipe=recipe)
        serializer = RecipeInfoSerializer(recipe)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_recipe(self, model, user, pk, message):
        recipe = model.objects.filter(user=user, recipe__id=pk)
        if recipe.exists():
            recipe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': f'Рецепта нет в списке {message}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        message = 'избранных'
        if request.method == 'POST':
            return self.add_recipe(Favorite, request.user, pk, message)
        return self.delete_recipe(Favorite, request.user, pk, message)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        message = 'покупок'
        if request.method == 'POST':
            return self.add_recipe(ShoppingCart, request.user, pk, message)
        return self.delete_recipe(ShoppingCart, request.user, pk, message)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
    )
    def download_shopping_cart(self, request):
        user = request.user

        if not user.shopping_cart.exists():
            return Response(
                {'errors': 'Ваш список продуктов пуст'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ingredients = RecipeIngredients.objects.filter(
            recipe__shopping_cart__user=user
        )

        ingredients_list = {}

        for ingredient in ingredients:
            name = ingredient.ingredient.name
            amount = ingredient.amount
            measurement_unit = ingredient.ingredient.measurement_unit

            if name not in ingredients_list:
                ingredients_list[name] = {
                    'amount': amount,
                    'measurement_unit': measurement_unit
                }
            else:
                ingredients_list[name]['amount'] += amount

        shopping_list = '\n'.join([

            f'{ingredient} — '
            f'{ingredients_list[ingredient]["amount"]}'
            f'{ingredients_list[ingredient]["measurement_unit"]}'

            for ingredient in ingredients_list
        ])

        today = datetime.today()

        filename = f'Shopping list {today:%Y-%m-%d}.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response
