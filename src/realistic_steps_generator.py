"""
realistic_steps_generator.py — Topic-specific cooking step generator.

Generates authentic, step-by-step preparation instructions for any food topic
without requiring an external API.  Used as a deterministic fallback when
OpenRouter is unavailable so that every script contains real, actionable steps
that reflect the actual dish rather than recycled generic guidance.

Detection priority (first match wins):
  1. Baked goods / pastry
  2. Rice dishes (biryani, pulao, pilaf)
  3. Curry / masala dishes
  4. Pasta / noodles
  5. Stir-fry / wok dishes
  6. Soups & stews
  7. Grilled / barbecued / kebab dishes
  8. Roasted dishes
  9. Bread / flatbreads (naan, paratha, roti)
 10. Fried foods
 11. Protein-based: chicken, red meat, seafood, eggs
 12. Rice (plain)
 13. Legumes (dal, chana)
 14. Salads / grain bowls
 15. Generic culinary sequence

Usage::

    from src.realistic_steps_generator import generate_realistic_steps
    steps = generate_realistic_steps("chicken biryani")
    # ['Wash and soak basmati rice ...', 'Marinate chicken ...', ...]
"""

from __future__ import annotations

import re


def _extract_main_ingredient(topic: str) -> str:
    """Pull the most prominent ingredient word from the topic string.

    Returns a lower-case word such as ``'chicken'``, ``'beef'``, or the
    full topic phrase when no specific protein/ingredient is detected.
    """
    t = topic.lower()
    proteins = [
        "chicken", "beef", "lamb", "mutton", "shrimp", "prawn", "salmon",
        "fish", "pork", "turkey", "duck", "tofu", "paneer", "egg",
    ]
    for p in proteins:
        if p in t:
            return p
    grains = ["rice", "pasta", "noodle", "spaghetti", "penne", "quinoa", "barley"]
    for g in grains:
        if g in t:
            return g
    return topic.strip() or "ingredients"


# ---------------------------------------------------------------------------
# Dish-family step generators
# ---------------------------------------------------------------------------

def _steps_baking(topic: str, _t: str) -> list[str]:
    """Steps for baked goods: cakes, bread, cookies, pastries."""
    item = topic.strip() or "baked good"
    return [
        f"Preheat the oven to the temperature required for {item} — usually 170–180 °C (340–360 °F) for cakes or 200 °C (400 °F) for breads.",
        "Prepare your baking pan by greasing it with butter and lining it with parchment paper.",
        "Sift together all dry ingredients (flour, baking powder, salt) into a large bowl to aerate the mix.",
        "In a separate bowl, cream the butter and sugar with an electric mixer on medium speed for 3–4 minutes until pale and fluffy.",
        "Beat in the eggs one at a time, mixing well after each addition to prevent curdling.",
        "Fold the dry ingredients into the wet mixture in three additions, alternating with any liquid; stir gently — over-mixing develops gluten and toughens the result.",
        f"Pour the batter into the prepared pan and smooth the top; bake until a skewer inserted in the centre of the {item} comes out clean.",
        "Allow to cool in the pan for 10 minutes, then transfer to a wire rack to cool completely before decorating or serving.",
    ]


def _steps_biryani(topic: str, _t: str) -> list[str]:
    """Steps for biryani / pulao / pilaf-style layered rice dishes."""
    protein = _extract_main_ingredient(topic)
    has_protein = protein not in ("rice",)
    marinate_line = (
        f"Marinate the {protein} in yogurt, lemon juice, ginger-garlic paste, and a blend of"
        " biryani spices (cumin, coriander, chilli, garam masala) for at least 1 hour, or overnight for deeper flavour."
        if has_protein
        else "Prepare the vegetable mixture: dice vegetables, toss with yogurt, spices, and ginger-garlic paste, and set aside."
    )
    cook_line = (
        f"Cook the {protein} in oil on high heat (bhunao technique) until the oil separates from the masala and the {protein} is sealed."
        if has_protein
        else "Sauté the spiced vegetables in oil over high heat until well coated and fragrant, about 8 minutes."
    )
    return [
        "Wash the basmati rice under cold water until it runs clear, then soak for 30 minutes — soaking prevents breakage and ensures long, separate grains.",
        marinate_line,
        "Slice two large onions very thinly and fry in hot oil until deep golden-brown (birista); drain on paper towels — these add the signature biryani sweetness.",
        cook_line,
        "Parboil the soaked rice in generously salted boiling water for exactly 6–7 minutes; the grains should be 70 % cooked and still have a firm white core.",
        "Layer the par-cooked rice over the masala/protein in the pot; drizzle saffron dissolved in warm milk and scatter the crispy fried onions over the top.",
        "Seal the pot with a tight lid (or foil then lid) and cook on dum: 2 minutes on high heat, then 20 minutes on the lowest flame using a heat diffuser.",
        "Gently fold from the bottom before serving to mix the layers without breaking the grains; garnish with fresh coriander and serve with raita.",
    ]


