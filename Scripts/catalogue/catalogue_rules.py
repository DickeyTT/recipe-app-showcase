"""Shared catalogue validation for the fixed category/tag lists and review rules."""
import json
import re

RULES_VERSION = '2026-10-25-review-3'


def load_tags(path):
    document = json.loads(path.read_text(encoding='utf-8'))
    tags = {}
    aliases = {}
    for group in document['groups']:
        for item in group['tags']:
            tag = item['tag']
            if tag in tags or not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', tag):
                raise ValueError('Invalid or duplicate canonical tag.')
            tags[tag] = item['meaning']
            for alias in item.get('aliases', []):
                if alias in aliases and aliases[alias] != tag:
                    raise ValueError('Conflicting tag aliases.')
                aliases[alias] = tag
    if set(aliases) & set(tags):
        raise ValueError('A tag alias cannot also be a canonical tag.')
    limit = document['maxTagsPerRecipe']
    if type(limit) is not int or not 0 < limit <= 5:
        raise ValueError('Tag limit must be between one and five.')
    return {'tags': tags, 'aliases': aliases, 'limit': limit}


def prune_categories(result, categories, changes):
    selected = []
    for category in result['categories']:
        if category not in categories:
            changes.append('Dropped unknown category: ' + category)
        elif category not in selected:
            selected.append(category)
    for parent, details in categories.items():
        if parent in selected and any(child in selected for child in details.get('children', [])):
            selected.remove(parent)
            changes.append('Dropped implied parent category: ' + parent)
    dishes = [item for item in selected if categories[item]['section'] == 'dish-type']
    if 'main-dishes' in dishes and len(dishes) > 1:
        selected.remove('main-dishes')
        dishes.remove('main-dishes')
        changes.append('Dropped main-dishes because a more specific dish type is present')
    meal_roles = {'breakfast-brunch', 'lunches-light-meals', 'starters-snacks', 'main-dishes', 'sides'}
    ordered = sorted(dishes, key=lambda item: item in meal_roles)
    if ordered != dishes:
        changes.append('Ordered dish types most specific first')
        slots = iter(ordered)
        selected = [next(slots) if item in dishes else item for item in selected]
        dishes = ordered
    for item in dishes[2:]:
        selected.remove(item)
        changes.append('Dropped excess dish type: ' + item)
    result['categories'] = selected
    cuisine = result['cuisine']
    if cuisine is not None and (cuisine not in selected or categories[cuisine]['section'] != 'cuisine'):
        changes.append('Cleared unrecognised or unselected cuisine: ' + cuisine)
        result['cuisine'] = None
    # Keep only the model's single chosen cuisine; do not guess from category order.
    for item in list(selected):
        if categories[item]['section'] == 'cuisine' and item != result['cuisine']:
            selected.remove(item)
            changes.append('Dropped extra cuisine category: ' + item)


def prune_tags(result, rules, changes):
    selected = []
    for raw in result['tags']:
        name = raw.strip().lstrip('#').lower()
        canonical = rules['aliases'].get(name, name)
        if canonical not in rules['tags']:
            changes.append('Dropped unknown tag: ' + raw)
            continue
        if canonical != name:
            changes.append('Mapped tag alias: ' + raw + ' → #' + canonical)
        formatted = '#' + canonical
        if formatted in selected:
            changes.append('Dropped repeated tag: ' + raw)
        elif len(selected) >= rules['limit']:
            changes.append('Dropped excess tag: ' + raw)
        else:
            selected.append(formatted)
    result['tags'] = selected


