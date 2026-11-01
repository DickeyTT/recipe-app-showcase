"""Generate the made-up demo library in demo-recipes/.

Usage: python3 Scripts/make-demo-library.py demo-recipes
"""
import json, struct, sys, zlib
from pathlib import Path

OUT = Path(sys.argv[1])

def png(path, top, bottom, w=640, h=420):
    rows = bytearray()
    for y in range(h):
        t = y / (h - 1)
        px = bytes(round(a + (b - a) * t) for a, b in zip(top, bottom))
        rows += b'\x00' + px * w
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(bytes(rows), 9)) + chunk(b'IEND', b''))

R = [
 ('Weeknight', 'Lemon_and_Herb_Traybake_Chicken', 'Lemon and herb traybake chicken', ((240, 200, 90), (190, 120, 50)),
  ['chicken thigh', 'new potato', 'lemon', 'garlic', 'thyme', 'olive oil'],
  ['meat', 'main-dishes'], None, 'chicken thigh', ['traybake', 'weeknight', 'easy'],
  ['8 chicken thighs, skin on', '600g new potatoes, halved', '1 lemon, quartered', '1 bulb garlic, cloves separated', 'A few sprigs of thyme', '3 tbsp olive oil'],
  ['Heat the oven to 200°C (180°C fan).', 'Toss everything in a large roasting tin with salt, pepper and the oil.', 'Roast for 45 minutes, turning the potatoes once, until the chicken skin is crisp.', 'Squeeze the roasted lemon over before serving.']),
 ('Weeknight', 'Spiced_Red_Lentil_Soup', 'Spiced red lentil soup', ((235, 140, 70), (170, 70, 40)),
  ['red lentil', 'onion', 'carrot', 'cumin', 'vegetable stock', 'lemon'],
  ['middle-eastern', 'vegetarian', 'soups'], 'middle-eastern', 'red lentil', ['one-pot', 'freezable', 'vegan'],
  ['200g red lentils, rinsed', '1 onion, chopped', '2 carrots, grated', '2 tsp ground cumin', '1.2 litres vegetable stock', 'Juice of half a lemon'],
  ['Soften the onion in a little oil for 8 minutes.', 'Add the cumin and carrot and cook for 2 minutes.', 'Add the lentils and stock, simmer for 20 minutes until soft.', 'Blend until smooth, season, and finish with lemon juice.']),
 ('Weeknight', 'Pasta_with_Courgette_and_Mint', 'Pasta with courgette and mint', ((170, 210, 120), (80, 140, 70)),
  ['spaghetti', 'courgette', 'mint', 'parmesan', 'garlic'],
  ['italian', 'vegetarian', 'pasta-noodles'], 'italian', 'courgette', ['quick', 'weeknight'],
  ['300g spaghetti', '3 courgettes, coarsely grated', '2 garlic cloves, sliced', 'A handful of mint leaves', '40g parmesan, grated'],
  ['Cook the pasta in well-salted water.', 'Meanwhile fry the garlic gently, then add the courgette and cook until soft and sweet, about 10 minutes.', 'Toss in the drained pasta with a splash of cooking water, the parmesan and torn mint.']),
 ('Weeknight', 'Baked_Cod_with_Chorizo_and_Beans', 'Baked cod with chorizo and beans', ((230, 120, 90), (150, 60, 50)),
  ['cod', 'chorizo', 'butter bean', 'tomato', 'parsley'],
  ['spanish-portuguese', 'fish', 'main-dishes'], 'spanish-portuguese', 'cod', ['one-pot', 'weeknight'],
  ['4 cod fillets', '100g cooking chorizo, sliced', '2 tins butter beans, drained', '1 tin chopped tomatoes', 'Chopped parsley'],
  ['Fry the chorizo in an ovenproof pan until it releases its oil.', 'Add the tomatoes and beans and simmer for 10 minutes.', 'Sit the cod on top and bake at 200°C for 12 minutes.', 'Scatter with parsley.']),
 ('Asian Cooking', 'Quick_Pork_Stir_Fry_with_Greens', 'Quick pork stir-fry with greens', ((200, 170, 110), (110, 80, 50)),
  ['pork mince', 'pak choi', 'ginger', 'garlic', 'soy sauce', 'rice'],
  ['chinese', 'meat', 'main-dishes'], 'chinese', 'pork', ['stir-fry', 'quick'],
  ['300g pork mince', '2 heads pak choi, quartered', 'Thumb of ginger, grated', '2 garlic cloves, grated', '2 tbsp soy sauce', 'Steamed rice, to serve'],
  ['Fry the pork in a hot wok until browned and crisp in places.', 'Add the ginger and garlic for 30 seconds.', 'Add the pak choi and soy sauce and toss until just wilted.', 'Serve over rice.']),
 ('Asian Cooking', 'Thai_Green_Vegetable_Curry', 'Thai green vegetable curry', ((150, 200, 120), (60, 120, 70)),
  ['aubergine', 'green bean', 'coconut milk', 'green curry paste', 'basil'],
  ['thai', 'vegetarian', 'curries-stews'], 'thai', 'aubergine', ['spicy', 'veggie-option'],
  ['1 aubergine, cubed', '150g green beans', '400ml coconut milk', '2 tbsp green curry paste (check it has no shrimp paste)', 'A handful of Thai basil'],
  ['Fry the curry paste in a splash of the coconut milk until fragrant.', 'Add the rest of the coconut milk and the aubergine; simmer for 15 minutes.', 'Add the beans for the last 5 minutes.', 'Stir in the basil and serve with rice.']),
 ('Asian Cooking', 'Simple_Cucumber_Kimchi', 'Simple cucumber kimchi', ((140, 200, 150), (200, 80, 60)),
  ['cucumber', 'gochugaru', 'spring onion', 'garlic'],
  ['korean', 'vegetarian', 'ferments-pickles'], 'korean', 'cucumber', ['make-ahead', 'spicy'],
  ['4 small cucumbers', '1 tbsp salt', '2 tbsp gochugaru', '3 spring onions, sliced', '2 garlic cloves, grated'],
  ['Cut the cucumbers into batons, salt them and leave for 30 minutes.', 'Rinse and drain well.', 'Mix with the remaining ingredients and pack into a clean jar.', 'Eat after a day in the fridge; keeps for a week.']),
 ('Baking', 'Brown_Butter_Banana_Bread', 'Brown butter banana bread', ((220, 180, 120), (140, 90, 50)),
  ['banana', 'butter', 'flour', 'brown sugar', 'egg'],
  ['bread-baking'], None, None, ['easy', 'freezable'],
  ['3 very ripe bananas', '115g butter', '200g plain flour', '1 tsp bicarbonate of soda', '120g light brown sugar', '2 eggs'],
  ['Melt the butter and cook until it smells nutty and turns golden brown. Cool slightly.', 'Mash the bananas and beat in the butter, sugar and eggs.', 'Fold in the flour and bicarbonate.', 'Bake in a lined loaf tin at 175°C for 55 to 60 minutes.']),
 ('Baking', 'Rosemary_Focaccia', 'Rosemary focaccia', ((240, 220, 160), (180, 150, 90)),
  ['flour', 'yeast', 'olive oil', 'rosemary', 'sea salt'],
  ['italian', 'bread-baking'], 'italian', None, ['project', 'make-ahead'],
  ['500g strong white flour', '7g fast-action yeast', '400ml warm water', '6 tbsp olive oil', 'Rosemary sprigs and flaky salt'],
  ['Mix the flour, yeast, water and 2 tbsp oil into a wet dough; rest for 15 minutes.', 'Stretch and fold four times over an hour.', 'Cover and refrigerate overnight.', 'Spread in an oiled tin, dimple, top with rosemary, salt and oil, and bake at 230°C for 20 minutes.']),
 ('Baking', 'Lemon_Posset', 'Lemon posset', ((250, 235, 150), (230, 200, 90)),
  ['double cream', 'lemon', 'sugar'],
  ['british', 'desserts'], 'british', None, ['make-ahead', 'entertaining', 'gluten-free'],
  ['600ml double cream', '150g caster sugar', 'Juice of 2 lemons'],
  ['Bring the cream and sugar to the boil and simmer for 3 minutes.', 'Off the heat, stir in the lemon juice.', 'Pour into glasses and chill for at least 3 hours.']),
]