def _steps_curry(topic: str, _t: str) -> list[str]:
    """Steps for curry, karahi, korma, masala, and similar saucy dishes."""
    protein = _extract_main_ingredient(topic)
    item_line = (
        f"Add the {protein} pieces to the masala and cook (bhunao) on high heat, stirring constantly, until the {protein} is sealed and the oil rises to the surface."
        if protein not in ("ingredients",)
        else "Add the main protein or vegetables and cook on high heat, stirring until well coated in the masala."
    )
    return [
        "Heat oil or ghee in a heavy-based pot over medium-high heat; add whole spices (cumin seeds, cardamom, bay leaf, cloves) and let them sizzle for 30 seconds to bloom.",
        "Add finely diced onions and fry, stirring frequently, until deep golden-brown — about 12–15 minutes; this caramelised base is the foundation of deep flavour.",
        "Stir in ginger-garlic paste and cook for 2 minutes until the raw smell disappears completely.",
        "Add pureed or finely chopped tomatoes and cook on medium heat, mashing as they soften, until the masala thickens and oil pools around the edges (8–10 minutes).",
        "Mix in ground spices (coriander, cumin, turmeric, chilli powder) and stir for 1 minute so they toast in the oil rather than steaming in liquid.",
        item_line,
        "Add water or stock to reach your desired consistency; cover and simmer on low heat for 15–25 minutes until the protein is fully tender.",
        "Finish with garam masala, a squeeze of lemon, and a generous handful of fresh coriander; taste and adjust salt before serving.",
    ]


def _steps_pasta(topic: str, _t: str) -> list[str]:
    """Steps for pasta dishes."""
    sauce_hint = ""
    t = topic.lower()
    if "carbonara" in t:
        sauce_hint = "carbonara — whisk egg yolks, Pecorino Romano, and cracked black pepper into a silky sauce"
    elif "arrabbiata" in t or "tomato" in t:
        sauce_hint = "tomato-based sauce — crush canned San Marzano tomatoes and simmer with chilli and garlic"
    elif "pesto" in t:
        sauce_hint = "pesto — blend fresh basil, pine nuts, Parmesan, garlic, and olive oil until smooth"
    elif "bolognese" in t or "ragù" in t or "ragu" in t:
        sauce_hint = "ragù — brown mince in batches and simmer with wine and tomatoes for 45 minutes"
    elif "alfredo" in t or "cream" in t:
        sauce_hint = "cream sauce — reduce heavy cream with Parmesan until it coats the back of a spoon"

    sauce_step = (
        f"Prepare the {sauce_hint}."
        if sauce_hint
        else f"Prepare the {topic.strip()} sauce while the water heats: build the flavour base in a wide pan over medium heat."
    )
    return [
        "Bring a large pot of water to a rolling boil and season it as generously as the sea — about 10 g of salt per litre of water.",
        sauce_step,
        "Heat 2 tablespoons of olive oil in a wide skillet over medium-low; gently cook minced garlic for 60 seconds until fragrant but not brown.",
        "Add the pasta to the boiling water and cook for 1 minute less than the packet instructions — it will finish cooking in the sauce.",
        "Reserve 200 ml of the starchy pasta cooking water before draining; this liquid is your secret weapon for silky sauce.",
        "Drain the pasta and transfer it directly to the skillet; add the sauce and toss vigorously over medium heat.",
        "Add reserved pasta water a splash at a time, tossing and folding until the sauce emulsifies and clings to every strand.",
        "Remove from heat, finish with grated Parmesan, freshly cracked pepper, and a drizzle of high-quality olive oil; serve immediately.",
    ]


