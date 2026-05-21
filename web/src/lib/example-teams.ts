import "server-only";

import { DEFAULT_REGULATION_ID } from "@/lib/python-analyzer";
import type { ExampleTeam } from "@/lib/types";

const FEATURED_EXAMPLES: ExampleTeam[] = [
  {
    slug: "sample-team",
    title: "Curated Sample",
    note: "Rain Tailwind shell with layered support turns and flexible speed control.",
    regulationId: DEFAULT_REGULATION_ID,
    teamText: `Lucario-Mega @ Lucarionite
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

Basculegion (M) @ Choice Scarf
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
    title: "Hyper Offense",
    note: "Fast hazard pressure built to win short damage races.",
    regulationId: DEFAULT_REGULATION_ID,
    teamText: `Glimmora @ Focus Sash
Ability: Toxic Debris
Level: 50
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
- Stealth Rock
- Power Gem
- Sludge Wave
- Earth Power

Garchomp @ Soft Sand
Ability: Rough Skin
Level: 50
EVs: 156 HP / 252 Atk / 100 Spe
Adamant Nature
- Swords Dance
- Dragon Claw
- Rock Slide
- Stomping Tantrum

Sneasler @ White Herb
Ability: Unburden
Level: 50
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Fake Out
- Protect

Aerodactyl @ Sharp Beak
Ability: Unnerve
Level: 50
EVs: 32 HP / 2 SpD / 32 Spe
Jolly Nature
- Rock Slide
- Dual Wingbeat
- Tailwind
- Protect

Scizor-Mega @ Scizorite
Ability: Technician
Level: 50
EVs: 220 HP / 252 Atk / 36 Spe
Adamant Nature
- Bullet Punch
- Protect
- Bug Bite
- Swords Dance

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
EVs: 252 HP / 252 Atk / 4 SpD
Adamant Nature
- Kowtow Cleave
- Protect
- Sucker Punch
- Iron Head`,
  },
  {
    slug: "trick-room",
    title: "Trick Room",
    note: "Slow-mode pressure calibrated to current Regulation M-A Trick Room shells.",
    regulationId: DEFAULT_REGULATION_ID,
    teamText: `Farigiraf @ Sitrus Berry
Ability: Armor Tail
Level: 50
EVs: 252 HP / 116 Def / 140 SpA
Modest Nature
- Trick Room
- Psychic
- Dazzling Gleam
- Protect

Torkoal @ Charcoal
Ability: Drought
Level: 50
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
- Eruption
- Heat Wave
- Earth Power
- Protect

Sinistcha @ Mental Herb
Ability: Hospitality
Level: 50
EVs: 252 HP / 124 Def / 132 SpA
Quiet Nature
- Matcha Gotcha
- Rage Powder
- Trick Room
- Life Dew

Primarina @ Leftovers
Ability: Liquid Voice
Level: 50
EVs: 252 HP / 196 SpA / 60 Spe
Modest Nature
- Hyper Voice
- Moonblast
- Calm Mind
- Protect

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
EVs: 252 HP / 252 Atk / 4 SpD
Adamant Nature
- Kowtow Cleave
- Protect
- Sucker Punch
- Iron Head

Arcanine-Hisui @ White Herb
Ability: Intimidate
Level: 50
EVs: 252 HP / 252 Atk / 4 SpD
Adamant Nature
- Rock Slide
- Flare Blitz
- Extreme Speed
- Protect`,
  },
  {
    slug: "perish-trap",
    title: "Perish Trap",
    note: "Trap-centric routing built around forced endgames and protected clocks.",
    regulationId: DEFAULT_REGULATION_ID,
    teamText: `Gengar @ Gengarite
Ability: Cursed Body
Level: 50
EVs: 28 HP / 252 SpA / 228 Spe
Timid Nature
- Perish Song
- Protect
- Shadow Ball
- Sludge Bomb

Politoed @ Mystic Water
Ability: Drizzle
Level: 50
EVs: 252 HP / 116 Def / 140 SpD
Calm Nature
- Perish Song
- Protect
- Icy Wind
- Whirlpool

Sableye @ Focus Sash
Ability: Prankster
Level: 50
EVs: 252 HP / 4 Def / 252 SpD
Careful Nature
- Mean Look
- Quash
- Protect
- Rain Dance

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
EVs: 252 HP / 92 Def / 164 SpA
Quiet Nature
- Matcha Gotcha
- Rage Powder
- Life Dew
- Protect

Primarina @ Leftovers
Ability: Liquid Voice
Level: 50
EVs: 252 HP / 196 SpA / 60 Spe
Modest Nature
- Hyper Voice
- Moonblast
- Calm Mind
- Protect

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
EVs: 252 HP / 252 Atk / 4 SpD
Adamant Nature
- Kowtow Cleave
- Protect
- Sucker Punch
- Iron Head`,
  },
  {
    slug: "master-ball",
    title: "Master Ball Ready",
    note: "Tournament hybrid pulled from live Regulation M-A play with mixed speed modes.",
    regulationId: DEFAULT_REGULATION_ID,
    teamText: `Gardevoir-Mega @ Gardevoirite
Ability: Pixilate
Level: 50
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Hyper Voice
- Psychic
- Trick Room
- Protect

Primarina @ Leftovers
Ability: Liquid Voice
Level: 50
EVs: 32 HP / 24 SpA / 10 Spe
Modest Nature
- Hyper Voice
- Moonblast
- Calm Mind
- Protect

Whimsicott @ Focus Sash
Ability: Prankster
Level: 50
EVs: 10 HP / 24 SpA / 32 Spe
Timid Nature
- Tailwind
- Moonblast
- Encore
- Protect

Sneasler @ White Herb
Ability: Unburden
Level: 50
EVs: 28 HP / 32 Atk / 6 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Fake Out
- Protect

Arcanine-Hisui @ Sitrus Berry
Ability: Intimidate
Level: 50
EVs: 28 HP / 32 Atk / 6 Spe
Adamant Nature
- Rock Slide
- Flare Blitz
- Extreme Speed
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
    note: "Modern balance shell with Tailwind support, priority, and mode-flex lines.",
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
];

export async function getFeaturedExampleTeams(): Promise<ExampleTeam[]> {
  return FEATURED_EXAMPLES.map((example) => ({ ...example }));
}
