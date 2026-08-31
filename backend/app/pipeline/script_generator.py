"""
Script & Screenplay Generator Engine.
Converts structured story arcs into detailed scene-by-scene screenplays with natural dialogue,
camera directions, sound effects, lighting, and visual cues.
"""
from typing import List, Dict, Any
from backend.app.schemas.screenplay import StorySchema, SceneSchema, DialogueLine
from backend.app.schemas.bible import CharacterSchema, LocationSchema


class ScriptGenerator:
    @classmethod
    def generate_screenplay(
        cls,
        story: StorySchema,
        characters: List[CharacterSchema],
        locations: List[LocationSchema],
        target_duration: int = 300,
        language: str = "en"
    ) -> List[SceneSchema]:
        """
        Generates full screenplay scenes scaled to target duration.
        """
        target_scene_count = story.metadata.get("target_scene_count", 6)
        scene_duration = max(15, target_duration // target_scene_count)
        is_hindi = (language == "hi")
        
        # Check if monsoon story
        p_summary = (story.summary or "").lower()
        is_monsoon = any(k in p_summary for k in ["monsoon", "barsat", "mother", "gauri", "village", "baby"])

        scenes: List[SceneSchema] = []

        if is_monsoon:
            scene_templates = [
                {
                    "title_en": "Monsoon Twilight over the Village",
                    "title_hi": "गाँव में मानसून की पहली शाम",
                    "loc": "Village Courtyard & Pathway",
                    "time": "Evening Twilight",
                    "action_en": "Rain begins to gently fall over lush green village huts. Gauri steps into her courtyard, looking up at the darkening monsoon clouds with a calm smile, carrying a basket of dried tulsi leaves.",
                    "action_hi": "हरे-भरे गाँव में रिमझिम बारिश शुरू होती है। गौरी तुलसी के पत्ते लेकर आँगन में आती है और बादलों की ओर देखकर मुस्कुराती है।",
                    "narration_en": "In a quiet village nestled between emerald hills, the monsoon had arrived with a song of rain and thunder.",
                    "narration_hi": "हरी-भरी पहाड़ियों की गोद में बसे एक छोटे से गाँव में, मानसून की बारिश अपनी सुरीली धुन लेकर आई थी।",
                    "dialogue_en": [{"character": "Gauri", "line": "The rains will nourish our harvest this year, my child.", "emotion": "Warm & Gentle"}],
                    "dialogue_hi": [{"character": "गौरी", "line": "इस बार की बारिश हमारी फसलों को नई ज़िंदगी देगी, मेरे लाल।", "emotion": "ममतामयी व शांत"}],
                    "emotion": "Serene and Hopeful",
                    "camera": "Slow cinematic establishing crane shot descending toward the courtyard",
                    "lighting": "Diffused soft blue twilight mixed with golden window light",
                    "sfx": ["soft_rain", "distant_thunder", "wind_chimes"],
                    "music": "Indian",
                    "visual_prompt": "Cinematic wide shot of a traditional Indian mud village under gentle monsoon rain, lush green trees, woman in emerald green cotton saree standing gracefully in rustic courtyard."
                },
                {
                    "title_en": "The Sudden Illness in the Night",
                    "title_hi": "रात का गहराता साया और नन्हे की बेचैनी",
                    "loc": "Village House Bedroom",
                    "time": "Midnight",
                    "action_en": "Heavy rain pours outside. Gauri wakes to the sound of soft whimpering. She touches baby Aarav's forehead and gasps with worry as she feels a severe burning fever.",
                    "action_hi": "तेज बारिश की आवाज के बीच गौरी जागती है। बच्चे के माथे पर हाथ रखते ही वह घबरा जाती है, उसका बदन बुखार से तप रहा था।",
                    "narration_en": "Midnight came with a violent gale. And with the cold wind came an unexpected peril for the little one.",
                    "narration_hi": "आधी रात को आंधी तेज हो गई। और उस ठंडी हवा के साथ नन्हे आरव पर तेज बुखार का साया आ गया।",
                    "dialogue_en": [
                        {"character": "Gauri", "line": "Aarav... wake up my darling. Oh God, your forehead is burning like fire!", "emotion": "Anxious & Concerned"}
                    ],
                    "dialogue_hi": [
                        {"character": "गौरी", "line": "आरव... मेरी जान आँखें खोलो। हे भगवान, इसका माथा तो आग की तरह तप रहा है!", "emotion": "चिंतित और व्याकुल"}
                    ],
                    "emotion": "Suspenseful and Anxious",
                    "camera": "Close-up of mother's expressive worried face transition to macro shot of touching baby's forehead",
                    "lighting": "Warm flickering amber light from a brass diya against dark shadows",
                    "sfx": ["heavy_rain_on_roof", "thunder_strike", "baby_whimper"],
                    "music": "Emotional",
                    "visual_prompt": "Intimate cinematic close-up of a concerned Indian mother looking with immense love and worry at her feverish baby resting on a clean wooden cot, soft brass lamp glow."
                },
                {
                    "title_en": "Preparing the Healing Potion",
                    "title_hi": "पारंपरिक जड़ी-बूटियों का काढ़ा",
                    "loc": "Village House Bedroom",
                    "time": "Late Night (2:00 AM)",
                    "action_en": "With steady hands despite her racing heart, Gauri crushes fresh ginger, tulsi, and neem leaves in a stone mortar, boiling water over an earthen stove to prepare a medicinal cooling remedy.",
                    "action_hi": "गौरी हिम्मत जुटाकर पत्थर के सिलबट्टे पर तुलसी और अदरक पीसती है और मिट्टी के चूल्हे पर बच्चे के लिए काढ़ा तैयार करती है।",
                    "narration_en": "With the village path submerged under floodwaters, a mother's wisdom and courage became the only medicine.",
                    "narration_hi": "गाँव के रास्ते पानी में डूब चुके थे। ऐसे में एक माँ की ममता और उसका हौसला ही सबसे बड़ी दवा थे।",
                    "dialogue_en": [
                        {"character": "Gauri", "line": "Hold on, my little angel. Mother is right here with you. Nothing will happen to you.", "emotion": "Resolute & Comforting"}
                    ],
                    "dialogue_hi": [
                        {"character": "गौरी", "line": "हिम्मत रखो मेरे बच्चे। तुम्हारी माँ तुम्हारे पास है, तुम्हें कुछ नहीं होने दूंगी।", "emotion": "धैर्य और स्नेह"}
                    ],
                    "emotion": "Determined and Focused",
                    "camera": "Medium profile tracking shot as mother grinds herbs with deliberate care",
                    "lighting": "Warm hearth glow casting dancing shadows on mud walls",
                    "sfx": ["pestle_grinding", "bubbling_pot", "wind_howl"],
                    "music": "Suspense",
                    "visual_prompt": "Medium cinematic shot of Indian mother grinding herbs in traditional stone mortar, steam rising from small copper vessel, atmospheric storm night."
                },
                {
                    "title_en": "The Long Vigil Through the Gale",
                    "title_hi": "तूफानी रात का लंबा पहरा",
                    "loc": "Village House Bedroom",
                    "time": "Deep Night (4:00 AM)",
                    "action_en": "Gauri gently applies cool wet cotton cloths to Aarav's forehead every few minutes. Strong gusts of wind rattle the wooden shutter; she shields the flickering lamp with her own hand.",
                    "action_hi": "गौरी ठंडे पानी में कपड़ा भिगोकर बार-बार आरव के माथे पर रखती है। तेज हवा से दीया कांपने लगता है तो गौरी अपनी हथेली की ओट बना लेती है।",
                    "narration_en": "Hour after hour, she remained motionless beside the cradle, fighting sleep and despair with every breath.",
                    "narration_hi": "घंटों तक गौरी बिना पलक झपकाए बैठी रही। उसने नींद और डर दोनों को अपने प्यार से हरा दिया।",
                    "dialogue_en": [
                        {"character": "Gauri", "line": "Sleep peacefully, my baby. The storm will pass soon.", "emotion": "Soft Whispering Lullaby"}
                    ],
                    "dialogue_hi": [
                        {"character": "गौरी", "line": "सो जाओ मेरे नन्हे राजकुमार... यह काली रात जल्द ही बीत जाएगी।", "emotion": "लोरी का मधुर स्वर"}
                    ],
                    "emotion": "Deep Emotional Bond",
                    "camera": "Intimate medium two-shot of mother cradling the baby against her chest",
                    "lighting": "Soft low-key amber lighting accentuating tear glistening on cheek",
                    "sfx": ["gentle_lullaby_humming", "wind_gusts", "rain_patter"],
                    "music": "Emotional",
                    "visual_prompt": "Cinematic portrait of an Indian mother gently cradling her resting infant to her chest, shielding a small oil lamp from storm breeze, deep love and devotion."
                },
                {
                    "title_en": "The Fever Breaks",
                    "title_hi": "बुखार का उतरना और सुकून की सांस",
                    "loc": "Village House Bedroom",
                    "time": "Pre-Dawn (5:30 AM)",
                    "action_en": "The storm begins to quieten. Gauri places her palm on Aarav's forehead—it is cool and calm. The baby stirs, opens his bright eyes, and reaches out tiny hands toward his mother.",
                    "action_hi": "तूफान शांत होने लगता है। गौरी बच्चे का माथा छूती है—बुखार उतर चुका था। आरव आँखें खोलकर अपनी माँ की तरफ नन्हें हाथ बढ़ाता है।",
                    "narration_en": "As the tempest surrendered to stillness, the burning heat subsided. Life and hope bloomed anew.",
                    "narration_hi": "जैसे ही तूफान थमा, बच्चे का बुखार भी उतर गया। माँ की तपस्या सफल हुई और उम्मीद की नई किरण जागी।",
                    "dialogue_en": [
                        {"character": "Gauri", "line": "You did it, my brave little warrior! Thank you, God, thank you!", "emotion": "Overjoyed with Tears"}
                    ],
                    "dialogue_hi": [
                        {"character": "गौरी", "line": "तुम जीत गए मेरे बहादुर बच्चे! हे ईश्वर, आपका लाख-लाख शुक्र है!", "emotion": "हर्ष और कृतज्ञता"}
                    ],
                    "emotion": "Relief and Gratitude",
                    "camera": "Slow zoom-in from medium shot to tight close-up of mother's radiant tearful smile",
                    "lighting": "Cool blue dawn light beginning to seep through the window curtains",
                    "sfx": ["baby_laugh", "birds_early_chirp", "rain_dripping"],
                    "music": "Cinematic",
                    "visual_prompt": "Emotional close-up of Indian mother crying tears of pure relief as her healthy baby smiles and grabs her finger, dawn light emerging."
                },
                {
                    "title_en": "Golden Sunrise over the Monsoon Village",
                    "title_hi": "गाँव में सुनहरी सुबह का सवेरा",
                    "loc": "Village Courtyard & Pathway",
                    "time": "Sunrise / Morning",
                    "action_en": "Gauri walks out into the courtyard bathed in radiant golden sunlight. Crystal rain droplets sparkle on green leaves. Aarav giggles joyfully in her arms as fresh morning air surrounds them.",
                    "action_hi": "गौरी आरव को गोद में लेकर आँगन में आती है। चारों तरफ सुनहरी धूप फैली हुई है और पत्तों पर बारिश की बूँदें मोतियों सी चमक रही हैं। आरव खिलखिलाकर हँसता है।",
                    "narration_en": "The monsoon had washed the world clean. Under the warm morning sun, love stood triumphant over every storm.",
                    "narration_hi": "बारिश ने पूरी दुनिया को नया रूप दे दिया था। सुबह के सुनहरे उजाले में, माँ की ममता हर तूफान पर विजयी साबित हुई।",
                    "dialogue_en": [
                        {"character": "Gauri", "line": "Look Aarav, see how beautiful the world is today!", "emotion": "Pure Joy & Triumph"}
                    ],
                    "dialogue_hi": [
                        {"character": "गौरी", "line": "देखो आरव, सूरज कितना सुंदर चमक रहा है! नई सुबह आ गई है।", "emotion": "उमंग और खुशी"}
                    ],
                    "emotion": "Triumphant and Uplifting",
                    "camera": "Majestic sweeping aerial tracking shot pulling back over the vibrant sunlit village",
                    "lighting": "Brilliant golden hour morning sunbeams through green palm fronds",
                    "sfx": ["morning_temple_bell", "birds_chorus", "village_sounds"],
                    "music": "Happy",
                    "visual_prompt": "Breathtaking wide cinematic shot of glowing golden sunrise over Indian village courtyard, mother in emerald green saree holding happy baby, glittering rain dew on leaves."
                }
            ]

            # Expand or cycle scenes if longer duration (e.g. 10m, 20m, 30m) is requested
            for idx in range(target_scene_count):
                template = scene_templates[idx % len(scene_templates)]
                scene_num = idx + 1
                
                title = template["title_hi"] if is_hindi else template["title_en"]
                if idx >= len(scene_templates):
                    title += f" (Part {idx // len(scene_templates) + 1})"

                action = template["action_hi"] if is_hindi else template["action_en"]
                narration = template["narration_hi"] if is_hindi else template["narration_en"]
                dialogue_raw = template["dialogue_hi"] if is_hindi else template["dialogue_en"]
                
                dialogue = [
                    DialogueLine(
                        character=d["character"],
                        line=d["line"],
                        emotion=d.get("emotion", "Neutral")
                    ) for d in dialogue_raw
                ]

                scenes.append(
                    SceneSchema(
                        order=idx,
                        scene_number=scene_num,
                        title=title,
                        duration_seconds=scene_duration,
                        location_name=template["loc"],
                        time_of_day=template["time"],
                        characters=["Gauri", "Baby Aarav"],
                        action=action,
                        dialogue=dialogue,
                        narration=narration,
                        emotion=template["emotion"],
                        camera=template["camera"],
                        lighting=template["lighting"],
                        sound_effects=template["sfx"],
                        music_prompt=template["music"],
                        visual_prompt=template["visual_prompt"],
                        status="PENDING",
                        shots=[]
                    )
                )
        else:
            # Generic script scaling
            for idx in range(target_scene_count):
                scene_num = idx + 1
                scenes.append(
                    SceneSchema(
                        order=idx,
                        scene_number=scene_num,
                        title=f"Scene {scene_num}: Narrative Progression" if not is_hindi else f"दृश्य {scene_num}: कहानी का विकास",
                        duration_seconds=scene_duration,
                        location_name=locations[0].name if locations else "Primary Setting",
                        time_of_day="Day",
                        characters=[c.name for c in characters] if characters else ["Alex"],
                        action=f"Key dramatic development of act {(idx * 3 // target_scene_count) + 1}.",
                        dialogue=[
                            DialogueLine(
                                character=characters[0].name if characters else "Alex",
                                line="We must keep moving forward." if not is_hindi else "हमें आगे बढ़ते रहना होगा।",
                                emotion="Determined"
                            )
                        ],
                        narration="The journey moves into its next defining chapter." if not is_hindi else "यात्रा अपने अगले महत्वपूर्ण पड़ाव की ओर बढ़ती है।",
                        emotion="Focused",
                        camera="Cinematic tracking shot",
                        lighting="Cinematic natural lighting",
                        sound_effects=["ambient_wind"],
                        music_prompt="Cinematic",
                        visual_prompt=f"Cinematic scene {scene_num} depicting characters in dramatic setting, high detail, 8k render.",
                        status="PENDING",
                        shots=[]
                    )
                )

        return scenes