def _steps_stir_fry(topic: str, _t: str) -> list[str]:
    """Steps for stir-fry and wok dishes."""
    protein = _extract_main_ingredient(topic)
    protein_line = (
        f"Slice the {protein} thinly against the grain; marinate in soy sauce, cornstarch, and a splash of Shaoxing wine for 15 minutes."
        if protein not in ("ingredients",)
        else "Slice all proteins and vegetables into uniform pieces for even, fast cooking."
    )
    return [
        "Mise en place first — prepare every ingredient before you turn on the heat, because stir-frying moves too fast to stop and chop.",
        protein_line,
        "Mix the stir-fry sauce in a small bowl: soy sauce, oyster sauce, sesame oil, cornstarch, and a pinch of sugar — set aside within arm's reach.",
        "Heat a wok over the highest flame possible for 2 full minutes until it begins to smoke; swirl in a tablespoon of high-smoke-point oil.",
        f"Add the {protein} in a single layer and cook without stirring for 90 seconds to get proper char (wok hei); stir and toss until cooked through, then remove.",
        "Add a little more oil and flash-fry vegetables, starting with the hardest (carrots, broccoli) and finishing with the most delicate (bean sprouts, leafy greens).",
        f"Return the {protein} to the wok, pour in the sauce, and toss everything together over high heat for 60 seconds until glossy and fragrant.",
        "Finish with a few drops of sesame oil, a scatter of sesame seeds or spring onion, and serve immediately over steamed jasmine rice.",
    ]


def _steps_soup_stew(topic: str, _t: str) -> list[str]:
    """Steps for soups, stews, broths, and slow-cooked dishes like nihari/haleem."""
    protein = _extract_main_ingredient(topic)
    protein_line = (
        f"Add the {protein} and brown it on all sides in batches — never crowd the pot, or it steams instead of searing."
        if protein not in ("ingredients",)
        else "Add the main protein or vegetables and sear until lightly browned on all sides."
    )
    is_slow = any(w in topic.lower() for w in ["nihari", "haleem", "stew", "slow"])
    simmer_time = "3–4 hours (or overnight on the lowest heat for nihari/haleem)" if is_slow else "25–35 minutes"
    return [
        "Heat a tablespoon of oil or ghee in a heavy pot over medium-high heat; add whole spices or aromatics (onion, celery, carrot) and cook until softened, about 5 minutes.",
        protein_line,
        "Deglaze the pot with a splash of stock, wine, or water; use a wooden spoon to scrape up all the browned bits — that fond is concentrated flavour.",
        "Add remaining vegetables, tomatoes, or paste; stir to combine and cook for 3–4 minutes before adding the main liquid.",
        "Pour in the stock or water, season generously with salt, pepper, and any signature spices; bring to a boil, then skim any foam that rises to the surface.",
        f"Reduce heat to a gentle simmer, cover the pot partially, and cook for {simmer_time} until the flavours meld and the protein is completely tender.",
        "Taste and correct the seasoning; if the broth is thin, remove the lid and simmer uncovered for 10 minutes to concentrate it.",
        "Ladle into bowls and finish with fresh herbs, a swirl of cream or yogurt, or a squeeze of lemon to brighten the flavour.",
    ]


def _steps_grilling(topic: str, _t: str) -> list[str]:
    """Steps for grilled, barbecued, and skewer/kebab dishes."""
    protein = _extract_main_ingredient(topic)
    is_kebab = any(w in topic.lower() for w in ["kebab", "kabab", "seekh", "chapli", "tikka", "skewer"])
    if is_kebab:
        return [
            f"Combine minced or cubed {protein} with ginger-garlic paste, yogurt, and a full spice blend (cumin, coriander, chilli, garam masala); mix thoroughly and refrigerate for at least 2 hours.",
            "Wet your hands and shape the mixture firmly onto flat metal skewers or form small patties; press tightly so they hold their shape during cooking.",
            "Preheat the grill or griddle pan to the highest temperature possible; brush the grate or pan lightly with oil to prevent sticking.",
            "Place the kebabs and cook undisturbed for 3–4 minutes until they release naturally and develop a charred crust on one side.",
            "Flip once and cook the other side for 3–4 minutes; the kebabs are done when they feel firm and reach an internal temperature of 74 °C (165 °F) for poultry.",
            "Rest for 3 minutes before serving; the juices will redistribute back into the meat.",
            "Serve on a platter with sliced onion, naan or paratha, and a squeeze of lemon; drizzle with green chutney or raita.",
        ]
    return [
        f"Marinate the {protein} in oil, lemon juice, herbs, and spices for at least 30 minutes (up to overnight) to tenderise and infuse flavour.",
        f"Remove the {protein} from the refrigerator 20 minutes before cooking to allow it to come to room temperature — cold protein cooks unevenly.",
        "Preheat the grill to high heat (230–260 °C / 450–500 °F); clean the grates and brush with oil just before placing the food down.",
        f"Place the {protein} on the grill and close the lid; cook without moving for the first 3–4 minutes to develop grill marks and prevent sticking.",
        "Flip once using tongs (not a fork — piercing releases juices); grill the second side until the internal temperature reaches the safe minimum for the protein.",
        f"Rest the {protein} on a warm plate, loosely tented with foil, for 5 minutes; resting allows the muscle fibres to relax and reabsorb their juices.",
        "Slice, garnish with fresh herbs or a citrus wedge, and serve immediately for the best texture and flavour.",
    ]


