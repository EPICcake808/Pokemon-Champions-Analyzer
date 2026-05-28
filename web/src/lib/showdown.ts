import type { EffortValueStat, ParsedTeamMember } from "@/lib/types";

const SPECIAL_SHOWDOWN_IDS: Record<string, string> = {
  "arcanine-hisui": "arcanine-hisui",
  "arcanine (hisuian form)": "arcanine-hisui",
  "hisuian arcanine": "arcanine-hisui",
  "basculegion (m)": "basculegion",
  "basculegion (male)": "basculegion",
  "basculegion (f)": "basculegion-f",
  "basculegion (female)": "basculegion-f",
  "eternal flower floette": "floette-eternal",
  "floette-eternal": "floette-eternal",
  "floette (eternal flower)": "floette-eternal",
  "mega eternal flower floette": "floette-mega",
  "mega floette": "floette-mega",
};

const SHOWDOWN_EV_ORDER: Array<{ stat: EffortValueStat; label: string }> = [
  { stat: "hp", label: "HP" },
  { stat: "attack", label: "Atk" },
  { stat: "defense", label: "Def" },
  { stat: "special_attack", label: "SpA" },
  { stat: "special_defense", label: "SpD" },
  { stat: "speed", label: "Spe" },
];

const SHOWDOWN_EV_LABEL_TO_STAT: Record<string, EffortValueStat> = {
  HP: "hp",
  Atk: "attack",
  Def: "defense",
  SpA: "special_attack",
  SpD: "special_defense",
  Spe: "speed",
};

const FORM_DESCRIPTOR_PATTERN = /^(?:M|F|Male|Female|Rotom|[A-Za-z-]+ Form|[A-Za-z-]+ Variety|[A-Za-z-]+ Rotom|Paldean Form \((?:Combat|Blaze|Aqua) Breed\)|(?:Combat|Blaze|Aqua) Breed)$/;

export function parseShowdownTeam(teamText: string): ParsedTeamMember[] {
  if (!teamText.trim()) {
    return [];
  }

  const blocks = teamText
    .trim()
    .split(/\n\s*\n/g)
    .map((block) => block.trim())
    .filter(Boolean);

  return blocks.map((block) => {
    const lines = block
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    const [speciesText, item] = parseHeader(lines[0] ?? "");
    const { displayName, species } = parseSpecies(speciesText);
    let ability: string | null = null;
    let level: number | null = null;
    let nature: string | null = null;
    const evs: Partial<Record<EffortValueStat, number>> = {};
    const moves: string[] = [];

    for (const line of lines.slice(1)) {
      if (line.startsWith("Ability: ")) {
        ability = line.slice("Ability: ".length).trim() || null;
      } else if (line.startsWith("Level: ")) {
        const parsedLevel = Number(line.slice("Level: ".length).trim());
        level = Number.isFinite(parsedLevel) ? parsedLevel : null;
      } else if (line.startsWith("EVs: ")) {
        Object.assign(evs, parseEvs(line.slice("EVs: ".length).trim()));
      } else if (line.endsWith(" Nature")) {
        nature = line.slice(0, -" Nature".length).trim() || null;
      } else if (line.startsWith("- ")) {
        moves.push(line.slice(2).trim());
      }
    }

    return {
      displayName,
      species,
      item,
      ability,
      level,
      nature,
      moves,
      evs,
    };
  });
}

export function serializeShowdownTeam(teamMembers: ParsedTeamMember[]): string {
  return teamMembers
    .map((member) => serializeShowdownMember(member))
    .filter(Boolean)
    .join("\n\n");
}

export function buildPokemonSpriteUrl(speciesName: string): string {
  const showdownId = toPokemonShowdownId(speciesName);
  return `https://play.pokemonshowdown.com/sprites/dex/${showdownId}.png`;
}

