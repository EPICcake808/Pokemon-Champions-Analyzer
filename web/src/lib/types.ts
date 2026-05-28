export interface ExampleTeam {
  slug: string;
  title: string;
  note: string;
  regulationId: string;
  teamText: string;
}

export interface AuthSessionUser {
  id: string;
  username: string | null;
  name: string | null;
  email: string | null;
  image: string | null;
}

export interface SavedTeamRecord {
  id: string;
  name: string;
  teamText: string;
  regulationId: string;
  createdAt: string;
  updatedAt: string;
}

export interface AuthCapabilitySummary {
  nativeAuthEnabled: boolean;
  googleAuthEnabled: boolean;
}

export interface RegulationCatalogEntry {
  id: string;
  display_name: string;
  battle_type: string;
  team_size: number;
  source_ruleset_name: string;
  source_ruleset_url: string;
  source_eligible_pokemon_url: string;
  source_held_items_url: string;
  champions_status: string;
  is_official_champions_regulation: boolean;
  notes: string;
  eligible_pokemon_count: number;
  allowed_held_item_count: number;
  allowed_mega_evolution_count: number;
  duplicate_species_disallowed?: boolean;
  duplicate_held_items_disallowed: boolean;
  team_count: number;
  eligible_species?: string[];
  allowed_held_items?: string[];
  allowed_mega_evolutions?: string[];
  required_items_by_mega_species?: Record<string, string>;
}

export interface RegulationCatalogPayload {
  default_regulation_id: string;
  regulations: RegulationCatalogEntry[];
}

export interface BuilderSpeciesOptions {
  species: string;
  types: string[];
  abilities: string[];
  moves: string[];
  base_stats: MemberStatBlock;
  required_item: string | null;
}

export interface BuilderMoveDetails {
  name: string;
  api_name: string;
  type_name: string;
  damage_class: string;
  power: number | null;
  accuracy: number | null;
  pp: number;
  short_effect: string;
  effect_chance: number | null;
  category_name: string;
  ailment_name: string;
  ailment_chance: number;
  flinch_chance: number;
  healing: number;
  stat_chance: number;
  stat_changes: Array<{
    stat_name: string;
    change: number;
  }>;
  priority: number;
  target_name: string;
}

export interface LegalityIssue {
  code: string;
  message: string;
  member_name: string | null;
  team_slot: number | null;
  value: string | null;
}

export interface LegalityResult {
  regulation_id: string;
  is_legal: boolean;
  issues: LegalityIssue[];
}

export interface BenchmarkTag {
  group: string;
  group_label: string;
  comparison: string;
  benchmark_slug: string;
  benchmark_label: string;
  target_speed: number;
  status: string;
  context_speed: number;
}

export interface MemberStatBlock {
  hp: number;
  attack: number;
  defense: number;
  special_attack: number;
  special_defense: number;
  speed: number;
}

export interface SpeedContext {
  slug: string;
  label: string;
  speed: number;
}

export interface SpeedMember {
  pokemon: string;
  base_speed: number;
  battle_speed: number;
  stats: MemberStatBlock;
  tier: string;
  speed_contexts: SpeedContext[];
  benchmark_tags: BenchmarkTag[];
}

export interface SpeedBenchmarkRow {
  slug: string;
  label: string;
  target_speed: number;
  source: string;
  comparison: string;
  status: string;
  hit_members: string[];
  tie_members: string[];
}

export interface SpeedBenchmarkGroup {
  label: string;
  comparison: string;
  available: boolean;
  best_member: string | null;
  best_speed: number | null;
  benchmarks: SpeedBenchmarkRow[];
}

export interface SpeedProfile {
  average_base_speed: number;
  average_battle_speed: number;
  median_battle_speed: number;
  standard_deviation: number;
  team_tier: string;
  normalized_level: number;
  fastest: {
    pokemon: string;
    base_speed: number;
    battle_speed: number;
    tier: string;
  };
  slowest: {
    pokemon: string;
    base_speed: number;
    battle_speed: number;
    tier: string;
  };
  base_speed_extremes: {
    fastest: { pokemon: string; base_speed: number };
    slowest: { pokemon: string; base_speed: number };
  };
  spread: {
    minimum: number;
    maximum: number;
    range: number;
  };
  distribution: Record<string, { count: number; members: string[] }>;
  benchmarks: {
    catalog: {
      regulation_id: string;
      display_name: string;
      notes: string;
    } | null;
    notes: string[];
    groups: Record<string, SpeedBenchmarkGroup>;
  };
  members: SpeedMember[];
}