def _steps_roasting(topic: str, _t: str) -> list[str]:
    """Steps for oven-roasted dishes."""
    protein = _extract_main_ingredient(topic)
    return [
        "Preheat the oven to 220 °C (425 °F) for the initial high-heat blast that creates a golden crust.",
        f"Pat the {protein} completely dry with paper towels — moisture is the enemy of browning; season generously with salt, pepper, and any dry rub.",
        "Rub the surface with olive oil or softened butter, then press on minced garlic, herbs (rosemary, thyme), and any aromatics.",
        f"Place the {protein} on a rack inside a roasting tin so hot air circulates all the way around; tuck vegetables underneath to catch the dripping juices.",
        f"Roast at 220 °C for the first 15–20 minutes to develop colour, then reduce to 180 °C (350 °F) and continue until the {protein} reaches the correct internal temperature.",
        "Baste every 20 minutes with the pan drippings to keep the surface moist and lacquered.",
        f"Rest the {protein} on a carving board for at least 10–15 minutes before slicing — the internal temperature will rise a few degrees during resting.",
        "Use the roasting tin juices to make a quick pan sauce or gravy; deglaze with wine or stock and simmer for 3 minutes.",
    ]


def _steps_flatbread(topic: str, _t: str) -> list[str]:
    """Steps for naan, paratha, roti, chapati, puri, and pizza dough."""
    t = topic.lower()
    is_layered = any(w in t for w in ["paratha", "laccha", "flaky"])
    is_pizza = "pizza" in t
    leavening = "instant yeast" if (is_pizza or "naan" in t) else "no leavening needed"
    rest_note = "Rest the dough for 60 minutes (or 8 hours in the fridge) for the best flavour and texture." if (is_pizza or "naan" in t) else "Rest the dough covered for 20–30 minutes so the gluten relaxes."
    cook_method = "Bake in a preheated oven at 250 °C (480 °F) on a hot pizza stone or steel for 8–10 minutes." if is_pizza else "Heat a tawa or cast-iron skillet over high heat until very hot; cook each piece until bubbles form, then press gently and flip."
    laminate_step = (
        "Roll each portion into a thin disc, spread with ghee or butter, fold like a letter, and re-roll to create flaky, laminated layers."
        if is_layered
        else "Roll each portion into a thin, even circle on a lightly floured surface."
    )
    return [
        f"Combine flour, salt, and {leavening} in a large bowl; make a well in the centre.",
        "Pour in warm water (and yogurt for naan) gradually, mixing with your hands until a shaggy dough forms; add water one tablespoon at a time if needed.",
        "Knead on a floured surface for 8–10 minutes until the dough is smooth, elastic, and springs back when pressed — proper kneading develops the gluten network.",
        rest_note,
        "Divide the dough into equal portions; cover the ones you are not working with so they do not dry out.",
        laminate_step,
        cook_method,
        "Brush immediately with melted butter or ghee while still hot; serve warm for the best texture and flavour.",
    ]


def _steps_frying(topic: str, _t: str) -> list[str]:
    """Steps for deep-fried and shallow-fried dishes."""
    protein = _extract_main_ingredient(topic)
    is_deep = any(w in topic.lower() for w in ["deep fry", "deep-fry", "pakora", "samosa", "puri", "doughnut"])
    oil_depth = "enough oil to fully submerge the food (at least 3–4 cm deep)" if is_deep else "a shallow layer of oil (about 1 cm deep)"
    temp = "170–180 °C (340–355 °F)" if is_deep else "160–170 °C (320–340 °F)"
    return [
        f"Prepare the coating: mix together the dry coating (breadcrumbs, flour, or chickpea batter) and season generously; pat the {protein} completely dry first.",
        f"Coat the {protein} evenly in the prepared coating, pressing firmly so it adheres; refrigerate for 15 minutes to set the crust.",
        f"Pour {oil_depth} into a heavy-bottomed pot or deep pan; heat over medium-high to {temp} — test with a wooden skewer: small bubbles should rise immediately.",
        f"Carefully lower the {protein} away from you into the oil; do not overcrowd — fry in batches of 2–3 pieces to maintain the oil temperature.",
        "Fry undisturbed until the coating turns a deep golden colour; flip once and fry the second side to match.",
        "Remove with a slotted spoon and drain on a wire rack (not paper towels, which trap steam and soften the crust).",
        "Season immediately while piping hot — salt sticks best right out of the oil.",
        "Serve with a dipping sauce or fresh lemon within 5 minutes for maximum crunch.",
    ]