for i, (book, stem, title, colours, ingredients, cats, cuisine, main, tags, items, steps) in enumerate(R):
    folder = OUT / book
    (folder / '_resources').mkdir(parents=True, exist_ok=True)
    image = f'_resources/{stem}.png'
    png(folder / image, *colours)
    md = [f'---', f'created at: 2026-0{1 + i % 9}-1{i % 9} 18:30', '---', '', f'# {title}', '',
          f'![[{image}]]', '', '## Ingredients', ''] + [f'- {x}' for x in items] + ['', '## Method', ''] \
         + [f'{n}. {s}' for n, s in enumerate(steps, 1)] + ['']
    (folder / f'{stem}.md').write_text('\n'.join(md), encoding='utf-8')
    side = {'schemaVersion': 1, 'sourceFile': f'{book}/{stem}.md', 'isRecipe': True, 'cleanTitle': title,
            'categories': cats, 'cuisine': cuisine, 'mainIngredient': main, 'ingredients': ingredients,
            'tags': ['#' + t for t in tags], 'likelyDuplicateOf': None, 'confidence': 0.9, 'notes': ''}
    (folder / f'{stem}.catalogue.json').write_text(json.dumps(side, indent=2) + '\n', encoding='utf-8')

note = OUT / 'Useful Notes'
note.mkdir(parents=True, exist_ok=True)
(note / 'Oven_Temperatures.md').write_text('\n'.join([
    '# Oven temperatures', '', 'A quick conversion table.', '',
    '- 150°C conventional = 130°C fan = gas 2', '- 180°C conventional = 160°C fan = gas 4',
    '- 200°C conventional = 180°C fan = gas 6', '- 220°C conventional = 200°C fan = gas 7', '']), encoding='utf-8')
(note / 'Oven_Temperatures.catalogue.json').write_text(json.dumps({
    'schemaVersion': 1, 'sourceFile': 'Useful Notes/Oven_Temperatures.md', 'isRecipe': False,
    'cleanTitle': 'Oven temperatures', 'categories': ['notes-logs'], 'cuisine': None, 'mainIngredient': None,
    'ingredients': [], 'tags': [], 'likelyDuplicateOf': None, 'confidence': 0.95, 'notes': ''}, indent=2) + '\n')
print('done')
