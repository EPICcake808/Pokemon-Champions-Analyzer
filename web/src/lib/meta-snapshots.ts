import "server-only";

import { eq } from "drizzle-orm";
import { z } from "zod";

import { db } from "@/db";
import { publishedMetaSnapshots } from "@/db/schema";

const snapshotString = z.string().trim().min(1);

export const tournamentTeamSnapshotSchema = z
  .object({
    slug: snapshotString.max(120),
    label: snapshotString.max(120),
    source: snapshotString.max(240),
    result_label: snapshotString.max(120),
    field_relevance: z.number().min(0).max(2),
    popularity_weight: z.number().min(0).max(2),
    result_weight: z.number().min(0).max(2),
    modes: z.array(snapshotString.max(80)).min(1).max(8),
    mode_weights: z.record(z.string(), z.number().min(0).max(4)),
    broad_mix: z.record(z.string(), z.number().min(0).max(4)),
    key_pokemon: z.array(snapshotString.max(80)).min(1).max(12),
    key_cores: z.array(snapshotString.max(160)).min(1).max(8),
  })
  .superRefine((snapshot, context) => {
    for (const mode of snapshot.modes) {
      if (!(mode in snapshot.mode_weights)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: `mode_weights is missing an entry for ${mode}.`,
          path: ["mode_weights", mode],
        });
      }
    }
  });

export const commonMetaPokemonSchema = z.object({
  species: snapshotString.max(120),
  metaShare: z.number().min(0).max(100),
  whyUsed: snapshotString.max(400),
  whatItDoes: snapshotString.max(400),
  featuredTeams: z.array(snapshotString.max(120)).max(3).default([]),
});

export const publishedMetaSnapshotDocumentSchema = z.object({
  regulationId: snapshotString.max(120),
  updatedAt: z.string().datetime().optional(),
  sourceLabel: snapshotString.max(240).optional(),
  notes: z.array(snapshotString.max(400)).max(20).default([]),
  commonMetaPokemon: z.array(commonMetaPokemonSchema).max(16).default([]),
  tournamentTeamSnapshots: z.array(tournamentTeamSnapshotSchema).min(1).max(64),
});

export const metaSnapshotFeedSchema = z.object({
  version: z.literal(1),
  generatedAt: z.string().datetime().optional(),
  regulations: z.array(publishedMetaSnapshotDocumentSchema).min(1).max(16),
});

export type PublishedMetaSnapshotDocument = z.infer<typeof publishedMetaSnapshotDocumentSchema>;

export type PublishedMetaSnapshotResponse = PublishedMetaSnapshotDocument & {
  refreshedAt: string;
  sourceUrl: string | null;
};

