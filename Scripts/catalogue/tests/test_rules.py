import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogue_export as catalogue
from catalogue_rules import apply_rules, load_tags

DIRECTORY = Path(catalogue.__file__).parent


def recipe(**changes):
    value = {'schemaVersion': 1, 'sourceFile': 'Asian Cooking/Soup.md', 'isRecipe': True,
             'cleanTitle': 'Soup', 'categories': ['japanese', 'vegetarian', 'soups'],
             'cuisine': 'japanese', 'mainIngredient': 'tofu', 'ingredients': ['tofu'],
             'tags': ['#weeknight'], 'likelyDuplicateOf': None, 'confidence': .95, 'notes': ''}
    value.update(changes)
    return value


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.categories, self.cuisines = catalogue.categories_from(DIRECTORY / 'categories.json')
        self.tags = load_tags(DIRECTORY / 'tags.json')

    def apply(self, value, checks=None):
        return apply_rules(copy.deepcopy(value), self.categories, self.tags, checks)

    def test_dish_limit_unknown_ids_and_main_fallback_are_logged(self):
        result = self.apply(recipe(categories=['japanese', 'made-up', 'main-dishes', 'soups', 'curries-stews', 'sides']))
        self.assertEqual(result['categories'], ['japanese', 'soups', 'curries-stews'])
        for dropped in ['made-up', 'main-dishes', 'sides']:
            self.assertIn(dropped, result['notes'])
        self.assertIn('main-dishes', self.apply(recipe(categories=['japanese', 'main-dishes']))['categories'])

    def test_specific_dish_type_precedes_meal_role(self):
        result = self.apply(recipe(categories=['japanese', 'sides', 'soups', 'starters-snacks']))
        self.assertEqual(result['categories'], ['japanese', 'soups', 'sides'])
        self.assertIn('starters-snacks', result['notes'])

    def test_tag_aliases_unknown_duplicates_and_limit(self):
        result = self.apply(recipe(tags=['#one-pan', '#one-wok', '#kimchi', '#quick', '#easy',
                                        '#weeknight', '#spicy', '#comfort-food']))
        self.assertEqual(result['tags'], ['#one-pot', '#quick', '#easy', '#weeknight', '#spicy'])
        for changed in ['one-pan', 'one-wok', '#kimchi', '#comfort-food']:
            self.assertIn(changed, result['notes'])

    def test_asian_fallback_and_child_precedence(self):
        self.assertEqual(self.apply(recipe(categories=['asian', 'curries-stews'], cuisine='asian'))['cuisine'], 'asian')
        result = self.apply(recipe(categories=['asian', 'korean', 'soups'], cuisine='korean'))
        self.assertNotIn('asian', result['categories'])
        self.assertEqual(result['cuisine'], 'korean')

    def test_vegetarian_exclusions_and_optional_swap(self):
        for ingredient in ['fish sauce', 'shrimp paste', 'dried shrimp', 'anchovy stock',
                           'oyster sauce', 'meat stock', 'chicken', 'beef', 'pork', 'tuna',
                           'fish sauce (or vegan substitute)']:
            with self.subTest(ingredient=ingredient):
                result = self.apply(recipe(ingredients=['tofu', ingredient], tags=['#vegan', '#veggie-option']))
                self.assertNotIn('vegetarian', result['categories'])
                self.assertNotIn('#vegan', result['tags'])
                self.assertIn('#veggie-option', result['tags'])
                self.assertIn('Dropped vegetarian', result['notes'])

    def test_house_kimchi_does_not_override_other_animal_ingredients(self):
        result = self.apply(recipe(ingredients=['kimchi', 'fish sauce']))
        self.assertNotIn('vegetarian', result['categories'])

    def test_oyster_mushroom_is_not_seafood(self):
        result = self.apply(recipe(ingredients=['oyster mushroom', 'tofu']),
                            {'vegetarianStatus': 'confirmed', 'vegetarianReason': 'Plant ingredients.'})
        self.assertIn('vegetarian', result['categories'])

    def test_explicit_vegetarian_kimchi_is_allowed(self):
        for ingredient in ['kimchi', 'kimchi juice', 'vegan kimchi', 'vegetarian kimchi', 'vegan fish sauce']:
            with self.subTest(ingredient=ingredient):
                result = self.apply(recipe(ingredients=['tofu', ingredient]),
                                    {'vegetarianStatus': 'confirmed', 'vegetarianReason': 'Explicitly vegan.'})
                self.assertIn('vegetarian', result['categories'])

    def test_uncertainty_lowers_confidence_but_meat_with_kimchi_stays_meat(self):
        result = self.apply(recipe(ingredients=['tofu']), {'vegetarianStatus': 'uncertain', 'vegetarianReason': 'Ingredients incomplete.'})
        self.assertNotIn('vegetarian', result['categories'])
        self.assertLessEqual(result['confidence'], .7)
        self.assertIn('Lowered confidence', result['notes'])
        result = self.apply(recipe(categories=['korean', 'meat', 'soups'], cuisine='korean', ingredients=['pork', 'kimchi']),
                            {'vegetarianStatus': 'not-vegetarian', 'vegetarianReason': 'Contains pork.'})
        self.assertIn('meat', result['categories'])
        self.assertEqual(result['confidence'], .95)

    def test_main_ingredient_rejects_seasonings_and_sauces(self):
        for ingredient in ['coconut milk', 'chilli flakes', 'gochujang', 'olive oil', 'soy sauce']:
            with self.subTest(ingredient=ingredient):
                result = self.apply(recipe(mainIngredient=ingredient))
                self.assertIsNone(result['mainIngredient'])
                self.assertIn(ingredient, result['notes'])
        self.assertIsNone(self.apply(recipe(mainIngredient='tomato', categories=['sauces-dips-condiments'], cuisine=None))['mainIngredient'])
        self.assertEqual(self.apply(recipe(mainIngredient='aubergine'))['mainIngredient'], 'aubergine')

    def test_checks_are_not_written_to_sidecar_and_validation_is_idempotent(self):
        value = recipe(categories=['japanese', 'vegetarian', 'soups', 'main-dishes'], tags=['#one-pan', '#unknown'], ingredients=['tofu', 'fish sauce'])
        value['catalogueChecks'] = {'vegetarianStatus': 'not-vegetarian', 'vegetarianReason': 'Fish sauce.', 'mainIngredientRole': 'protein'}
        result = catalogue.validate(value, value['sourceFile'], self.categories, self.cuisines, [], self.tags)
        self.assertNotIn('catalogueChecks', result)
        again = catalogue.validate(result, result['sourceFile'], self.categories, self.cuisines, [], self.tags)
        self.assertEqual(result, again)



if __name__ == '__main__':
    unittest.main()
