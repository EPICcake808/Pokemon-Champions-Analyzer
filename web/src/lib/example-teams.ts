import "server-only";

import { CATALOG_DEFAULT_REGULATION_ID, DEFAULT_REGULATION_ID } from "@/lib/python-analyzer";
import type { ExampleTeam } from "@/lib/types";

const FEATURED_EXAMPLES: ExampleTeam[] = [
  {
    slug: "sample-team",
    title: "Curated Sample",
    note: "Regulation M-B rain Tailwind shell with layered support turns and flexible speed control.",
    // Tagged with the current default regulation so the app's first load lands on M-B.
    regulationId: CATALOG_DEFAULT_REGULATION_ID,
        teamText: `Mega Lucario @ Lucarionite
Ability: Adaptability
Level: 50
EVs: 32 HP / 32 Def / 2 Spe
Bold Nature
- Aura Sphere
- Detect
- Calm Mind
- Dark Pulse

Sableye @ Roseli Berry
Ability: Prankster
Level: 50
EVs: 32 HP / 9 Def / 25 SpD
Sassy Nature
- Rain Dance
- Quash
- Light Screen
- Reflect

Archaludon @ Leftovers
Ability: Stamina
Level: 50
EVs: 32 HP / 1 Def / 5 SpA / 25 SpD / 3 Spe
Modest Nature
- Electro Shot
- Dragon Pulse
- Flash Cannon
- Protect

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
EVs: 31 HP / 7 Def / 28 SpD
Sassy Nature
- Matcha Gotcha
- Rage Powder
- Life Dew
- Protect

Basculegion (Male) @ Choice Scarf
Ability: Adaptability
Level: 50
EVs: 32 Atk / 2 Def / 32 Spe
Jolly Nature
- Last Respects
- Aqua Jet
- Wave Crash
- Psychic Fangs

Aerodactyl @ Focus Sash
Ability: Unnerve
Level: 50
EVs: 32 Atk / 2 SpD / 32 Spe
Jolly Nature
- Rock Slide
- Tailwind
- Dual Wingbeat
- Wide Guard`,
  },
  {
    slug: "hyper-offense",
    title: "Whimsicott Glimmora",
        note: "Fast current-field offense built around Whimsicott support, Glimmora chip, and Mega Charizard Y pressure.",
    regulationId: DEFAULT_REGULATION_ID,
    teamText: `Whimsicott @ Focus Sash
Ability: Prankster
Level: 50
EVs: 10 HP / 24 SpA / 32 Spe
Timid Nature
- Tailwind
- Encore
- Moonblast
- Protect

Glimmora @ Poison Barb
Ability: Toxic Debris
Level: 50
EVs: 10 HP / 32 SpA / 24 Spe
Timid Nature
- Stealth Rock
- Power Gem
- Sludge Wave
- Earth Power

Charizard @ Charizardite Y
Ability: Blaze
Level: 50
EVs: 2 Def / 32 SpA / 32 Spe
Timid Nature
- Heat Wave
- Air Slash
- Solar Beam
- Protect

Garchomp @ Soft Sand
Ability: Rough Skin
Level: 50
EVs: 18 HP / 32 Atk / 2 Def / 14 Spe
Adamant Nature
- Dragon Claw
- Rock Slide
- Protect
- Stomping Tantrum

Basculegion (M) @ Choice Scarf
Ability: Adaptability
Level: 50
EVs: 32 Atk / 2 Def / 32 Spe
Jolly Nature
- Last Respects
- Aqua Jet
- Wave Crash
- Psychic Fangs

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
EVs: 32 HP / 32 Atk / 2 Spe
Adamant Nature
- Kowtow Cleave
- Protect
- Sucker Punch
- Iron Head`,
  },
  {
    slug: "trick-room",
    title: "Farigiraf Torkoal Room",
    note: "Established Trick Room pressure shell with redirection, healing, and hard sun turns.",
    regulationId: DEFAULT_REGULATION_ID,
    teamText: `Farigiraf @ Sitrus Berry
Ability: Armor Tail
Level: 50
EVs: 32 HP / 15 Def / 19 SpA
Modest Nature
- Trick Room
- Psychic
- Dazzling Gleam
- Protect

Torkoal @ Charcoal
Ability: Drought
Level: 50
EVs: 32 HP / 32 SpA / 2 SpD
Quiet Nature
- Eruption
- Heat Wave
- Earth Power
- Protect

Sinistcha @ Mental Herb
Ability: Hospitality
Level: 50
EVs: 32 HP / 16 Def / 18 SpA
Quiet Nature
- Matcha Gotcha
- Rage Powder
- Trick Room
- Life Dew

Primarina @ Leftovers
Ability: Liquid Voice
Level: 50
EVs: 32 HP / 26 SpA / 8 Spe
Modest Nature
- Hyper Voice
- Moonblast
- Calm Mind
- Protect

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
EVs: 32 HP / 32 Atk / 2 SpD
Adamant Nature
- Kowtow Cleave
- Protect
- Sucker Punch
- Iron Head

Arcanine-Hisui @ White Herb
Ability: Intimidate
Level: 50
EVs: 32 HP / 32 Atk / 2 SpD
Adamant Nature
- Rock Slide
- Flare Blitz
- Extreme Speed
- Protect`,
  },
  {
    slug: "perish-trap",
    title: "Perish Trap",
    note: "Specialized endgame shell that trades broad flexibility for forced clocks and trap lines.",
    regulationId: DEFAULT_REGULATION_ID,
    teamText: `Gengar @ Gengarite
Ability: Cursed Body
Level: 50
EVs: 4 HP / 32 SpA / 30 Spe
Timid Nature
- Perish Song
- Protect
- Shadow Ball
- Sludge Bomb

Politoed @ Mystic Water
Ability: Drizzle
Level: 50
EVs: 32 HP / 15 Def / 19 SpD
Calm Nature
- Perish Song
- Protect
- Icy Wind
- Whirlpool

Sableye @ Focus Sash
Ability: Prankster
Level: 50
EVs: 32 HP / 2 Def / 32 SpD
Careful Nature
- Mean Look
- Quash
- Protect
- Rain Dance

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
EVs: 32 HP / 12 Def / 22 SpA
Quiet Nature
- Matcha Gotcha
- Rage Powder
- Life Dew
- Protect

Primarina @ Leftovers
Ability: Liquid Voice
Level: 50
EVs: 32 HP / 26 SpA / 8 Spe
Modest Nature
- Hyper Voice
- Moonblast
- Calm Mind
- Protect

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
EVs: 32 HP / 32 Atk / 2 SpD
Adamant Nature
- Kowtow Cleave
- Protect
- Sucker Punch
- Iron Head`,
  },
  {
    slug: "master-ball",
    title: "Sableye Archaludon",
    note: "Current dual-mode shell with screens, rain support, and Archaludon + Basculegion pressure.",
    regulationId: DEFAULT_REGULATION_ID,
        teamText: `Sableye @ Roseli Berry
Ability: Prankster
Level: 50
EVs: 32 HP / 9 Def / 25 SpD
Careful Nature
- Fake Out
- Light Screen
- Reflect
- Quash

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Hurricane
- Tailwind
- Wide Guard
- Protect

Archaludon @ Leftovers
Ability: Stamina
Level: 50
EVs: 32 HP / 4 Def / 28 SpA
Modest Nature
- Electro Shot
- Dragon Pulse
- Flash Cannon
- Protect

Basculegion (M) @ Choice Scarf
Ability: Adaptability
Level: 50
EVs: 32 Atk / 2 Def / 32 Spe
Jolly Nature
- Last Respects
- Aqua Jet
- Wave Crash
- Psychic Fangs

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
EVs: 32 HP / 2 Def / 32 SpA
Quiet Nature
- Matcha Gotcha
- Rage Powder
- Life Dew
- Protect

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
EVs: 32 HP / 32 Atk / 2 Spe
Adamant Nature
- Kowtow Cleave
- Protect
- Sucker Punch
- Iron Head`,
  },
  {
    slug: "mega-scizor",
    title: "Mega Scizor",
    note: "Earlier top-cut balance reference with Tailwind pressure and emergency Trick Room coverage.",
    regulationId: DEFAULT_REGULATION_ID,
    teamText: `Sneasler @ White Herb
Ability: Unburden
Level: 50
EVs: 2 HP / 32 Atk / 32 Spe
Adamant Nature
- Close Combat
- Dire Claw
- Fake Out
- Protect

Garchomp @ Soft Sand
Ability: Rough Skin
Level: 50
EVs: 18 HP / 32 Atk / 2 Def / 14 Spe
Adamant Nature
- Dragon Claw
- Rock Slide
- Protect
- Stomping Tantrum

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
EVs: 32 HP / 2 Def / 32 SpA
Quiet Nature
- Matcha Gotcha
- Rage Powder
- Trick Room
- Life Dew

Aerodactyl @ Focus Sash
Ability: Unnerve
Level: 50
EVs: 32 HP / 2 SpD / 32 Spe
Jolly Nature
- Rock Slide
- Protect
- Dual Wingbeat
- Tailwind

Scizor-Mega @ Scizorite
Ability: Technician
Level: 50
EVs: 31 HP / 30 Atk / 5 Spe
Adamant Nature
- Bullet Punch
- Protect
- Bug Bite
- Swords Dance

Milotic @ Leftovers
Ability: Competitive
Level: 50
EVs: 32 HP / 16 Def / 10 SpA / 8 Spe
Calm Nature
- Scald
- Protect
- Icy Wind
- Recover`,
  },
  {
    slug: "incoherent-stress-test",
    title: "Incoherent Stress Test",
    note: "Legal on paper, strategically self-sabotaging, and packed with conflicting weather and speed plans.",
    regulationId: DEFAULT_REGULATION_ID,
    teamText: `Tyranitar @ Leftovers
Ability: Sand Stream
Level: 50
EVs: 32 HP / 32 Atk / 2 Spe
Adamant Nature
- Sandstorm
- Stealth Rock
- Roar
- Protect

Politoed @ Mystic Water
Ability: Drizzle
Level: 50
EVs: 32 HP / 16 Def / 16 SpD
Calm Nature
- Rain Dance
- Perish Song
- Icy Wind
- Protect

Torkoal @ Charcoal
Ability: Drought
Level: 50
EVs: 32 HP / 32 SpA / 2 SpD
Quiet Nature
- Eruption
- Sunny Day
- Earth Power
- Protect

Alolan Ninetales @ Mental Herb
Ability: Snow Warning
Level: 50
EVs: 32 HP / 24 SpA / 10 Spe
Timid Nature
- Aurora Veil
- Blizzard
- Freeze-Dry
- Protect

Farigiraf @ Sitrus Berry
Ability: Armor Tail
Level: 50
EVs: 32 HP / 24 SpA / 8 Def
Modest Nature
- Trick Room
- Psychic
- Dazzling Gleam
- Protect

Whimsicott @ Focus Sash
Ability: Prankster
Level: 50
EVs: 10 HP / 24 SpA / 32 Spe
Timid Nature
- Tailwind
- Encore
- Moonblast
- Protect`,
  },
];

export async function getFeaturedExampleTeams(): Promise<ExampleTeam[]> {
  return FEATURED_EXAMPLES.map((example) => ({ ...example }));
}