def _steps_chicken(topic: str, _t: str) -> list[str]:
    """Generic chicken preparation steps."""
    return [
        "Pat the chicken pieces completely dry with paper towels — surface moisture is the single biggest obstacle to crispy skin and good browning.",
        "Score the thickest parts of the chicken with a sharp knife so the marinade or seasoning penetrates deeper into the meat.",
        "Coat with oil, then rub a spice mix (paprika, garlic powder, onion powder, salt, pepper) all over, including underneath the skin.",
        "Heat a wide skillet or oven-proof pan over medium-high heat until it just starts to smoke; add oil and swirl to coat.",
        "Place the chicken skin-side down and cook without moving for 6–8 minutes until a deep golden-brown crust forms and the chicken releases naturally.",
        "Flip the chicken, reduce heat to medium, and cook through — basting occasionally with the rendered fat in the pan.",
        "Check doneness with an instant-read thermometer: 74 °C (165 °F) at the thickest part with no pink near the bone.",
        "Rest for 5 minutes on a warm plate before cutting so the juices redistribute throughout the meat.",
    ]


def _steps_red_meat(topic: str, _t: str) -> list[str]:
    """Generic steps for beef, lamb, and other red meat."""
    is_steak = any(w in topic.lower() for w in ["steak", "chop"])
    if is_steak:
        return [
            "Remove the steak from the refrigerator 30–45 minutes before cooking so it reaches room temperature — cold steak cooks unevenly.",
            "Pat the surface very dry with paper towels; season generously with coarse salt and cracked black pepper on both sides and the edges.",
            "Heat a cast-iron skillet over the highest flame possible for at least 3 minutes until it begins to smoke slightly.",
            "Add a thin layer of high-smoke-point oil; carefully lay the steak away from you in the pan — it should sear loudly immediately.",
            "Cook without pressing or moving for 2–3 minutes per side for medium-rare; tilt the pan and baste continuously with butter, garlic, and thyme.",
            "Finish by searing the fat cap and edges briefly on each side.",
            "Transfer to a warm plate and rest for at least half the cooking time — a 3-minute cook needs 1.5 minutes of rest minimum.",
            "Slice against the grain with a sharp knife and serve immediately with a finishing pinch of flaky salt.",
        ]
    protein = _extract_main_ingredient(topic)
    return [
        f"Cut the {protein} into even-sized pieces (3–4 cm cubes for stewing, thinner for stir-fries); season well with salt and pepper.",
        "Bring the meat to room temperature for 20–30 minutes before cooking for more even results.",
        "Heat oil in a heavy pan over high heat; sear the meat in batches without crowding — proper browning (Maillard reaction) creates the deep flavour base.",
        "Once all the meat is seared, add aromatics (onion, garlic, ginger) and cook until softened.",
        "Deglaze with stock, wine, or water, scraping up all the caramelised bits stuck to the bottom of the pan.",
        "Add spices, sauce, or braising liquid and bring to a simmer; cover and cook on low heat until the meat is fork-tender.",
        "Uncover for the last 10 minutes to reduce the sauce to the correct consistency.",
        "Taste, adjust seasoning, and finish with fresh herbs or a squeeze of lemon before serving.",
    ]


def _steps_seafood(topic: str, _t: str) -> list[str]:
    """Steps for fish, salmon, and shellfish."""
    t = topic.lower()
    is_shrimp = any(w in t for w in ["shrimp", "prawn"])
    if is_shrimp:
        return [
            "Peel and devein the shrimp; rinse under cold water and pat dry with paper towels.",
            "Season with salt, pepper, garlic powder, and a pinch of cayenne or paprika.",
            "Heat a wide skillet over high heat until very hot; add oil and let it shimmer.",
            "Add the shrimp in a single layer — do not crowd the pan or they will steam instead of sear.",
            "Cook for exactly 90 seconds per side: shrimp are done when they turn pink-orange and curl into a loose 'C' shape; a tight 'O' means overcooked.",
            "Add a knob of butter, minced garlic, and a splash of white wine or lemon juice; toss to coat.",
            "Garnish with fresh parsley and serve immediately — shrimp go rubbery very quickly if left to sit.",
        ]
    protein = _extract_main_ingredient(topic)
    return [
        f"Pat the {protein} fillet completely dry with paper towels — this is the single most important step for preventing sticking and achieving a crispy skin.",
        f"Season the {protein} with salt and pepper just before cooking; salting too early draws moisture out.",
        "Heat a stainless-steel or cast-iron skillet over medium-high heat; add oil with a high smoke point (avocado, grapeseed) and heat until shimmering.",
        f"Place the {protein} presentation-side (skin-side) down and immediately press gently for 10 seconds with a spatula to prevent curling.",
        "Cook without moving for 3–4 minutes until the flesh turns opaque 70 % of the way up the side.",
        "Flip once using a thin spatula; cook for 1–2 more minutes (the fish should flake easily with a fork but still be moist in the centre).",
        "Add a knob of butter to the pan and baste the fish as it finishes; squeeze half a lemon over the top.",
        "Serve immediately — fish continues to cook from residual heat, so plate it the moment it reaches doneness.",
    ]