const COMMON_META_POKEMON_CONTEXT: Record<string, { whyUsed: string; whatItDoes: string }> = {
  sinistcha: {
    whyUsed:
      "It compresses redirection, healing, and slower-mode insurance into one slot, so balance, room, and hybrid shells can stay consistent without losing support density.",
    whatItDoes:
      "It keeps partners healthy with Hospitality or healing support, redirects key turns with Rage Powder, and still threatens real board progress with Matcha Gotcha or Trick Room positioning.",
  },
  incineroar: {
    whyUsed:
      "It remains one of the safest glue pieces because Intimidate and positioning utility patch physical pressure without forcing teams to give up tempo.",
    whatItDoes:
      "It slows openings with Fake Out and pivot pressure, softens setup attempts, and buys cleaner entry turns for the field's main sweepers and weather payoffs.",
  },
  whimsicott: {
    whyUsed:
      "Prankster speed control and disruption are still premium, so fast offenses keep reaching for it when they want immediate tempo without spending their mega slot on support.",
    whatItDoes:
      "It gets Tailwind online quickly, threatens Encore-style disruption, and creates fast openings for attackers like Garchomp, Mega Charizard Y, and Kingambit.",
  },
  garchomp: {
    whyUsed:
      "It fits into several current shells because it threatens offense immediately while still scaling well with Tailwind, sun, or bulky positioning support.",
    whatItDoes:
      "It applies broad physical pressure with strong Ground coverage and spread damage, forcing awkward switches and punishing teams that fall behind on speed control.",
  },
  basculegion: {
    whyUsed:
      "Rain and fast-offense shells keep it around because it converts speed control into immediate KOs better than most physical cleaners in the format.",
    whatItDoes:
      "It acts as the rain-enabled cleaner that cashes in on chipped boards and forces endgames once Pelipper, Tailwind, or support positioning has opened the field.",
  },
  torkoal: {
    whyUsed:
      "Sun and Trick Room teams still lean on it because one clean positioning turn can translate directly into overwhelming damage output.",
    whatItDoes:
      "It sets sun, threatens huge spread Fire damage, and gives slower control teams a direct punish once Trick Room or redirection support sticks.",
  },
  "charizard-mega-y": {
    whyUsed:
      "Sun structures still lean on it because it gives them a self-contained weather engine and one of the format's best special nukes in a single slot.",
    whatItDoes:
      "It turns the board hostile immediately with harsh sunlight and high-output Fire pressure, especially once Tailwind or support positioning has already stabilized the turn order.",
  },
  archaludon: {
    whyUsed:
      "Rain and screens variants keep returning to it because it is both hard to remove and devastating once supported properly.",
    whatItDoes:
      "It functions as the bulky special payoff that converts rain, screens, or healing turns into snowball pressure and awkward trades for the opponent.",
  },
  pelipper: {
    whyUsed:
      "It is still the cleanest rain enabler for the format's Archaludon and Basculegion shells, so teams keep starting from it when they want consistent weather offense.",
    whatItDoes:
      "It sets rain, supports fast modes with Tailwind in relevant builds, and makes the backline start threatening boosted damage immediately.",
  },
  kingambit: {
    whyUsed:
      "Balance and offense teams both value it because it keeps priority endgames honest and punishes passive or overly defensive lines.",
    whatItDoes:
      "It acts as a cleaner and trade punisher, usually closing games with strong Dark or Steel pressure and priority once its partners have chipped the field.",
  },
  aerodactyl: {
    whyUsed:
      "Fast offense still likes it because it gives reliable speed control and immediate utility without demanding much support around it.",
    whatItDoes:
      "It threatens Tailwind leads, fast chip, and disruptive positioning turns that let stronger backline attackers start the game ahead on tempo.",
  },
  glimmora: {
    whyUsed:
      "Hazard-centric offenses use it because it pressures positioning from turn one while still fitting aggressive Tailwind shells.",
    whatItDoes:
      "It chips the opposing side, punishes contact and bad switching, and helps faster partners convert early momentum into lasting board damage.",
  },
  sneasler: {
    whyUsed:
      "Fast offense and dual-mega shells keep reaching for it because Unburden turns a single consumed item into a speed tier almost nothing outruns, letting it close games before slower control teams stabilize.",
    whatItDoes:
      "It opens with Fake Out, then snowballs with fast Fighting and Poison pressure and Dire Claw status, cleaning chipped boards and punishing teams that fall behind on speed.",
  },
  "floette-eternal": {
    whyUsed:
      "Balance, Trick Room, and dual-mega shells lean on it because its Mega folds a top-tier Fairy special attacker and a durable support body into one flexible slot.",
    whatItDoes:
      "It threatens high-output Fairy damage through Light of Ruin while Flower Veil and its bulk let it stay in to support partners, anchoring both slow Trick Room and fast dual-mode lines.",
  },
  charizard: {
    whyUsed:
      "Sun and fast-offense shells lean on it because its Mega forms fold a self-contained weather engine and one of the format's best nukes into a single, flexible slot.",
    whatItDoes:
      "As Mega Charizard Y it sets harsh sunlight and fires off high-output special Fire damage; as Mega Charizard X it offers a physical Dragon/Fire alternative — either way it turns Tailwind and support turns straight into KO pressure.",
  },
  tyranitar: {
    whyUsed:
      "Sand and bulky-offense shells build around it because Sand Stream chips the field for free and its Mega gives them a hard-hitting, hard-to-remove backbone in one slot.",
    whatItDoes:
      "It sets sand to wear down the opposing side, soaks special hits, and threatens heavy Rock and Dark damage that punishes passive trades and fragile special attackers.",
  },
  hydreigon: {
    whyUsed:
      "Offense and dual-mode shells like it because Levitate plus a broad special movepool gives them safe pivots into Ground attacks and reliable spread damage without much support.",
    whatItDoes:
      "It pressures the field with strong Dark and Dragon coverage, weakens special attackers with Snarl, and forces awkward switches thanks to its immunity to Ground.",
  },
  "rotom-wash": {
    whyUsed:
      "Balance and bulky shells keep it as glue because it pivots safely, spreads status, and answers the format's Water- and Ground-weak attackers from one resilient slot.",
    whatItDoes:
      "It pivots with Volt Switch, cripples physical threats with Will-O-Wisp, and chips the field with Hydro Pump while its Electric/Water typing dodges common offensive types.",
  },
  corviknight: {
    whyUsed:
      "Defensive and pivot-heavy shells rely on it because it patches physical pressure, provides speed control, and keeps recovering without giving up tempo.",
    whatItDoes:
      "It pivots with U-turn, sets Tailwind or stalls with Roost, and punishes contact and grounded attackers with Body Press behind its Steel/Flying bulk.",
  },
  froslass: {
    whyUsed:
      "Fast offense leans on it because it gives reliable speed control and disruption from turn one, and its Mega trades up into a real offensive threat without changing the lead plan.",
    whatItDoes:
      "It threatens fast Tailwind, hazards, and Destiny Bond trades, opening clean turns for the backline while its Ice/Ghost coverage chips key targets.",
  },
  farigiraf: {
    whyUsed:
      "Trick Room and balance shells value it because Armor Tail shuts off opposing priority and one bulky slot can both set the room and protect the win condition.",
    whatItDoes:
      "It sets Trick Room under pressure, supports with Helping Hand and Foul Play, and keeps slow attackers safe while the team flips the speed order.",
  },
};