export function formatLabel(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function parseHeader(header: string): [string, string | null] {
  if (!header.includes(" @ ")) {
    return [header.trim(), null];
  }

  const [speciesText, item] = header.split(" @ ", 2);
  return [speciesText.trim(), item.trim() || null];
}

function parseSpecies(speciesText: string): { displayName: string; species: string } {
  const stripped = speciesText.trim();
  if (stripped.endsWith(" (M)") || stripped.endsWith(" (F)")) {
    return { displayName: stripped, species: stripped };
  }

  const nicknameSplit = splitNicknameAndSpecies(stripped);
  if (nicknameSplit && !looksLikeFormDescriptor(nicknameSplit.species)) {
    return {
      displayName: nicknameSplit.nickname,
      species: nicknameSplit.species,
    };
  }

  return { displayName: stripped, species: stripped };
}

function splitNicknameAndSpecies(speciesText: string): { nickname: string; species: string } | null {
  if (!speciesText.endsWith(")")) {
    return null;
  }

  let depth = 0;
  for (let index = speciesText.length - 1; index >= 0; index -= 1) {
    const character = speciesText[index];
    if (character === ")") {
      depth += 1;
    } else if (character === "(") {
      depth -= 1;
      if (depth === 0) {
        if (index === 0 || speciesText[index - 1] !== " ") {
          return null;
        }

        const nickname = speciesText.slice(0, index - 1).trim();
        const species = speciesText.slice(index + 1, -1).trim();
        if (!nickname || !species) {
          return null;
        }

        return { nickname, species };
      }
    }
  }

  return null;
}

function looksLikeFormDescriptor(speciesText: string): boolean {
  return FORM_DESCRIPTOR_PATTERN.test(speciesText.trim());
}

function parseEvs(evsText: string): Partial<Record<EffortValueStat, number>> {
  const evs: Partial<Record<EffortValueStat, number>> = {};

  for (const chunk of evsText.split("/")) {
    const trimmedChunk = chunk.trim();
    const match = trimmedChunk.match(/^(\d+)\s+([A-Za-z]+)$/);
    if (!match) {
      continue;
    }

    const value = Number(match[1]);
    const stat = SHOWDOWN_EV_LABEL_TO_STAT[match[2]];
    if (!stat || !Number.isFinite(value)) {
      continue;
    }

    evs[stat] = value;
  }

  return evs;
}

function serializeShowdownMember(member: ParsedTeamMember): string {
  const species = member.species.trim();
  if (!species) {
    return "";
  }

  const displayName = member.displayName.trim();
  const header = displayName && displayName !== species ? `${displayName} (${species})` : species;
  const lines = [member.item?.trim() ? `${header} @ ${member.item.trim()}` : header];
  const ability = member.ability?.trim();
  const evLine = serializeEvs(member.evs);
  const nature = member.nature?.trim();
  const moves = member.moves.map((move) => move.trim()).filter(Boolean).slice(0, 4);

  if (ability) {
    lines.push(`Ability: ${ability}`);
  }

  if (evLine) {
    lines.push(evLine);
  }

  if (nature) {
    lines.push(`${nature} Nature`);
  }

  for (const move of moves) {
    lines.push(`- ${move}`);
  }

  return lines.join("\n");
}

function serializeEvs(evs: Partial<Record<EffortValueStat, number>>): string | null {
  const chunks = SHOWDOWN_EV_ORDER.map(({ stat, label }) => {
    const value = evs[stat];
    if (!value || value <= 0) {
      return null;
    }
    return `${value} ${label}`;
  }).filter((chunk): chunk is string => Boolean(chunk));

  return chunks.length ? `EVs: ${chunks.join(" / ")}` : null;
}

function toPokemonShowdownId(speciesName: string): string {
  const normalized = speciesName.trim().toLowerCase();
  if (SPECIAL_SHOWDOWN_IDS[normalized]) {
    return SPECIAL_SHOWDOWN_IDS[normalized];
  }

  const spacedMegaMatch = normalized.match(/^mega\s+(.+?)(?:\s+([xy]))?$/);
  if (spacedMegaMatch) {
    return formatMegaShowdownId(spacedMegaMatch[1], spacedMegaMatch[2]);
  }

  const dashedMegaMatch = normalized.match(/^(.+?)-mega(?:-([xy]))?$/);
  if (dashedMegaMatch) {
    return formatMegaShowdownId(dashedMegaMatch[1], dashedMegaMatch[2]);
  }

  return normalizeShowdownAssetId(normalized);
}

function formatMegaShowdownId(baseName: string, suffix: string | undefined) {
  const normalizedBaseName = normalizeShowdownAssetId(baseName);
  if (suffix) {
    return `${normalizedBaseName}-mega${suffix.toLowerCase()}`;
  }

  return `${normalizedBaseName}-mega`;
}

function normalizeShowdownAssetId(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[♀]/g, "f")
    .replace(/[♂]/g, "m")
    .replace(/[’'.:%]/g, "")
    .replace(/[()\s-]/g, "");
}