def _steps_eggs(topic: str, _t: str) -> list[str]:
    """Steps for egg-based dishes."""
    t = topic.lower()
    if "scramble" in t or "scrambled" in t:
        return [
            "Crack the eggs into a bowl and whisk with a pinch of salt; whisk until the yolks and whites are completely combined with no streaks.",
            "Heat a non-stick pan over the lowest possible heat; add a generous knob of cold butter.",
            "Pour in the eggs and let them sit undisturbed for 20 seconds until the edges just begin to set.",
            "Using a silicone spatula, gently push the set edges toward the centre; let the liquid run to the edges and set again.",
            "Repeat this slow push-and-wait technique for 3–4 minutes — low and slow is the secret to creamy scrambled eggs.",
            "Remove from the heat while the eggs still look slightly underdone; residual heat will finish them to a silky, custardy consistency.",
            "Season with cracked black pepper, fresh chives, and an optional small amount of crème fraîche or cream cheese for extra richness.",
        ]
    if "poach" in t or "poached" in t:
        return [
            "Bring a wide, deep pan of water to a gentle simmer (80–85 °C); add a splash of white vinegar to help the whites coagulate quickly.",
            "Crack each egg into a small cup or ramekin first — never crack directly into the water.",
            "Create a gentle whirlpool in the water with a spoon, then slide the egg into the centre.",
            "Poach for exactly 3 minutes for a runny yolk, 4 minutes for a jammy yolk; do not let the water boil.",
            "Lift with a slotted spoon, blot the bottom dry on a clean cloth, and season with salt and pepper.",
            "Serve immediately on toasted bread, smoked salmon, or wilted greens.",
        ]
    # Omelette / frittata / generic
    return [
        "Crack 2–3 eggs per serving into a bowl, add a tablespoon of water or milk, and whisk until uniform.",
        "Heat a non-stick pan over medium-high heat; add butter and let it foam then subside — this is the correct temperature.",
        "Pour in the eggs; shake the pan gently and push the set edges toward the centre with a spatula.",
        "Add fillings (cheese, herbs, vegetables) to one half while the centre is still slightly liquid.",
        "Fold the unfilled half over the filled half; the residual heat will finish setting the eggs.",
        "Slide onto a warm plate and season with salt, pepper, and fresh herbs; serve within 2 minutes for the best texture.",
    ]


def _steps_rice(topic: str, _t: str) -> list[str]:
    """Steps for plain rice preparation."""
    is_fried = "fried" in topic.lower()
    if is_fried:
        return [
            "Start with day-old cold cooked rice — freshly cooked rice is too moist and will clump; the dried surface is key to separated fried rice grains.",
            "Beat 2 eggs lightly with a pinch of salt and scramble them in the hot wok first; remove and set aside.",
            "Add vegetables (peas, carrots, corn) to the hot oiled wok and stir-fry for 2 minutes.",
            "Add the cold rice, pressing and spreading it across the hot wok surface; do not stir for 60 seconds so the bottom grains begin to crisp.",
            "Toss vigorously and add soy sauce, oyster sauce, and a pinch of white pepper; fold in the scrambled eggs.",
            "Stir-fry on the highest heat for 2–3 minutes until every grain is separate, glossy, and fragrant.",
            "Finish with a drizzle of sesame oil and sliced spring onions; serve immediately.",
        ]
    return [
        "Rinse the rice in cold water 3–4 times, swirling with your hand until the water runs almost clear — removing excess surface starch prevents clumping.",
        "Soak the rice in cold water for 20–30 minutes for fluffier, more separate grains; drain before cooking.",
        "Combine rice with the correct water ratio (1 : 1.5 for basmati, 1 : 1.75 for long-grain white) and a pinch of salt in a heavy-bottomed pot.",
        "Bring to a full boil over high heat uncovered; as soon as it boils, reduce heat to the absolute minimum and cover tightly.",
        "Cook undisturbed for 12 minutes (basmati) to 15 minutes (long-grain); resist the urge to lift the lid and let the steam escape.",
        "Remove from heat and leave the pot covered for 5 minutes to allow the rice to steam-finish in its own heat.",
        "Fluff gently with a fork from the edges inward; every grain should be separate, fluffy, and cooked through.",
    ]