const META_BOARD_MIN_FIELD_RELEVANCE = 0.7;
const MAX_COMMON_META_POKEMON = 10;

function normalizePublishedMetaSnapshotDocument(document: PublishedMetaSnapshotDocument): PublishedMetaSnapshotDocument {
  return {
    ...document,
    commonMetaPokemon: document.commonMetaPokemon.length
      ? document.commonMetaPokemon
      : deriveCommonMetaPokemon(document.tournamentTeamSnapshots),
  };
}

function deriveCommonMetaPokemon(
  tournamentTeamSnapshots: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"],
): PublishedMetaSnapshotDocument["commonMetaPokemon"] {
  const eligibleSnapshots = tournamentTeamSnapshots.filter(
    (snapshot) => snapshot.field_relevance >= META_BOARD_MIN_FIELD_RELEVANCE,
  );
  const totalWeight = eligibleSnapshots.reduce((sum, snapshot) => sum + buildTournamentSnapshotWeight(snapshot), 0) || 1;
  const speciesWeights = new Map<string, number>();
  const featuredTeams = new Map<string, Array<{ weight: number; label: string }>>();

  for (const snapshot of eligibleSnapshots) {
    const metaWeight = buildTournamentSnapshotWeight(snapshot);
    for (const speciesToken of snapshot.key_pokemon) {
      speciesWeights.set(speciesToken, (speciesWeights.get(speciesToken) ?? 0) + metaWeight);
      const rankedTeams = featuredTeams.get(speciesToken) ?? [];
      rankedTeams.push({ weight: metaWeight, label: snapshot.label });
      featuredTeams.set(speciesToken, rankedTeams);
    }
  }

  return [...speciesWeights.entries()]
    .sort((left, right) => {
      if (right[1] !== left[1]) {
        return right[1] - left[1];
      }

      return renderSpeciesToken(left[0]).localeCompare(renderSpeciesToken(right[0]));
    })
    .slice(0, MAX_COMMON_META_POKEMON)
    .map(([speciesToken, weightedPresence]) => {
      const species = renderSpeciesToken(speciesToken);
      const context = COMMON_META_POKEMON_CONTEXT[speciesToken];
      const rankedFeaturedTeams = (featuredTeams.get(speciesToken) ?? [])
        .slice()
        .sort((left, right) => (right.weight !== left.weight ? right.weight - left.weight : left.label.localeCompare(right.label)));
      const dedupedFeaturedTeams: string[] = [];
      const seenFeaturedTeams = new Set<string>();

      for (const team of rankedFeaturedTeams) {
        if (seenFeaturedTeams.has(team.label)) {
          continue;
        }

        dedupedFeaturedTeams.push(team.label);
        seenFeaturedTeams.add(team.label);
        if (dedupedFeaturedTeams.length >= 3) {
          break;
        }
      }

      if (!context) {
        const whyUsed = dedupedFeaturedTeams.length
          ? `${species} keeps turning up in high-performing shells like ${renderSeries(
              dedupedFeaturedTeams.slice(0, 2),
            )}, and that spread across different team styles is what keeps it on the meta board.`
          : `${species} keeps turning up across a range of high-performing shells rather than being tied to one team style, which is what keeps it on the meta board.`;
        return {
          species,
          metaShare: Number(((100 * weightedPresence) / totalWeight).toFixed(1)),
          whyUsed,
          whatItDoes:
            "Its spot here comes from broad usage across top teams rather than one signature role; teams reach for it in both offensive and supportive builds.",
          featuredTeams: dedupedFeaturedTeams,
        };
      }

      return {
        species,
        metaShare: Number(((100 * weightedPresence) / totalWeight).toFixed(1)),
        whyUsed: context.whyUsed,
        whatItDoes: context.whatItDoes,
        featuredTeams: dedupedFeaturedTeams,
      };
    });
}

