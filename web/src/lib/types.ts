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

export interface SpeedCoverageMember {
  pokemon: string;
  battle_speed: number;
  natural_pct: number;
  tailwind_pct: number;
  trick_room_pct: number;
}

export interface SpeedCoverage {
  available: boolean;
  weighted?: boolean;
  sample_species: number;
  sampled_pokemon?: string[];
  contexts?: string[];
  members: SpeedCoverageMember[];
  note: string;
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
  coverage?: SpeedCoverage;
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
  contextual_score: number;
  context_reasons: string[];
  matchup_score: number;
  impact_score: number;
  standing: string;
}

export interface MatchupDetail {
  base_score: number;
  contextual_adjustment: number;
  score: number;
  reasons: string[];
}

export interface MetaProvenanceSource {
  label: string;
  url: string;
}

export interface MetaProvenance {
  as_of: string;
  source_label: string;
  sources: MetaProvenanceSource[];
  methodology: string;
  is_live: boolean;
  // True when the common-meta board reflects measured overall usage (share of sampled
  // tournament teams) rather than curated board share. sample_size is the team count.
  usage_based?: boolean;
  sample_size?: number | null;
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
  provenance?: MetaProvenance;
}

export interface DamageMatchupRow {
  attacker: string;
  defender: string;
  move: string;
  move_type: string;
  category: string;
  min_percent: number;
  max_percent: number;
  type_multiplier: number;
  summary: string;
  guaranteed_ohko: boolean;
  possible_ohko: boolean;
  guaranteed_2hko: boolean;
  unmodeled: string[];
  // The build assumed for the curated (benchmark) side of this row.
  benchmark_set: string;
}

export interface DamageMatchups {
  outgoing: DamageMatchupRow[];
  incoming: DamageMatchupRow[];
  benchmark_walls: string[];
  benchmark_attackers: string[];
  notes: string[];
}

export interface DamageRollResult {
  move: string;
  move_type: string;
  category: string;
  base_power: number;
  type_multiplier: number;
  stab: number;
  rolls: number[];
  min_damage: number;
  max_damage: number;
  defender_hp: number;
  min_percent: number;
  max_percent: number;
  guaranteed_ohko: boolean;
  possible_ohko: boolean;
  guaranteed_2hko: boolean;
  possible_2hko: boolean;
  guaranteed_ko_hits: number | null;
  summary: string;
  unmodeled: string[];
}

export interface DamageCalcSide {
  species: string;
  move?: string | null;
  ability?: string | null;
  item?: string | null;
  nature?: string | null;
  evs?: Partial<Record<string, number>>;
}

export interface DamageCalcField {
  weather?: string | null;
  spread?: boolean | null;
  crit?: boolean;
  attackerAtkStage?: number;
  defenderDefStage?: number;
  attackerBurned?: boolean;
  reflect?: boolean;
  lightScreen?: boolean;
}

export interface DamageCalcRequest {
  attacker: DamageCalcSide;
  defender: DamageCalcSide;
  field?: DamageCalcField;
  regulationId?: string;
}

export interface DamageCalcResponse {
  ok: true;
  attacker: { species: string; types: string[]; stats: MemberStatBlock };
  defender: { species: string; types: string[]; stats: MemberStatBlock };
  move: { name: string; type: string; category: string; power: number | null };
  result: DamageRollResult | null;
}

export interface PreviewDamageLine {
  move: string;
  min_percent: number;
  max_percent: number;
  summary: string;
  guaranteed_ohko: boolean;
  guaranteed_2hko: boolean;
}

export interface PreviewMatchupRecord {
  member: string;
  speed: number;
  outspeeds: number;
  opponent_count: number;
  ko_targets: string[];
  ohko_targets: string[];
  threatened_by: string[];
  ohko_threats: string[];
  support: string[];
  lines: Record<string, { out: PreviewDamageLine | null; in: PreviewDamageLine | null }>;
}

export interface PreviewBring {
  members: string[];
  lead: string[];
  score: number;
  covers: number;
  opponent_count: number;
  reasons: string[];
}

export interface PreviewResponse {
  ok: true;
  opponent: string[];
  opponent_has_trick_room: boolean;
  recommended_bring: PreviewBring;
  alternatives: Array<{ members: string[]; lead: string[] }>;
  matchups: PreviewMatchupRecord[];
}

export interface PreviewRequest {
  myTeamText: string;
  opponentTeamText: string;
  regulationId?: string;
}

export interface SlotDoctorSwap {
  member: string;
  move: string;
  note: string;
}

export interface SlotDoctorReplacement {
  species: string | null;
  note: string;
}

export interface SlotDoctorGap {
  id: string;
  label: string;
  problem: string;
  move_swaps: SlotDoctorSwap[];
  replacements: SlotDoctorReplacement[];
}

export interface SlotDoctorResponse {
  ok: true;
  team: string[];
  gaps: SlotDoctorGap[];
  all_clear: boolean;
  note: string;
}

export interface SlotDoctorRequest {
  teamText: string;
  regulationId?: string;
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
  damage_matchups: DamageMatchups;
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
    details: Record<string, MatchupDetail>;
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
  plain_summary: string[];
  glossary: Record<string, { term: string; definition: string }>;
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

export interface ChangelogRoutePayload {
  content: string;
}

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