def _steps_legumes(topic: str, _t: str) -> list[str]:
    """Steps for dal, chana, lentil, and bean dishes."""
    t = topic.lower()
    is_chana = any(w in t for w in ["chana", "chickpea", "chole"])
    protein = "chickpeas" if is_chana else "lentils"
    soak_note = "Soak chickpeas overnight (8–12 hours) in plenty of cold water; they will nearly double in size." if is_chana else "No soaking required for red or split lentils; rinse under cold water and pick out any debris."
    cook_time = "45–60 minutes in a pot (or 20 minutes in a pressure cooker)" if is_chana else "20–25 minutes until completely soft"
    return [
        soak_note,
        f"Rinse the {protein} thoroughly; if using soaked chickpeas, drain and cover with fresh water before cooking.",
        f"Boil the {protein} with turmeric and salt for {cook_time}; skim any foam that rises in the first 5 minutes.",
        "For the tarka (tempering): heat ghee or oil in a small pan until very hot; add cumin seeds and let them sizzle for 30 seconds.",
        "Add finely diced onion to the tarka and cook until golden-brown; add ginger-garlic paste and cook for 2 more minutes.",
        "Stir in tomatoes, chilli, coriander powder, and garam masala; cook until the oil separates from the masala (about 8 minutes).",
        f"Add the cooked {protein} to the tarka, mix well, and simmer together for 10 minutes so the flavours marry.",
        "Finish with a squeeze of lemon juice, fresh coriander, and an optional final tarka of butter with dried chilli for richness and heat.",
    ]


def _steps_salad(topic: str, _t: str) -> list[str]:
    """Steps for salads, grain bowls, and composed plates."""
    return [
        f"Wash and thoroughly dry all salad greens and vegetables for {topic.strip()}; wet leaves dilute the dressing and make it slide off.",
        "Prepare any cooked components (grains, roasted vegetables, proteins) and allow to cool before assembling — heat wilts fresh greens.",
        "Make the dressing: whisk together acid (lemon juice or vinegar) and oil in a 1 : 3 ratio; add salt, pepper, a teaspoon of mustard as an emulsifier, and any herbs.",
        "Season individual components before they go into the bowl — under-seasoning is the most common salad mistake.",
        "Dress the greens lightly just before serving; add the dressing in small amounts and toss with clean hands for even, gentle coating.",
        "Arrange components with height and colour contrast in mind — place the most visually appealing elements on top.",
        "Add any crunchy garnish (nuts, seeds, croutons) at the very last moment so they stay crisp.",
        "Taste, adjust salt and acid balance, and serve within 5 minutes of dressing.",
    ]