export interface BreakdownEntry {
  count: number;
  moves?: string[];
  members?: string[];
}

export interface TeamPackageAxis {
  label?: string;
  labels?: string[];
  scores: Record<string, number>;
}

export interface TeamPreviewPlan {
  label: string;
  summary: string;
  leads: string[];
  back: string[];
  pick_four: string[];
  recommended_into: string[];
  member_reasons: Record<string, string>;
}

export interface MetaModeMatchupRow {
  mode: string;
  tournament_weight: number;
  meta_share: number;
  matchup_score: number;
  impact_score: number;
  identity_score: number;
  standing: string;
}

export interface MetaTournamentRow {
  slug: string;
  label: string;
  source: string;
  result_label: string;
  modes: string[];
  key_cores: string[];
  key_pokemon: string[];
  popularity_score: number;
  result_score: number;
  meta_weight: number;
  meta_share: number;
  matchup_score: number;
  impact_score: number;
  standing: string;
}

export interface MetaAnalysis {
  label: string;
  overall_score: number;
  positive_weight_share: number;
  negative_weight_share: number;
  strongest_modes: string[];
  pressured_modes: string[];
  strongest_targets: string[];
  pressured_targets: string[];
  weighted_matchups: MetaModeMatchupRow[];
  tournament_rows: MetaTournamentRow[];
  common_pokemon?: Array<{
    species: string;
    meta_share: number;
    why_used: string;
    what_it_does: string;
    featured_teams: string[];
  }>;
  notes: string[];
}

export interface PokemonTeamAnalysis {
  regulation_id: string;
  team_size: number;
  typing_counts: Record<string, number>;
  defensive_profile: Record<
    string,
    {
      average_multiplier: number;
      weak_members: number;
      resistant_members: number;
      immune_members: number;
    }
  >;
  offensive_coverage: Record<string, number>;
  target_coverage: Record<
    string,
    {
      best_multiplier: number;
      super_effective_lines: number;
      neutral_or_better_lines: number;
      resisted_lines: number;
      immune_lines: number;
    }
  >;
  coverage_gaps: string[];
  speed_profile: SpeedProfile;
  damage_split: {
    physical: number;
    special: number;
  };
  utility_moves: number;
  utility_breakdown: Record<string, BreakdownEntry>;
  pokemon_role_breakdown: Record<string, BreakdownEntry>;
  member_roles: Record<string, string[]>;
  team_archetype: string;
  team_archetype_scores: Record<string, number>;
  team_package_profile: {
    style: TeamPackageAxis & { label: string };
    modes: TeamPackageAxis & { labels: string[] };
    win_conditions: TeamPackageAxis & { labels: string[] };
  };
  matchup_profile: {
    favorable: string[];
    unfavorable: string[];
    scores: Record<string, number>;
  };
  meta_mode_profile: {
    favorable: string[];
    unfavorable: string[];
    team_labels: string[];
    team_scores: Record<string, number>;
    scores: Record<string, number>;
  };
  meta_analysis: MetaAnalysis;
  team_difficulty: {
    label: string;
    score: number;
    factors: string[];
  };
  beginner_guidance: {
    notes: string[];
  };
  team_preview: {
    bring_plans: TeamPreviewPlan[];
    watch_teams: string[];
    watch_pokemon: string[];
    strategy_notes: string[];
    counterplay_notes: string[];
  };
  top_defensive_weaknesses: string[];
}

export type AnalyzeRoutePayload =
  | {
      ok: true;
      analysis: PokemonTeamAnalysis;
    }
  | {
      ok: false;
      message: string;
      legality?: LegalityResult;
    };

export type EffortValueStat =
  | "hp"
  | "attack"
  | "defense"
  | "special_attack"
  | "special_defense"
  | "speed";

export interface ParsedTeamMember {
  displayName: string;
  species: string;
  item: string | null;
  ability: string | null;
  level: number | null;
  nature: string | null;
  moves: string[];
  evs: Partial<Record<EffortValueStat, number>>;
}