def animal_ingredients(ingredients):
    """Conservative checks against extracted recipe ingredients, never adverts/comments."""
    animal = []
    uncertain = []
    for ingredient in ingredients:
        # Explicitly labelled vegetarian substitutes do not contain the named animal ingredient.
        substitute = bool(re.match(r'(?:vegan|vegetarian|plant-based)\b', ingredient))
        if substitute:
            continue
        # User-confirmed house kimchi is vegetarian; other animal ingredients still exclude it.
        if re.search(r'\b(?:fish sauce|shrimp paste|dried shrimp|anchovy stock|anchovy broth|'
                     r'oyster sauce|meat stock|chicken stock|beef stock|bone broth|'
                     r'chicken|turkey|duck|beef|pork|lamb|bacon|ham|sausage|'
                     r'fish|seafood|anchovy|anchovies|tuna|salmon|cod|haddock|'
                     r'prawn|shrimp|clam|mussel|oyster(?! mushrooms?\b)|squid|octopus|crab|lobster|bonito)\b', ingredient):
            # Names containing 'or' may describe a non-vegetarian recipe with an adaptation.
            animal.append(ingredient)
        elif re.search(r'\b(?:stock|broth|dashi)\b', ingredient) and not re.search(
                r'\b(?:vegetable|mushroom|kombu|kelp|seaweed)\b', ingredient):
            uncertain.append(ingredient + ' (stock ingredients unspecified)')
    return animal, uncertain


def check_diet(result, checks, changes):
    animal, uncertain = animal_ingredients(result['ingredients'])
    status = checks.get('vegetarianStatus')
    if status not in (None, 'confirmed', 'not-vegetarian', 'uncertain'):
        raise ValueError('Invalid vegetarian assessment.')
    evidence = '; '.join(animal + uncertain)
    reason = checks.get('vegetarianReason', '')
    if not isinstance(reason, str):
        raise ValueError('Invalid vegetarian assessment explanation.')
    excluded = bool(animal or uncertain or not result['ingredients'] or status in ('not-vegetarian', 'uncertain'))
    if excluded:
        if 'vegetarian' in result['categories']:
            result['categories'].remove('vegetarian')
            changes.append('Dropped vegetarian: ' + (evidence or reason or 'insufficient ingredient evidence'))
        if '#vegan' in result['tags']:
            result['tags'].remove('#vegan')
            changes.append('Dropped #vegan: ' + (evidence or reason or 'insufficient ingredient evidence'))
    if (uncertain and not animal and status != 'not-vegetarian') or status == 'uncertain' or (not result['ingredients'] and result['isRecipe']):
        for item in ('meat', 'fish', 'vegetarian'):
            if item in result['categories']:
                result['categories'].remove(item)
                changes.append('Dropped uncertain main-ingredient category: ' + item)
        if result['confidence'] > 0.7:
            result['confidence'] = 0.7
            changes.append('Lowered confidence to 0.7: ' + (evidence or reason or 'ingredient evidence is incomplete'))
    if '#vegan' in result['tags'] and any(re.search(
            r'\b(?:egg|eggs|butter|cheese|yoghurt|yogurt|honey|cream|milk)\b', item)
            and not re.search(r'\b(?:vegan|plant-based|coconut|oat|almond|soya|soy|peanut|cashew|cocoa|butter bean)\b', item)
            for item in result['ingredients']):
        result['tags'].remove('#vegan')
        changes.append('Dropped #vegan: animal-derived ingredient present')


def check_main_ingredient(result, checks, changes):
    ingredient = result['mainIngredient']
    if not ingredient:
        return
    invalid_role = checks.get('mainIngredientRole') in ('seasoning', 'sauce-base', 'unknown')
    sauce = 'sauces-dips-condiments' in result['categories']
    seasoning = bool(re.search(r'\b(?:oil|sauce|paste|stock|broth|spice|seasoning|salt|'
                               r'peppercorn|gochujang|doenjang|gochugaru|chilli flakes?|'
                               r'coconut milk|coconut cream|vinegar|sugar)\b', ingredient))
    if sauce or seasoning or invalid_role:
        result['mainIngredient'] = None
        changes.append('Cleared unsuitable main ingredient: ' + ingredient)


def apply_rules(result, categories, tags, checks=None):
    changes = []
    checks = checks or {}
    if not isinstance(checks, dict):
        raise ValueError('Invalid catalogue checks.')
    prune_categories(result, categories, changes)
    prune_tags(result, tags, changes)
    check_diet(result, checks, changes)
    check_main_ingredient(result, checks, changes)
    if changes:
        note = 'Validation: ' + '; '.join(changes) + '.'
        result['notes'] = (result['notes'].rstrip() + '\n' + note).strip()
    return result