def _steps_generic(topic: str) -> list[str]:
    """Fallback steps that follow the universal culinary sequence."""
    item = topic.strip() or "this dish"
    return [
        f"Mise en place: measure, chop, and prepare all ingredients for {item} before turning on any heat — once cooking starts, things move quickly.",
        "Prepare the base flavour: heat oil or butter in your cooking vessel over medium heat and add aromatics (onion, garlic, ginger) to build the flavour foundation.",
        "Add the main protein or primary vegetables; cook on high heat first to develop colour and seal in the juices, then reduce heat to finish cooking through.",
        "Build the sauce or cooking liquid by adding tomatoes, stock, or water; scrape any caramelised bits from the bottom of the pan — that is concentrated flavour.",
        "Season in layers: add salt, spices, and herbs at multiple stages rather than all at the end; taste as you go and adjust accordingly.",
        f"Finish {item} with a balancing acid (lemon juice or vinegar) and a finishing fat (butter, olive oil, or cream) to round out the flavours.",
        "Garnish with fresh herbs, a drizzle of high-quality oil, or a sprinkle of flaky salt just before plating.",
        "Taste one final time and plate with intention — the visual presentation sets expectations for the first bite.",
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_realistic_steps(topic: str) -> list[str]:
    """Generate authentic, topic-specific preparation steps for *topic*.

    Analyses the topic string to detect cuisine, cooking method, and primary
    ingredients, then returns a list of 6–8 concrete, actionable preparation
    steps that follow the standard culinary sequence:
    mise en place → primary prep → cooking → finishing.

    This function is purely deterministic (no API calls) and is intended as
    a high-quality fallback when OpenRouter is unavailable.

    Args:
        topic: The food dish or topic, e.g. ``"chicken biryani"`` or
               ``"chocolate lava cake"``.

    Returns:
        A list of step strings, each a complete, actionable instruction.
    """
    t = topic.lower().strip()
    t = re.sub(r"\s+", " ", t)

    # --- Baked goods / pastry -------------------------------------------------
    if any(w in t for w in [
        "bake", "baked", "cake", "bread", "cookie", "cookies", "muffin",
        "brownie", "tart", "pie", "scone", "croissant", "pastry",
        "cheesecake", "loaf",
    ]):
        return _steps_baking(topic, t)

    # --- Rice-based layered dishes -------------------------------------------
    if any(w in t for w in [
        "biryani", "biriyani", "pulao", "pilaf", "pilau", "palaw", "kabuli",
        "qabuli",
    ]):
        return _steps_biryani(topic, t)

    # --- Curry / masala / saucy dishes ----------------------------------------
    if any(w in t for w in [
        "curry", "karahi", "korma", "masala", "nihari", "haleem",
        "tikka masala", "butter chicken", "palak", "saag", "qorma", "shorwa",
        "makhani",
    ]):
        return _steps_curry(topic, t)

    # --- Pasta / noodles -------------------------------------------------------
    if any(w in t for w in [
        "pasta", "spaghetti", "fettuccine", "penne", "rigatoni", "linguine",
        "tagliatelle", "carbonara", "bolognese", "alfredo", "arrabbiata",
        "lasagne", "lasagna", "ramen", "udon", "lo mein",
    ]):
        return _steps_pasta(topic, t)

    # --- Stir-fry / wok -------------------------------------------------------
    if any(w in t for w in [
        "stir fry", "stir-fry", "stirfry", "wok", "fried rice", "chow mein",
        "pad thai",
    ]):
        return _steps_stir_fry(topic, t)

    # --- Soups & stews ---------------------------------------------------------
    if any(w in t for w in [
        "soup", "stew", "broth", "chowder", "bisque", "shorwa", "nihari",
        "haleem", "pho", "ramen",
    ]):
        return _steps_soup_stew(topic, t)

    # --- Grilled / barbecued / kebabs -----------------------------------------
    if any(w in t for w in [
        "grill", "grilled", "barbecue", "bbq", "kebab", "kabab", "kabob",
        "seekh", "chapli", "tikka", "skewer", "satay", "tandoori",
    ]):
        return _steps_grilling(topic, t)

    # --- Roasted dishes -------------------------------------------------------
    if any(w in t for w in ["roast", "roasted", "oven baked", "oven-baked"]):
        return _steps_roasting(topic, t)

    # --- Flatbreads -----------------------------------------------------------
    if any(w in t for w in [
        "naan", "paratha", "roti", "chapati", "chapatti", "puri", "poori",
        "flatbread", "tortilla", "pizza dough", "bolani",
    ]):
        return _steps_flatbread(topic, t)

    # --- Fried foods ---------------------------------------------------------
    if any(w in t for w in [
        "fry", "fried", "deep fry", "deep-fry", "crispy", "batter",
        "pakora", "bhaji", "fritter", "tempura", "samosa",
    ]):
        return _steps_frying(topic, t)

    # --- Protein-first detection ----------------------------------------------
    if any(w in t for w in ["chicken", "poultry"]):
        return _steps_chicken(topic, t)

    if any(w in t for w in [
        "beef", "steak", "lamb", "mutton", "mince", "minced", "ground beef",
        "keema", "kheema",
    ]):
        return _steps_red_meat(topic, t)

    if any(w in t for w in [
        "fish", "salmon", "tuna", "shrimp", "prawn", "seafood", "cod",
        "halibut", "tilapia", "bass", "trout",
    ]):
        return _steps_seafood(topic, t)

    if any(w in t for w in [
        "egg", "eggs", "omelette", "omelet", "scramble", "scrambled",
        "poach", "poached", "frittata",
    ]):
        return _steps_eggs(topic, t)

    if any(w in t for w in ["rice", "basmati", "jasmine rice", "white rice"]):
        return _steps_rice(topic, t)

    if any(w in t for w in [
        "dal", "daal", "dhal", "lentil", "chana", "chickpea", "chole",
        "beans", "rajma",
    ]):
        return _steps_legumes(topic, t)

    if any(w in t for w in ["salad", "slaw", "bowl", "grain bowl"]):
        return _steps_salad(topic, t)

    # --- Generic fallback -----------------------------------------------------
    return _steps_generic(topic)