function buildTournamentSnapshotWeight(snapshot: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number]) {
  return (0.68 * snapshot.popularity_weight + 0.32 * snapshot.result_weight) * snapshot.field_relevance;
}

function renderSeries(values: string[]) {
  if (!values.length) {
    return "";
  }

  if (values.length === 1) {
    return values[0];
  }

  if (values.length === 2) {
    return `${values[0]} and ${values[1]}`;
  }

  return `${values.slice(0, -1).join(", ")}, and ${values.at(-1)}`;
}

function renderSpeciesToken(speciesToken: string) {
  if (speciesToken.endsWith("-mega-x")) {
    return `Mega ${speciesToken.slice(0, -"-mega-x".length).replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())} X`;
  }

  if (speciesToken.endsWith("-mega-y")) {
    return `Mega ${speciesToken.slice(0, -"-mega-y".length).replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())} Y`;
  }

  if (speciesToken.endsWith("-mega")) {
    return `Mega ${speciesToken.slice(0, -"-mega".length).replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())}`;
  }

  if (speciesToken.endsWith("-male")) {
    return `${speciesToken.slice(0, -"-male".length).replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())} (M)`;
  }

  if (speciesToken.endsWith("-female")) {
    return `${speciesToken.slice(0, -"-female".length).replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())} (F)`;
  }

  if (speciesToken.endsWith("-alola")) {
    return `Alolan ${speciesToken.slice(0, -"-alola".length).replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())}`;
  }

  if (speciesToken.endsWith("-hisui")) {
    return `Hisuian ${speciesToken.slice(0, -"-hisui".length).replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())}`;
  }

  return speciesToken.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function serializePublishedMetaSnapshot(
  row: typeof publishedMetaSnapshots.$inferSelect,
): PublishedMetaSnapshotResponse {
  const payload = normalizePublishedMetaSnapshotDocument(publishedMetaSnapshotDocumentSchema.parse(row.payload));
  return {
    ...payload,
    refreshedAt: row.refreshedAt.toISOString(),
    sourceUrl: row.sourceUrl,
  };
}

export async function getPublishedMetaSnapshot(regulationId: string) {
  const [row] = await db
    .select()
    .from(publishedMetaSnapshots)
    .where(eq(publishedMetaSnapshots.regulationId, regulationId))
    .limit(1);

  return row ? serializePublishedMetaSnapshot(row) : null;
}

export async function upsertPublishedMetaSnapshot({
  document,
  sourceUrl,
}: {
  document: PublishedMetaSnapshotDocument;
  sourceUrl: string | null;
}) {
  const now = new Date();
  const normalizedDocument = normalizePublishedMetaSnapshotDocument(document);
  const [row] = await db
    .insert(publishedMetaSnapshots)
    .values({
      regulationId: normalizedDocument.regulationId,
      payload: normalizedDocument,
      sourceUrl,
      refreshedAt: now,
      createdAt: now,
      updatedAt: now,
    })
    .onConflictDoUpdate({
      target: publishedMetaSnapshots.regulationId,
      set: {
        payload: normalizedDocument,
        sourceUrl,
        refreshedAt: now,
        updatedAt: now,
      },
    })
    .returning();

  return serializePublishedMetaSnapshot(row);
}

export function isMetaSnapshotRefreshAuthorized(request: Request) {
  const expectedSecret =
    process.env.META_SNAPSHOT_REFRESH_SECRET?.trim() || process.env.CRON_SECRET?.trim() || "";
  if (!expectedSecret) {
    return false;
  }

  const authorization = request.headers.get("authorization")?.trim();
  return authorization === `Bearer ${expectedSecret}`;
}