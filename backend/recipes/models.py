from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint

ORANGE = '#E26C2D'
GREEN = '#49B64E'
PURPLE = '#8775D2'


COLORS = (
        (ORANGE, 'Оранжевый'),
        (GREEN, 'Зеленый'),
        (PURPLE, 'Пурпурный'),
    )


class User(AbstractUser):
    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name='Email'
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Имя пользователя'
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ['-id']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Tag(models.Model):
    name = models.CharField('Название', max_length=200, unique=True)
    slug = models.SlugField('Slug', max_length=200, unique=True)
    color = models.CharField(choices=COLORS, max_length=16, unique=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField('Название', max_length=200)
    measurement_unit = models.CharField('Единицы измерения', max_length=200)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    name = models.CharField('Название', max_length=200)
    text = models.TextField('Текст')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredients',
        related_name='recipes',
        verbose_name='Ингредиенты',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        verbose_name='Фото блюда'
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги'
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=[
            MinValueValidator(
                1,
                message='Время приготовления не может быть меньше минуты')
            ]
    )

    class Meta:
        verbose_name = 'Рецепты'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredients(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_list',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe',
        verbose_name='Ингредиент',
    )
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, message='Не может быть менее одного'),
        ],
        verbose_name='Количество',
    )

    class Meta:
        verbose_name = 'Ингредиенты для рецептов'
        verbose_name_plural = 'Ингредиенты для рецептов'
        constraints = [
            models.UniqueConstraint(
                fields=['ingredient', 'recipe'],
                name='ingredient_recipe_unique')
        ]


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзина'

        constraints = [
            UniqueConstraint(
                fields=['user', 'recipe'],
                name='user_recipe_shopping_unique'
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.recipe}'


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

        constraints = [
            UniqueConstraint(
                fields=['user', 'recipe'],
                name='user_recipe_unique'
            ),
        ]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='author',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

        constraints = [
            UniqueConstraint(
                fields=['user', 'author'],
                name='user_author_unique'
            ),
        ]
