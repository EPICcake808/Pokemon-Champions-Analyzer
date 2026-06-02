"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { signIn, signOut } from "next-auth/react";
import {
  FormEvent,
  type ReactNode,
  useEffect,
  useState,
} from "react";

import { buildPokemonSpriteUrl, formatLabel, parseShowdownTeam, serializeShowdownTeam } from "@/lib/showdown";
import type {
  AnalyzeRoutePayload,
  AuthCapabilitySummary,
  AuthSessionUser,
  BenchmarkTag,
  BuilderMoveDetails,
  BuilderSpeciesOptions,
  EffortValueStat,
  MemberStatBlock,
  ParsedTeamMember,
  PokemonTeamAnalysis,
  RegulationCatalogEntry,
  SavedTeamRecord,
  SpeedContext,
  SpeedMember,
} from "@/lib/types";

const TYPE_ACCENTS: Record<string, string> = {
  bug: "#90d86b",
  dark: "#6f6d86",
  dragon: "#77a4ff",
  electric: "#ffd56c",
  fairy: "#ffb1dc",
  fighting: "#ff8c72",
  fire: "#ff8b5c",
  flying: "#8ebeff",
  ghost: "#94a6ff",
  grass: "#67db97",
  ground: "#cda76d",
  ice: "#91e9f5",
  normal: "#e4e6ef",
  poison: "#d48cff",
  psychic: "#ff8fc6",
  rock: "#d7b46b",
  steel: "#b3c2d8",
  water: "#6bb9ff",
};

const TYPE_ORDER = [
  "normal",
  "fire",
  "water",
  "electric",
  "grass",
  "ice",
  "fighting",
  "poison",
  "ground",
  "flying",
  "psychic",
  "bug",
  "rock",
  "ghost",
  "dragon",
  "dark",
  "steel",
  "fairy",
] as const;

const TYPE_ICON_LABELS: Record<string, string> = {
  bug: "BG",
  dark: "DK",
  dragon: "DR",
  electric: "EL",
  fairy: "FY",
  fighting: "FG",
  fire: "FR",
  flying: "FL",
  ghost: "GH",
  grass: "GR",
  ground: "GD",
  ice: "IC",
  normal: "NR",
  poison: "PS",
  psychic: "PY",
  rock: "RK",
  steel: "ST",
  water: "WT",
};

const BUILDER_TEAM_SIZE = 6;
const BUILDER_MOVE_COUNT = 4;
const CHAMPIONS_LEVEL = 50;
const CHAMPIONS_TOTAL_SPS = 66;
const CHAMPIONS_FIXED_IV = 31;

type AnalyzerWorkspaceProps = {
  initialAnalysis: PokemonTeamAnalysis;
  initialAnalysisError?: string | null;
  initialTeamText: string;
  initialSessionUser: AuthSessionUser | null;
  initialSavedTeams: SavedTeamRecord[];
  regulationOptions: RegulationCatalogEntry[];
  authCapabilities: AuthCapabilitySummary;
  changelogContent: string;
  playGuideContent: string;
};

type SiteDocumentId = "changelog" | "play-guide";

type SiteDocument = {
  id: SiteDocumentId;
  label: string;
  eyebrow: string;
  title: string;
  description: string;
  content: string;
};

type BattleStatKey = Exclude<keyof MemberStatBlock, "hp">;

type ItemStatModifier = {
  stat: keyof MemberStatBlock;
  numerator: number;
  denominator: number;
};

type RosterEntry = ParsedTeamMember & {
  roles: string[];
  speed: SpeedMember | undefined;
};

type TeamPreviewPlanCardData = PokemonTeamAnalysis["team_preview"]["bring_plans"][number];
type MetaMatchupRowData = PokemonTeamAnalysis["meta_analysis"]["tournament_rows"][number];
type MetaCommonPokemonRowData = NonNullable<PokemonTeamAnalysis["meta_analysis"]["common_pokemon"]>[number];

const MEMBER_STAT_ORDER: Array<{ key: keyof MemberStatBlock; label: string }> = [
  { key: "hp", label: "HP" },
  { key: "attack", label: "Atk" },
  { key: "defense", label: "Def" },
  { key: "special_attack", label: "SpA" },
  { key: "special_defense", label: "SpD" },
  { key: "speed", label: "Spe" },
];

const MEMBER_STAT_VISUAL_CAP = 255;
const MEMBER_STAT_COLOR_STOPS = [
  { minimum: 0, color: "#ff5f5f" },
  { minimum: 70, color: "#ff9a4d" },
  { minimum: 90, color: "#ffd95c" },
  { minimum: 110, color: "#63d88d" },
  { minimum: 130, color: "#69b7ff" },
  { minimum: 150, color: "#b27cff" },
] as const;

const NATURE_EFFECTS: Record<string, { increase?: BattleStatKey; decrease?: BattleStatKey }> = {
  adamant: { increase: "attack", decrease: "special_attack" },
  bashful: {},
  bold: { increase: "defense", decrease: "attack" },
  brave: { increase: "attack", decrease: "speed" },
  calm: { increase: "special_defense", decrease: "attack" },
  careful: { increase: "special_defense", decrease: "special_attack" },
  docile: {},
  gentle: { increase: "special_defense", decrease: "defense" },
  hardy: {},
  hasty: { increase: "speed", decrease: "defense" },
  impish: { increase: "defense", decrease: "special_attack" },
  jolly: { increase: "speed", decrease: "special_attack" },
  lax: { increase: "defense", decrease: "special_defense" },
  lonely: { increase: "attack", decrease: "defense" },
  mild: { increase: "special_attack", decrease: "defense" },
  modest: { increase: "special_attack", decrease: "attack" },
  naive: { increase: "speed", decrease: "special_defense" },
  naughty: { increase: "attack", decrease: "special_defense" },
  quiet: { increase: "special_attack", decrease: "speed" },
  quirky: {},
  rash: { increase: "special_attack", decrease: "special_defense" },
  relaxed: { increase: "defense", decrease: "speed" },
  sassy: { increase: "special_defense", decrease: "speed" },
  serious: {},
  timid: { increase: "speed", decrease: "attack" },
};

const NATURE_STAT_LABELS: Record<BattleStatKey, string> = {
  attack: "Atk",
  defense: "Def",
  special_attack: "SpA",
  special_defense: "SpD",
  speed: "Spe",
};

const NATURE_OPTIONS = Object.keys(NATURE_EFFECTS).map((nature) => ({
  value: nature.charAt(0).toUpperCase() + nature.slice(1),
  label: formatNatureOptionLabel(nature),
}));

function buildRosterValidationMessage(memberCount: number) {
  if (memberCount < BUILDER_TEAM_SIZE) {
    return `The live dashboard needs a full six-Pokemon roster. Right now it can only parse ${memberCount} member${memberCount === 1 ? "" : "s"}.`;
  }

  return null;
}

function formatSavedTeamTimestamp(value: string) {
  try {
    return new Intl.DateTimeFormat("en", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function buildSuggestedTeamName(teamText: string, fallback = "New saved team") {
  const parsedTeam = parseShowdownTeam(teamText);
  const firstSpecies = parsedTeam[0]?.species?.trim();

  return firstSpecies ? `${firstSpecies} squad` : fallback;
}

function buildSelectOptions(currentValue: string | null | undefined, options: string[]) {
  const normalizedOptions: string[] = [];
  const seenOptionKeys = new Set<string>();

  function appendOption(option: string | null | undefined) {
    const trimmedOption = option?.trim();
    if (!trimmedOption) {
      return;
    }

    const optionKey = normalizeAssetId(trimmedOption);
    if (seenOptionKeys.has(optionKey)) {
      return;
    }

    seenOptionKeys.add(optionKey);
    normalizedOptions.push(trimmedOption);
  }

  appendOption(currentValue);
  options.forEach((option) => appendOption(option));

  return normalizedOptions;
}

function buildDisplaySelectOptions(currentValue: string | null | undefined, options: string[]) {
  return buildSelectOptions(
    formatBuilderOptionValue(currentValue),
    options.map((option) => formatBuilderOptionValue(option)).filter(Boolean),
  );
}

function formatBuilderOptionValue(value: string | null | undefined) {
  const trimmedValue = value?.trim() ?? "";
  if (!trimmedValue) {
    return "";
  }

  if (/[A-Z]/.test(trimmedValue) || /[()'’.:]/.test(trimmedValue)) {
    return trimmedValue;
  }

  return formatLabel(trimmedValue);
}

export function AnalyzerWorkspace({
  initialAnalysis,
  initialAnalysisError,
  initialTeamText,
  initialSessionUser,
  initialSavedTeams,
  regulationOptions,
  authCapabilities,
  changelogContent,
  playGuideContent,
}: AnalyzerWorkspaceProps) {
  const router = useRouter();
  const [teamText, setTeamText] = useState(initialTeamText);
  const [analysisState, setAnalysis] = useState(initialAnalysis);
  const [sessionUserOverride, setSessionUserOverride] = useState<AuthSessionUser | null | undefined>(undefined);
  const [savedTeamsOverride, setSavedTeamsOverride] = useState<SavedTeamRecord[] | undefined>(undefined);
  const [selectedSavedTeamId, setSelectedSavedTeamId] = useState("");
  const [savedTeamName, setSavedTeamName] = useState("");
  const [authMode, setAuthMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [signInIdentifier, setSignInIdentifier] = useState("");
  const [signInPassword, setSignInPassword] = useState("");
  const [signUpUsername, setSignUpUsername] = useState("");
  const [signUpEmail, setSignUpEmail] = useState("");
  const [signUpPassword, setSignUpPassword] = useState("");
  const [accountNotice, setAccountNotice] = useState<string | null>(null);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const [isSavedTeamSubmitting, setIsSavedTeamSubmitting] = useState(false);
  const [selectedBuilderSlot, setSelectedBuilderSlot] = useState(0);
  const [selectedPreviewPlanLabel, setSelectedPreviewPlanLabel] = useState("");
  const [selectedBuilderSpeciesOptions, setSelectedBuilderSpeciesOptions] = useState<BuilderSpeciesOptions | null>(null);
  const [builderSpeciesResponseKey, setBuilderSpeciesResponseKey] = useState("");
  const [builderSpeciesError, setBuilderSpeciesError] = useState<string | null>(null);
  const [selectedRegulationId, setSelectedRegulationId] = useState(initialAnalysis.regulation_id);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(initialAnalysisError ?? null);
  const [legalityIssues, setLegalityIssues] = useState<string[]>([]);
  const [activeSiteDocumentId, setActiveSiteDocumentId] = useState<SiteDocumentId | null>(null);

  const sessionUser = sessionUserOverride !== undefined ? sessionUserOverride : initialSessionUser;
  const savedTeams = savedTeamsOverride !== undefined ? savedTeamsOverride : initialSavedTeams;
  const activeRegulation =
    regulationOptions.find((regulation) => regulation.id === selectedRegulationId) ?? regulationOptions[0];
  const parsedTeam = canonicalizeParsedTeamForRegulation(parseShowdownTeam(teamText), activeRegulation);
  const analysis = canonicalizeAnalysisForRegulation(analysisState, activeRegulation);
  const builderMembers = normalizeBuilderMembers(parsedTeam);
  const selectedBuilderMember = builderMembers[selectedBuilderSlot] ?? builderMembers[0];
  const filledBuilderCount = builderMembers.filter((member) => member.species.trim()).length;
  const rosterValidationMessage = buildRosterValidationMessage(filledBuilderCount);
  const dashboardBlockingMessage = rosterValidationMessage;
  const dashboardBlockingDetails = rosterValidationMessage
    ? [`${filledBuilderCount}/${BUILDER_TEAM_SIZE} roster slots are currently filled.`]
    : legalityIssues;
  const liveAnalysisStatusMessage = rosterValidationMessage
    ? rosterValidationMessage
    : isLoading
      ? "Live analysis is updating the dashboard..."
      : "Live analysis is on. Builder edits refresh the dashboard after you rerun the analyzer.";
  const selectedBuilderSpeciesRequestKey = selectedBuilderMember?.species?.trim()
    ? `${selectedRegulationId}::${normalizeAssetId(selectedBuilderMember.species)}`
    : "";
  const isBuilderSpeciesLoading =
    Boolean(selectedBuilderSpeciesRequestKey) && builderSpeciesResponseKey !== selectedBuilderSpeciesRequestKey;
  const activeBuilderSpeciesOptions =
    builderSpeciesResponseKey === selectedBuilderSpeciesRequestKey &&
    selectedBuilderSpeciesOptions
      ? selectedBuilderSpeciesOptions
      : null;
  const activeBuilderSpeciesError =
    builderSpeciesResponseKey === selectedBuilderSpeciesRequestKey ? builderSpeciesError : null;
  const selectedSavedTeam = selectedSavedTeamId
    ? savedTeams.find((team) => team.id === selectedSavedTeamId) ?? null
    : null;
  const selectedSavedTeamValue = selectedSavedTeam?.id ?? "";
  const authConfigurationMessage = authCapabilities.nativeAuthEnabled
    ? authCapabilities.googleAuthEnabled
      ? null
      : "Native username/password auth is enabled. Add AUTH_GOOGLE_ID and AUTH_GOOGLE_SECRET to enable Google sign-in on Vercel."
    : "Set DATABASE_URL and AUTH_SECRET to enable account-backed saved teams. Add AUTH_GOOGLE_ID and AUTH_GOOGLE_SECRET for Google sign-in.";
  const builderSpeciesChoices = buildSelectOptions(
    selectedBuilderMember?.species,
    [...(activeRegulation?.eligible_species ?? []), ...(activeRegulation?.allowed_mega_evolutions ?? [])],
  );
  const builderItemChoices = buildSelectOptions(
    selectedBuilderMember?.item,
    activeRegulation?.allowed_held_items ?? [],
  );
  const builderAbilityChoices = buildDisplaySelectOptions(
    selectedBuilderMember?.ability,
    activeBuilderSpeciesOptions?.abilities ?? [],
  );
  const builderMoveChoices = buildDisplaySelectOptions(undefined, activeBuilderSpeciesOptions?.moves ?? []);
  const selectedBuilderLockedItem = resolveRequiredMegaItem(
    selectedBuilderMember?.species ?? "",
    activeRegulation,
    activeBuilderSpeciesOptions?.required_item ?? null,
  );
  const siteDocuments: SiteDocument[] = [
    {
      id: "play-guide",
      label: "Play Guide",
      eyebrow: "Complete beginner guide",
      title: "How a VGC match actually works",
      description: "A literal beginner walkthrough of what happens before a match, what you click each turn, and how you win a doubles game.",
      content: playGuideContent,
    },
    {
      id: "changelog",
      label: "Changelog",
      eyebrow: "Release history",
      title: "What changed in the analyzer",
      description: "Recent releases across the analyzer, API, and live web experience.",
      content: changelogContent,
    },
  ];
  const activeSiteDocument = activeSiteDocumentId
    ? siteDocuments.find((document) => document.id === activeSiteDocumentId) ?? null
    : null;

  useEffect(() => {
    if (!activeSiteDocumentId) {
      return;
    }

    const previousOverflow = document.body.style.overflow;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setActiveSiteDocumentId(null);
      }
    }

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [activeSiteDocumentId]);

  async function runAnalysis(nextTeamText: string, regulationId = selectedRegulationId) {
    if (!nextTeamText.trim()) {
      setErrorMessage("Paste a Pokemon Showdown import before running the analyzer.");
      setLegalityIssues([]);
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setLegalityIssues([]);

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          teamText: nextTeamText,
          regulationId,
        }),
      });

      const payload = (await response.json()) as AnalyzeRoutePayload;
      if (!payload.ok) {
        setErrorMessage(payload.message);
        setLegalityIssues(payload.legality?.issues.map((issue) => issue.message) ?? []);
        return;
      }

      setAnalysis(payload.analysis);
    } catch {
      setErrorMessage(
        "The web app could not reach the local analyzer process. Make sure `python3` is available and run the app from this repository.",
      );
      setLegalityIssues([]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleManualTeamTextChange(nextTeamText: string) {
    setSelectedSavedTeamId("");
    setSavedTeamName((currentName) => currentName || buildSuggestedTeamName(nextTeamText));
    setTeamText(nextTeamText);
  }

  function handleRegulationChange(nextRegulationId: string) {
    setSelectedRegulationId(nextRegulationId);
    void runAnalysis(teamText, nextRegulationId);
  }

  function handleBlankTeam() {
    setSelectedBuilderSlot(0);
    setSelectedSavedTeamId("");
    setSavedTeamName("");
    setTeamText("");
    setErrorMessage(null);
    setLegalityIssues([]);
  }

  function updateBuilderMember(slotIndex: number, updater: (member: ParsedTeamMember) => ParsedTeamMember) {
    const nextMembers = builderMembers.map((member, index) =>
      index === slotIndex ? normalizeBuilderMember(updater(member)) : member,
    );

    handleManualTeamTextChange(serializeShowdownTeam(nextMembers));
  }

  function handleBuilderFieldChange(
    slotIndex: number,
    field: "species" | "item" | "ability" | "nature" | "level",
    value: string,
  ) {
    updateBuilderMember(slotIndex, (member) => {
      if (field === "species") {
        const nextSpecies = value;
        const nextLockedItem = resolveRequiredMegaItem(nextSpecies, activeRegulation);
        const usesSpeciesAsDisplayName = !member.displayName.trim() || member.displayName.trim() === member.species.trim();

        return {
          ...member,
          species: nextSpecies,
          displayName: usesSpeciesAsDisplayName ? nextSpecies : member.displayName,
          item: nextLockedItem,
          ability: null,
          moves: Array.from({ length: BUILDER_MOVE_COUNT }, () => ""),
          level: CHAMPIONS_LEVEL,
        };
      }

      if (field === "level") {
        return {
          ...member,
          level: CHAMPIONS_LEVEL,
        };
      }

      const normalizedValue = value.trim();
      return {
        ...member,
        [field]: normalizedValue || null,
      };
    });
  }

  function handleBuilderMoveChange(slotIndex: number, moveIndex: number, value: string) {
    updateBuilderMember(slotIndex, (member) => {
      const nextMoves = [...member.moves];
      nextMoves[moveIndex] = value;
      return {
        ...member,
        moves: nextMoves,
      };
    });
  }

  function handleBuilderEvChange(slotIndex: number, stat: EffortValueStat, value: string) {
    updateBuilderMember(slotIndex, (member) => {
      const nextEvs = { ...member.evs };
      if (!value.trim()) {
        delete nextEvs[stat];
      } else {
        const otherStatTotal = totalEffortValues(nextEvs) - (nextEvs[stat] ?? 0);
        const nextValue = clampNumber(Number(value), 0, CHAMPIONS_TOTAL_SPS);
        nextEvs[stat] = clampNumber(nextValue, 0, Math.max(0, CHAMPIONS_TOTAL_SPS - otherStatTotal));
      }

      return {
        ...member,
        evs: nextEvs,
      };
    });
  }

  function handleClearBuilderSlot(slotIndex: number) {
    updateBuilderMember(slotIndex, () => createEmptyTeamMember());
  }

  function resetAccountFeedback() {
    setAccountNotice(null);
    setAccountError(null);
  }

  function handleSavedTeamSelection(nextTeamId: string) {
    resetAccountFeedback();

    if (!nextTeamId) {
      setSelectedSavedTeamId("");
      setSavedTeamName("");
      setAccountNotice("Working in an unsaved builder draft.");
      return;
    }

    const savedTeam = savedTeams.find((team) => team.id === nextTeamId);
    if (!savedTeam) {
      setAccountError("That saved team could not be found.");
      return;
    }

    setSelectedBuilderSlot(0);
    setSelectedSavedTeamId(savedTeam.id);
    setSavedTeamName(savedTeam.name);
    setSelectedRegulationId(savedTeam.regulationId);
    setTeamText(savedTeam.teamText);
    setErrorMessage(null);
    setLegalityIssues([]);
    setAccountNotice(`Loaded ${savedTeam.name}.`);
  }

  async function handleCredentialsSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetAccountFeedback();
    setIsAuthSubmitting(true);

    try {
      const result = await signIn("credentials", {
        identifier: signInIdentifier,
        password: signInPassword,
        redirect: false,
      });

      if (!result || result.error) {
        throw new Error("The username/email or password is incorrect.");
      }

      setSessionUserOverride(undefined);
      setSavedTeamsOverride(undefined);
      setSignInPassword("");
      setAccountNotice("Signed in. Loading your saved teams...");
      router.refresh();
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : "The sign-in request failed.");
    } finally {
      setIsAuthSubmitting(false);
    }
  }

  async function handleCredentialsSignUp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetAccountFeedback();
    setIsAuthSubmitting(true);

    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: signUpUsername,
          email: signUpEmail,
          password: signUpPassword,
        }),
      });

      const payload = (await response.json()) as { message?: string };
      if (!response.ok) {
        throw new Error(payload.message || "The sign-up request failed.");
      }

      const signInResult = await signIn("credentials", {
        identifier: signUpUsername.toLowerCase(),
        password: signUpPassword,
        redirect: false,
      });

      if (!signInResult || signInResult.error) {
        throw new Error("The account was created, but the automatic sign-in step failed.");
      }

      setSessionUserOverride(undefined);
      setSavedTeamsOverride(undefined);
      setAuthMode("sign-in");
      setSignUpPassword("");
      setAccountNotice("Account created. Loading your saved teams...");
      router.refresh();
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : "The sign-up request failed.");
    } finally {
      setIsAuthSubmitting(false);
    }
  }

  async function handleGoogleSignIn() {
    resetAccountFeedback();
    setIsAuthSubmitting(true);
    setSessionUserOverride(undefined);
    setSavedTeamsOverride(undefined);

    try {
      await signIn("google", { callbackUrl: "/" });
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : "The Google sign-in request failed.");
      setIsAuthSubmitting(false);
    }
  }

  async function handleAccountSignOut() {
    resetAccountFeedback();
    setIsAuthSubmitting(true);

    try {
      await signOut({ redirect: false });
      setSessionUserOverride(null);
      setSavedTeamsOverride([]);
      setSelectedSavedTeamId("");
      setSavedTeamName("");
      setAccountNotice("Signed out.");
      router.refresh();
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : "The sign-out request failed.");
    } finally {
      setIsAuthSubmitting(false);
    }
  }

  async function handleCreateSavedTeam() {
    resetAccountFeedback();
    if (!sessionUser) {
      setAccountError("Sign in before saving teams.");
      return;
    }

    if (!savedTeamName.trim()) {
      setAccountError("Name the roster before saving it.");
      return;
    }

    if (!teamText.trim()) {
      setAccountError("Build or import a roster before saving it.");
      return;
    }

    setIsSavedTeamSubmitting(true);

    try {
      const response = await fetch("/api/saved-teams", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: savedTeamName,
          teamText,
          regulationId: selectedRegulationId,
        }),
      });

      const payload = (await response.json()) as { team?: SavedTeamRecord; message?: string };
      if (!response.ok || !payload.team) {
        throw new Error(payload.message || "The team could not be saved.");
      }

      setSavedTeamsOverride([payload.team, ...savedTeams.filter((team) => team.id !== payload.team!.id)]);
      setSelectedSavedTeamId(payload.team.id);
      setSavedTeamName(payload.team.name);
      setAccountNotice(`Saved ${payload.team.name}.`);
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : "The team could not be saved.");
    } finally {
      setIsSavedTeamSubmitting(false);
    }
  }

  async function handleUpdateSavedTeam() {
    resetAccountFeedback();
    if (!sessionUser) {
      setAccountError("Sign in before updating saved teams.");
      return;
    }

    if (!selectedSavedTeam) {
      setAccountError("Select a saved team to update it.");
      return;
    }

    if (!savedTeamName.trim()) {
      setAccountError("Saved teams need a name.");
      return;
    }

    setIsSavedTeamSubmitting(true);

    try {
      const response = await fetch(`/api/saved-teams/${encodeURIComponent(selectedSavedTeam.id)}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: savedTeamName,
          teamText,
          regulationId: selectedRegulationId,
        }),
      });

      const payload = (await response.json()) as { team?: SavedTeamRecord; message?: string };
      if (!response.ok || !payload.team) {
        throw new Error(payload.message || "The saved team could not be updated.");
      }

      setSavedTeamsOverride(savedTeams.map((team) => (team.id === payload.team!.id ? payload.team! : team)));
      setSavedTeamName(payload.team.name);
      setAccountNotice(`Updated ${payload.team.name}.`);
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : "The saved team could not be updated.");
    } finally {
      setIsSavedTeamSubmitting(false);
    }
  }

  async function handleDeleteSavedTeam() {
    resetAccountFeedback();
    if (!sessionUser) {
      setAccountError("Sign in before deleting saved teams.");
      return;
    }

    if (!selectedSavedTeam) {
      setAccountError("Select a saved team to delete it.");
      return;
    }

    setIsSavedTeamSubmitting(true);

    try {
      const response = await fetch(`/api/saved-teams/${encodeURIComponent(selectedSavedTeam.id)}`, {
        method: "DELETE",
      });

      const payload = (await response.json()) as { message?: string };
      if (!response.ok) {
        throw new Error(payload.message || "The saved team could not be deleted.");
      }

      const deletedTeam = selectedSavedTeam;
      setSavedTeamsOverride(savedTeams.filter((team) => team.id !== selectedSavedTeam.id));
      setSelectedSavedTeamId("");
      setSavedTeamName("");
      setAccountNotice(deletedTeam ? `Deleted ${deletedTeam.name}.` : "Saved team deleted.");
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : "The saved team could not be deleted.");
    } finally {
      setIsSavedTeamSubmitting(false);
    }
  }

  useEffect(() => {
    const species = selectedBuilderMember?.species?.trim();
    const requestKey = species ? `${selectedRegulationId}::${normalizeAssetId(species)}` : "";

    if (!species) {
      return;
    }

    const abortController = new AbortController();

    void fetch(
      `/api/builder-species?species=${encodeURIComponent(species)}&regulationId=${encodeURIComponent(selectedRegulationId)}`,
      {
        signal: abortController.signal,
      },
    )
      .then(async (response) => {
        const payload = (await response.json()) as BuilderSpeciesOptions & { message?: string };

        if (!response.ok) {
          throw new Error(payload.message ?? "The builder species request failed.");
        }

        setSelectedBuilderSpeciesOptions(payload);
        setBuilderSpeciesError(null);
        setBuilderSpeciesResponseKey(requestKey);
      })
      .catch((error: unknown) => {
        if (abortController.signal.aborted) {
          return;
        }

        setSelectedBuilderSpeciesOptions(null);
        setBuilderSpeciesError(error instanceof Error ? error.message : "The builder species request failed.");
        setBuilderSpeciesResponseKey(requestKey);
      });

    return () => {
      abortController.abort();
    };
  }, [selectedBuilderMember?.species, selectedRegulationId]);

  const roster = buildRoster(parsedTeam, analysis);
  const rosterLookup = new Map(roster.map((member) => [member.displayName, member]));
  const typingRows = rankedRows(analysis.typing_counts, 8).filter((row) => row.value > 0);
  const coverageRows = TYPE_ORDER.map((label) => ({
    label,
    value: analysis.offensive_coverage[label] ?? 0,
  }));
  const targetCoverage = analysis.target_coverage ?? {};
  const coverageGapSet = new Set(analysis.coverage_gaps ?? []);
  const coverageGapNotes = TYPE_ORDER.filter((typeName) => coverageGapSet.has(typeName)).map((typeName) =>
    describeCoverageGap(typeName, targetCoverage[typeName]),
  );
  const utilityRows = rankedBreakdownRows(analysis.utility_breakdown, 7);
  const roleRows = rankedBreakdownRows(analysis.pokemon_role_breakdown, 7);
  const defensiveRows = TYPE_ORDER.map((label) => {
    const details = analysis.defensive_profile[label] ?? {
      average_multiplier: 0,
      weak_members: 0,
      resistant_members: 0,
      immune_members: 0,
    };

    return {
      label,
      value: details.average_multiplier,
      note: `${details.weak_members} weak / ${details.resistant_members} resist / ${details.immune_members} immune`,
    };
  });
  const matchupRows = scoreRows(analysis.matchup_profile.scores, analysis.matchup_profile.details);
  const modeRows = scoreRows(analysis.meta_mode_profile.scores);
  const packageModeRows = scoreRows(analysis.team_package_profile.modes.scores).slice(0, 4);
  const winConditionRows = scoreRows(analysis.team_package_profile.win_conditions.scores)
    .filter(
      (row) => row.value >= 2 || analysis.team_package_profile.win_conditions.labels.includes(row.label),
    )
    .slice(0, 3);
  const leadRoleLabels = roleRows.slice(0, 3).map((row) => formatLabel(row.label));
  const currentBuildTitle =
    savedTeamName.trim() || selectedSavedTeam?.name || (parsedTeam.length ? "Current build" : "Current import");
  const currentBuildNote = selectedSavedTeam
    ? `Loaded from your saved teams. Last updated ${formatSavedTeamTimestamp(selectedSavedTeam.updatedAt)}.`
    : parsedTeam.length
      ? "This is your active builder roster. Run the analyzer after major edits to refresh the scoring panels."
      : "Start from scratch or paste a Showdown export to populate the builder.";
  const previewPlans = analysis.team_preview.bring_plans;
  const activePreviewPlan = previewPlans.find((plan) => plan.label === selectedPreviewPlanLabel) ?? previewPlans[0] ?? null;
  const teamStyleLabel = formatLabel(analysis.team_package_profile.style.label);
  const modePackageLabel = analysis.team_package_profile.modes.labels.length
    ? analysis.team_package_profile.modes.labels.map(formatLabel).join(" / ")
    : "No dominant mode package";
  const winConditionLabel = analysis.team_package_profile.win_conditions.labels.length
    ? analysis.team_package_profile.win_conditions.labels.map(formatLabel).join(" / ")
    : "No clear endgame plan";
  const watchPokemonNotes = analysis.team_preview.watch_pokemon.length
    ? [analysis.team_preview.watch_pokemon.join(", ")]
    : ["No specific signature threats flagged."];

  return (
    <div className="min-h-screen text-[var(--fg)]">
      <SiteHeader
        regulationLabel={activeRegulation.display_name}
        documentLinks={siteDocuments.map(({ id, label }) => ({ id, label }))}
        onOpenDocument={setActiveSiteDocumentId}
      />
      <SiteDocumentDialog
        activeDocument={activeSiteDocument}
        documents={siteDocuments}
        onClose={() => setActiveSiteDocumentId(null)}
        onOpenDocument={setActiveSiteDocumentId}
      />

      <main className="mx-auto w-full max-w-[1680px] px-5 pb-16 pt-6 sm:px-8 lg:px-10 lg:pt-8">
        <section className="pb-8 lg:pb-10">
          <div className="flex flex-col gap-5 border-b border-[var(--line)] pb-7 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-4xl">
              <p className="[font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.38em] text-white/38">
                Deterministic Battle Intelligence
              </p>
              <h1 className="balance-text mt-4 [font-family:var(--font-title)] text-[2.45rem] font-semibold uppercase tracking-[0.08em] text-white sm:text-[3rem] lg:text-[4rem] lg:leading-[1.02]">
                Pokemon Champions Analyzer
              </h1>
              <p className="mt-4 max-w-3xl text-[0.98rem] leading-7 text-[var(--fg-muted)] sm:text-[1.04rem]">
                Build your Champions roster visually, then run the same regulation-aware Python analyzer that powers the
                CLI for legality, speed, matchup, mode, and role reads.
              </p>
            </div>

            <p className="max-w-md text-sm leading-6 text-white/42 lg:text-right">
              Builder-first workflow up top, dense analysis below it. Edit slots, import raw Showdown text if you want,
              and rerun once the shell is where you want it.
            </p>
          </div>
        </section>

        <section className="border-t border-[var(--line)] py-10">
          <div className="grid gap-8 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
            <div className="border-y border-[var(--line)] py-6">
              {sessionUser ? (
                <>
                  <SectionHeading eyebrow="Saved teams" title="Account-linked builder" />
                  <p className="mt-4 max-w-3xl text-sm leading-6 text-[var(--fg-muted)]">
                    Signed in as @{sessionUser.username ?? "trainer"}
                    {sessionUser.email ? ` · ${sessionUser.email}` : ""}. Load a saved roster directly into the
                    builder or save the current draft back to your Neon-backed account.
                  </p>

                  <div className="mt-6 grid gap-4 md:grid-cols-[minmax(0,1fr)_240px]">
                    <label className="space-y-2">
                      <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                        Saved roster
                      </span>
                      <select
                        value={selectedSavedTeamValue}
                        onChange={(event) => handleSavedTeamSelection(event.target.value)}
                        className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
                      >
                        <option value="" className="bg-[#090b10] text-white">
                          Current builder draft
                        </option>
                        {savedTeams.map((savedTeam) => (
                          <option key={savedTeam.id} value={savedTeam.id} className="bg-[#090b10] text-white">
                            {savedTeam.name}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="space-y-2">
                      <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                        Team name
                      </span>
                      <input
                        type="text"
                        value={savedTeamName}
                        onChange={(event) => setSavedTeamName(event.target.value)}
                        className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
                        placeholder="Give this roster a saved name"
                      />
                    </label>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => void handleCreateSavedTeam()}
                      className="border border-white/45 px-4 py-3 [font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.22em] text-white/88 transition hover:border-white hover:text-white disabled:border-white/20 disabled:text-white/28"
                      disabled={isSavedTeamSubmitting}
                    >
                      {isSavedTeamSubmitting ? "Saving" : "Save as new"}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleUpdateSavedTeam()}
                      className="border border-white/28 px-4 py-3 [font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.22em] text-white/70 transition hover:border-white/55 hover:text-white disabled:border-white/12 disabled:text-white/22"
                      disabled={isSavedTeamSubmitting || !selectedSavedTeam}
                    >
                      Update selected
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDeleteSavedTeam()}
                      className="border border-white/18 px-4 py-3 [font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.22em] text-white/62 transition hover:border-[var(--negative)] hover:text-[var(--negative)] disabled:border-white/12 disabled:text-white/22"
                      disabled={isSavedTeamSubmitting || !selectedSavedTeam}
                    >
                      Delete selected
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleAccountSignOut()}
                      className="border-b border-white/45 pb-2 pt-3 [font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.22em] text-white/74 transition hover:text-white disabled:border-white/20 disabled:text-white/26"
                      disabled={isAuthSubmitting}
                    >
                      Sign out
                    </button>
                  </div>

                  <p className="mt-4 text-sm leading-6 text-white/42">
                    {selectedSavedTeam
                      ? `Loaded entry last updated ${formatSavedTeamTimestamp(selectedSavedTeam.updatedAt)}.`
                      : "Select a saved team to load it instantly, or keep working in the current unsaved builder draft."}
                  </p>
                </>
              ) : authCapabilities.nativeAuthEnabled ? (
                <>
                  <SectionHeading eyebrow="Account access" title="Sign in to sync teams" />
                  <p className="mt-4 max-w-3xl text-sm leading-6 text-[var(--fg-muted)]">
                    Every account gets a unique username. Native sign-up stores a securely hashed password, and Google
                    sign-in can attach to the same verified-email account so your saved teams stay under one identity.
                  </p>

                  <div className="mt-5 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => setAuthMode("sign-in")}
                      className={`border px-4 py-3 [font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.22em] transition ${
                        authMode === "sign-in"
                          ? "border-white/60 bg-white/[0.04] text-white"
                          : "border-white/18 text-white/56 hover:border-white/40 hover:text-white"
                      }`}
                    >
                      Sign in
                    </button>
                    <button
                      type="button"
                      onClick={() => setAuthMode("sign-up")}
                      className={`border px-4 py-3 [font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.22em] transition ${
                        authMode === "sign-up"
                          ? "border-white/60 bg-white/[0.04] text-white"
                          : "border-white/18 text-white/56 hover:border-white/40 hover:text-white"
                      }`}
                    >
                      Create account
                    </button>
                  </div>

                  {authMode === "sign-in" ? (
                    <form className="mt-6" onSubmit={(event) => void handleCredentialsSignIn(event)}>
                      <div className="grid gap-4 md:grid-cols-2">
                        <label className="space-y-2">
                          <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                            Username or email
                          </span>
                          <input
                            type="text"
                            value={signInIdentifier}
                            onChange={(event) => setSignInIdentifier(event.target.value)}
                            className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
                            placeholder="champion_player"
                            autoComplete="username"
                          />
                        </label>
                        <label className="space-y-2">
                          <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                            Password
                          </span>
                          <input
                            type="password"
                            value={signInPassword}
                            onChange={(event) => setSignInPassword(event.target.value)}
                            className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
                            placeholder="Enter your password"
                            autoComplete="current-password"
                          />
                        </label>
                      </div>

                      <button
                        type="submit"
                        className="mt-5 border border-white/45 px-4 py-3 [font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.22em] text-white/88 transition hover:border-white hover:text-white disabled:border-white/20 disabled:text-white/28"
                        disabled={isAuthSubmitting}
                      >
                        {isAuthSubmitting ? "Signing in" : "Sign in with password"}
                      </button>
                    </form>
                  ) : (
                    <form className="mt-6" onSubmit={(event) => void handleCredentialsSignUp(event)}>
                      <div className="grid gap-4 md:grid-cols-3">
                        <label className="space-y-2">
                          <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                            Username
                          </span>
                          <input
                            type="text"
                            value={signUpUsername}
                            onChange={(event) => setSignUpUsername(event.target.value)}
                            className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
                            placeholder="champion_player"
                            autoComplete="username"
                          />
                        </label>
                        <label className="space-y-2">
                          <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                            Email
                          </span>
                          <input
                            type="email"
                            value={signUpEmail}
                            onChange={(event) => setSignUpEmail(event.target.value)}
                            className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
                            placeholder="you@example.com"
                            autoComplete="email"
                          />
                        </label>
                        <label className="space-y-2">
                          <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                            Password
                          </span>
                          <input
                            type="password"
                            value={signUpPassword}
                            onChange={(event) => setSignUpPassword(event.target.value)}
                            className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
                            placeholder="Use at least 8 characters"
                            autoComplete="new-password"
                          />
                        </label>
                      </div>

                      <button
                        type="submit"
                        className="mt-5 border border-white/45 px-4 py-3 [font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.22em] text-white/88 transition hover:border-white hover:text-white disabled:border-white/20 disabled:text-white/28"
                        disabled={isAuthSubmitting}
                      >
                        {isAuthSubmitting ? "Creating account" : "Create account"}
                      </button>
                    </form>
                  )}

                  <div className="mt-6 border-t border-[var(--line)] pt-5">
                    <p className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                      Google
                    </p>
                    {authCapabilities.googleAuthEnabled ? (
                      <button
                        type="button"
                        onClick={() => void handleGoogleSignIn()}
                        className="mt-4 border border-white/28 px-4 py-3 [font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.22em] text-white/74 transition hover:border-white/55 hover:text-white disabled:border-white/12 disabled:text-white/22"
                        disabled={isAuthSubmitting}
                      >
                        Continue with Google
                      </button>
                    ) : (
                      <p className="mt-3 text-sm leading-6 text-white/42">
                        Google sign-in is already wired into the app. Set AUTH_GOOGLE_ID and AUTH_GOOGLE_SECRET in
                        Vercel and locally to enable the button.
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <SectionHeading eyebrow="Account access" title="Configure auth to unlock saved teams" />
                  <p className="mt-4 max-w-3xl text-sm leading-6 text-[var(--fg-muted)]">
                    Native auth, Google OAuth, and account-linked saved teams are all wired into this app now. The
                    controls stay disabled until your environment variables are present.
                  </p>
                  <p className="mt-4 text-sm leading-6 text-white/42">{authConfigurationMessage}</p>
                </>
              )}

              {accountError ? <p className="mt-5 text-sm leading-6 text-[var(--negative)]">{accountError}</p> : null}
              {!accountError && accountNotice ? (
                <p className="mt-5 text-sm leading-6 text-[var(--positive)]">{accountNotice}</p>
              ) : null}
            </div>

            <aside className="border-y border-[var(--line)] py-6">
              <p className="[font-family:var(--font-display)] text-[0.64rem] uppercase tracking-[0.32em] text-white/35">
                Deployment shape
              </p>
              <ul className="mt-5 space-y-3 text-sm leading-6 text-[var(--fg-muted)]">
                <li>Native sign-up stores bcrypt-hashed passwords. Raw passwords never get written to Neon.</li>
                <li>Google OAuth and username/password accounts can converge on one user record through verified email.</li>
                <li>Every saved roster is scoped to the signed-in user id, so the selector only surfaces that account&apos;s teams.</li>
                <li>Neon&apos;s serverless Postgres driver and Auth.js route handlers are compatible with Vercel&apos;s Node runtime.</li>
              </ul>
              <p className="mt-5 text-sm leading-6 text-white/42">
                {authConfigurationMessage ?? "The account layer is fully available for this environment."}
              </p>
            </aside>
          </div>
        </section>

        <section id="builder" className="grid gap-8 border-t border-[var(--line)] py-10 xl:grid-cols-[280px_minmax(0,1.12fr)_360px] xl:items-start">
          <aside className="space-y-8">
            <div>
              <SectionHeading eyebrow="Team builder" title="Build your six" />
              <p className="mt-4 text-sm leading-6 text-[var(--fg-muted)]">
                Pick a slot, edit the set on the right, and keep the synced Showdown export handy for imports or quick
                copy-out.
              </p>
              <TeamBuilderSlotRail
                members={builderMembers}
                selectedIndex={selectedBuilderSlot}
                regulationId={selectedRegulationId}
                onSelect={setSelectedBuilderSlot}
              />
            </div>

            <div className="border-t border-[var(--line)] pt-6">
              <button
                type="button"
                onClick={handleBlankTeam}
                className="border-b border-white/60 pb-2 [font-family:var(--font-display)] text-[0.7rem] uppercase tracking-[0.24em] text-white/82 transition-colors hover:text-[var(--accent)]"
              >
                Start blank roster
              </button>
              <div className="mt-4 space-y-2 text-sm leading-6 text-white/46">
                <p>
                  {parsedTeam.length} / {BUILDER_TEAM_SIZE} slots filled
                </p>
                <p>{currentBuildNote}</p>
              </div>
            </div>
          </aside>

          <div className="min-w-0 xl:border-x xl:border-[var(--line)] xl:px-8">
            <TeamBuilderEditor
              member={selectedBuilderMember}
              slotIndex={selectedBuilderSlot}
              speciesOptions={activeBuilderSpeciesOptions}
              speciesTypes={activeBuilderSpeciesOptions?.types ?? []}
              regulationId={selectedRegulationId}
              lockedItem={selectedBuilderLockedItem}
              speciesChoices={builderSpeciesChoices}
              itemChoices={builderItemChoices}
              abilityChoices={builderAbilityChoices}
              moveChoices={builderMoveChoices}
              isSpeciesOptionsLoading={isBuilderSpeciesLoading}
              speciesOptionsError={activeBuilderSpeciesError}
              onFieldChange={handleBuilderFieldChange}
              onMoveChange={handleBuilderMoveChange}
              onEvChange={handleBuilderEvChange}
              onClear={handleClearBuilderSlot}
            />

            <details className="mt-8 border-t border-[var(--line)] pt-5" open={parsedTeam.length === 0}>
              <summary className="list-none cursor-pointer [font-family:var(--font-display)] text-[0.68rem] uppercase tracking-[0.3em] text-white/42">
                Import or export Showdown text
              </summary>
              <p className="mt-4 max-w-3xl text-sm leading-6 text-[var(--fg-muted)]">
                Paste a full Showdown export to populate the builder, or copy the synced text back out after editing.
                The analyzer still consumes this exact text when you submit.
              </p>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
                <label htmlFor="team-import" className="[font-family:var(--font-display)] text-[0.68rem] uppercase tracking-[0.3em] text-white/40">
                  Active import
                </label>
                <span className="text-[0.68rem] uppercase tracking-[0.24em] text-white/28">
                  {parsedTeam.length > 0 ? `${parsedTeam.length} members parsed live` : "Paste a Showdown import to populate the builder"}
                </span>
              </div>

              <textarea
                id="team-import"
                value={teamText}
                onChange={(event) => handleManualTeamTextChange(event.target.value)}
                spellCheck={false}
                className="mt-4 min-h-[280px] w-full border-y border-[var(--line)] bg-transparent py-4 [font-family:var(--font-mono)] text-[13.5px] leading-6 text-white/88 outline-none placeholder:text-white/24 focus:border-[var(--line-strong)]"
                placeholder="Paste a Pokemon Showdown import here."
              />
            </details>
          </div>

          <aside className="space-y-8 xl:sticky xl:top-24">
            <div className="border-t border-[var(--line)] pt-6">
              <label
                htmlFor="regulation-select"
                className="[font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.32em] text-white/35"
              >
                Regulation Catalog
              </label>
              <div className="mt-3 border-y border-[var(--line)] py-2.5">
                <select
                  id="regulation-select"
                  value={selectedRegulationId}
                  onChange={(event) => handleRegulationChange(event.target.value)}
                  className="w-full bg-transparent text-sm leading-6 text-white/78 outline-none"
                >
                  {regulationOptions.map((regulation) => (
                    <option key={regulation.id} value={regulation.id} className="bg-[#090b10] text-white">
                      {regulation.display_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="mt-4 grid gap-x-4 gap-y-1 text-sm leading-6 text-white/44 sm:grid-cols-2 xl:grid-cols-1">
                <p>{activeRegulation.eligible_pokemon_count} eligible species</p>
                <p>{activeRegulation.allowed_held_item_count} allowed items</p>
                <p>{activeRegulation.allowed_mega_evolution_count} legal Mega forms</p>
              </div>

              <details className="mt-4 border-t border-[var(--line)] pt-4">
                <summary className="list-none cursor-pointer [font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.28em] text-white/46">
                  Regulation snapshot
                </summary>
                <p className="mt-3 text-sm leading-6 text-white/42">{activeRegulation.notes}</p>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[0.68rem] uppercase tracking-[0.22em] text-white/34">
                  <a href={activeRegulation.source_ruleset_url} target="_blank" rel="noreferrer" className="hover:text-white/74">
                    Ruleset
                  </a>
                  <a href={activeRegulation.source_eligible_pokemon_url} target="_blank" rel="noreferrer" className="hover:text-white/74">
                    Eligible Pokemon
                  </a>
                  <a href={activeRegulation.source_held_items_url} target="_blank" rel="noreferrer" className="hover:text-white/74">
                    Held Items
                  </a>
                </div>
              </details>
            </div>

            <div className="border-t border-[var(--line)] pt-6">
              <p className="[font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.34em] text-white/35">
                Live analysis
              </p>
              <p className="mt-4 text-sm leading-6 text-[var(--fg-muted)]">
                The dashboard refreshes automatically against {activeRegulation.display_name} once the roster is
                complete. Use the manual refresh only if you want to force an immediate rerun.
              </p>
              <div className="mt-4 grid gap-4 text-sm leading-6 text-white/44 sm:grid-cols-2 xl:grid-cols-1">
                <p>{filledBuilderCount} / {BUILDER_TEAM_SIZE} roster slots filled</p>
                <p>{analysis.team_size} members in the last successful analysis snapshot</p>
              </div>
              <p className={`mt-4 text-sm leading-6 ${rosterValidationMessage ? "text-[var(--negative)]" : "text-white/54"}`}>
                {liveAnalysisStatusMessage}
              </p>

              <button
                type="button"
                onClick={() => void runAnalysis(teamText, selectedRegulationId)}
                className="mt-6 border-b border-white pb-2 [font-family:var(--font-display)] text-[0.74rem] uppercase tracking-[0.26em] text-white transition-colors hover:text-[var(--accent)] disabled:border-white/20 disabled:text-white/25"
                disabled={isLoading || Boolean(rosterValidationMessage)}
              >
                {isLoading ? "Updating live analysis" : "Refresh now"}
              </button>

              {(errorMessage || legalityIssues.length > 0) && (
                <div className="mt-6 border-t border-[var(--line)] pt-4">
                  {errorMessage && <p className="text-sm leading-6 text-[var(--negative)]">{errorMessage}</p>}
                  {legalityIssues.length > 0 && (
                    <ul className="mt-3 space-y-1.5 text-sm leading-6 text-[var(--fg-muted)]">
                      {legalityIssues.map((issue) => (
                        <li key={issue}>{issue}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

          </aside>
        </section>

        {dashboardBlockingMessage ? (
          <DashboardErrorState
            message={dashboardBlockingMessage}
            details={dashboardBlockingDetails}
            isLoading={isLoading}
          />
        ) : null}

        <div className={dashboardBlockingMessage ? "hidden" : "contents"}>
        <section id="overview" className="grid gap-10 border-t border-[var(--line)] py-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
          <div>
            <p className="[font-family:var(--font-display)] text-[0.66rem] uppercase tracking-[0.34em] text-white/35">
              Output Snapshot
            </p>
            <h2 className="mt-3 [font-family:var(--font-display)] text-[1.34rem] uppercase tracking-[0.14em] text-white">
              Current overview
            </h2>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-[var(--fg-muted)]">
              {currentBuildTitle} reads as {formatLabel(analysis.team_archetype)} with a
              {" "}
              {teamStyleLabel} structure, a {modePackageLabel.toLowerCase()} mode package, and a
              {" "}
              {formatLabel(analysis.team_difficulty.label)} pilot load.
            </p>

            <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <CompactMetric label="Style shell" value={teamStyleLabel} />
              <CompactMetric
                label="Mode shell"
                value={modePackageLabel}
              />
              <CompactMetric label="Endgame plan" value={winConditionLabel} />
              <CompactMetric label="Utility load" value={`${analysis.utility_moves} actions`} />
              <CompactMetric label="Speed shape" value={formatLabel(analysis.speed_profile.team_tier)} />
              <CompactMetric
                label="Pilot load"
                value={`${formatLabel(analysis.team_difficulty.label)} · ${analysis.team_difficulty.score.toFixed(1)}/10`}
              />
            </div>

            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              <SummaryList
                heading="Good into"
                values={analysis.matchup_profile.favorable.map(formatLabel)}
                fallback="No strong positive broad matchups reported"
              />
              <SummaryList
                heading="Watch for"
                values={analysis.matchup_profile.unfavorable.map(formatLabel)}
                fallback="No major broad matchup liabilities reported"
              />
              <SummaryList
                heading="Weak points"
                values={analysis.top_defensive_weaknesses.map(formatLabel)}
                fallback="No standout defensive weak points"
              />
              <SummaryList
                heading="Role core"
                values={leadRoleLabels}
                fallback="No standout role cluster"
              />
            </div>
          </div>

          <div className="space-y-6 border-t border-[var(--line)] pt-6 lg:border-t-0 lg:border-l lg:border-[var(--line)] lg:pl-8 lg:pt-0">
            <SectionHeading eyebrow="Score lanes" title="Broad pressure and package reads" />
            <p className="max-w-2xl text-sm leading-6 text-[var(--fg-muted)]">
              These quick score rails split the roster into its broad pressure profile, package identity, and endgame
              plan so the shell reads cleanly before you dig into the deeper charts below.
            </p>
            <div className="space-y-6">
              <CompactScoreList heading="Broad pressure" rows={matchupRows.slice(0, 4)} />
              <CompactScoreList heading="Package identity" rows={packageModeRows} />
              <CompactScoreList heading="Endgame plan" rows={winConditionRows} />
            </div>
          </div>

          <div className="text-xs leading-6 text-white/38 lg:col-span-2">
            Builder edits reshape the roster immediately. Graphs, scores, and benchmark notes refresh when you rerun
            the analyzer.
          </div>
        </section>

        <MetricRail analysis={analysis} />

        <section id="roster" className="border-t border-[var(--line)] py-10">
          <SectionHeading eyebrow="Roster breakdown" title="Members, items, and benchmark hits" />
          <p className="mt-4 max-w-4xl text-sm leading-6 text-[var(--fg-muted)]">
            Builder edits update the parsed roster immediately. Analyzer-driven roles, normalized stats, speed
            contexts, and benchmark hits refresh from the last analysis run.
          </p>
          <div className="mt-8">
            {roster.map((member) => (
              <MemberRow key={member.displayName} member={member} />
            ))}
          </div>
        </section>

        <section id="graphs" className="grid gap-10 border-t border-[var(--line)] py-10 lg:grid-cols-2">
          <div className="space-y-6">
            <SectionHeading eyebrow="Speed architecture" title="Battle speed map" />
            <SpeedTrack analysis={analysis} />
            <DistributionChart distribution={analysis.speed_profile.distribution} />
            <PlainList heading="Benchmark notes" values={analysis.speed_profile.benchmarks.notes} />
            <div className="border-t border-[var(--line)] pt-6">
              <SectionHeading eyebrow="Team notes" title="Difficulty and builder guidance" />
              <div className="mt-6 space-y-6">
                <PlainList heading="Difficulty factors" values={analysis.team_difficulty.factors} />
                <PlainList
                  heading="Builder guidance"
                  values={analysis.beginner_guidance.notes.length ? analysis.beginner_guidance.notes : ["No major beginner-facing build issues flagged."]}
                />
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <SectionHeading eyebrow="Matchup outlook" title="Pressure and liabilities" />
            <DivergingBars
              heading="Broad archetype profile"
              rows={matchupRows}
              positiveColor="var(--positive)"
              negativeColor="var(--negative)"
            />
            <DivergingBars
              heading="Tournament mode pressure"
              rows={modeRows}
              positiveColor="var(--accent)"
              negativeColor="var(--negative)"
            />
          </div>
        </section>

        <section id="meta" className="grid gap-10 border-t border-[var(--line)] py-10 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <div className="space-y-6">
            <SectionHeading eyebrow="Meta analysis" title="Current Regulation M-A field" />
            <p className="max-w-3xl text-sm leading-6 text-[var(--fg-muted)]">
              This layer reweights the team&apos;s mode matchups against the current Regulation M-A tournament shell mix, so the dashboard
              can show where the roster is actually well positioned and where the live field still pushes back.
            </p>
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
              <CompactMetric label="Standing" value={formatLabel(analysis.meta_analysis.label)} />
              <CompactMetric label="Weighted score" value={analysis.meta_analysis.overall_score.toFixed(2)} />
              <CompactMetric
                label="Favored field share"
                value={`${analysis.meta_analysis.positive_weight_share.toFixed(1)}%`}
              />
              <CompactMetric
                label="Pressure share"
                value={`${analysis.meta_analysis.negative_weight_share.toFixed(1)}%`}
              />
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <SummaryList
                heading="Strongest current edges"
                values={analysis.meta_analysis.strongest_targets}
                fallback="No standout weighted meta edge"
              />
              <SummaryList
                heading="Most relevant pressure"
                values={analysis.meta_analysis.pressured_targets}
                fallback="No major weighted meta pressure"
              />
            </div>
            <PlainList
              heading="Meta notes"
              values={analysis.meta_analysis.notes.length ? analysis.meta_analysis.notes : ["No extra meta notes were generated."]}
            />
            <MetaCommonPokemonBoard rows={analysis.meta_analysis.common_pokemon ?? []} />
          </div>

          <div className="space-y-6">
            <MetaImpactBoard rows={analysis.meta_analysis.tournament_rows} />
          </div>
        </section>

        <section id="preview" className="grid gap-10 border-t border-[var(--line)] py-10 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <div className="space-y-6">
            <SectionHeading eyebrow="Team preview" title="Pick-4 plan browser" />
            <p className="max-w-4xl text-sm leading-6 text-[var(--fg-muted)]">
              Browse every generated preview line here, including the default bring. The selector keeps the exhaustive
              plan list compact without hiding the baseline line.
            </p>
            {activePreviewPlan ? (
              <div className="space-y-6">
                <div className="border-y border-[var(--line)] py-5">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                    <label className="min-w-0 flex-1 space-y-2">
                      <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                        Choose plan
                      </span>
                      <select
                        value={activePreviewPlan.label}
                        onChange={(event) => setSelectedPreviewPlanLabel(event.target.value)}
                        className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
                      >
                        {previewPlans.map((plan, index) => (
                          <option key={plan.label} value={plan.label} className="bg-[#090b10] text-white">
                            {index === 0 ? `Default: ${plan.label}` : plan.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <div className="text-right text-[0.7rem] uppercase tracking-[0.22em] text-white/28">
                      {previewPlans.length} total plans
                    </div>
                  </div>
                </div>

                <TeamPreviewPlanCard plan={activePreviewPlan} rosterLookup={rosterLookup} />
              </div>
            ) : analysis.team_preview.bring_plans.length ? (
              <div className="grid gap-6 xl:grid-cols-2">
                {analysis.team_preview.bring_plans.map((plan) => (
                  <TeamPreviewPlanCard key={plan.label} plan={plan} rosterLookup={rosterLookup} />
                ))}
              </div>
            ) : (
              <p className="border-t border-[var(--line)] pt-4 text-sm leading-6 text-white/52">
                No preview defaults were generated for this roster.
              </p>
            )}
          </div>

          <div className="space-y-6">
            <SectionHeading eyebrow="Preview notes" title="Threats, positioning, and counterplay" />
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-1">
              <PlainList
                heading="Watch teams"
                values={analysis.team_preview.watch_teams.length ? analysis.team_preview.watch_teams : ["No standout mode shells flagged."]}
              />
              <PlainList
                heading="Watch Pokemon"
                values={watchPokemonNotes}
              />
            </div>
            <PlainList
              heading="Positioning plan"
              values={analysis.team_preview.strategy_notes.length ? analysis.team_preview.strategy_notes : ["No extra positioning notes were generated."]}
            />
            <PlainList
              heading="Counterplay plan"
              values={analysis.team_preview.counterplay_notes.length ? analysis.team_preview.counterplay_notes : ["No extra counterplay notes were generated."]}
            />
          </div>
        </section>

        <section className="grid gap-10 border-t border-[var(--line)] py-10 lg:grid-cols-2">
          <div className="space-y-6">
            <SectionHeading eyebrow="Type profile" title="Coverage and exposure" />
            <BarLedger
              heading="Typing density"
              rows={typingRows}
              valueFormatter={(value) => `${value} member${value === 1 ? "" : "s"}`}
              accentResolver={(label) => TYPE_ACCENTS[label] ?? "var(--accent)"}
            />
            <BarLedger
              heading="Offensive coverage"
              rows={coverageRows}
              valueFormatter={(value) => `${value} attacking line${value === 1 ? "" : "s"}`}
              accentResolver={(label) => TYPE_ACCENTS[label] ?? "var(--accent)"}
            />
            <PlainList
              heading="Coverage gaps"
              values={coverageGapNotes.length ? coverageGapNotes : ["No clear type coverage gaps detected."]}
            />
            <BarLedger
              heading="Defensive exposure"
              rows={defensiveRows}
              valueFormatter={(value, row) => `${value.toFixed(2)}x average taken · ${row.note}`}
              accentResolver={() => "var(--negative)"}
            />
          </div>

          <div className="space-y-6">
            <SectionHeading eyebrow="Role structure" title="Utility and member roles" />
            <BarLedger
              heading="Utility actions"
              rows={utilityRows}
              valueFormatter={(value, row) => `${value} · ${(row.note ?? "").trim() || "No move list"}`}
              accentResolver={() => "var(--warning)"}
            />
            <BarLedger
              heading="Pokemon roles"
              rows={roleRows}
              valueFormatter={(value, row) => `${value} · ${(row.note ?? "").trim() || "No members"}`}
              accentResolver={() => "var(--accent)"}
            />
          </div>
        </section>
        </div>

      </main>
    </div>
  );
}

function DashboardErrorState({
  message,
  details,
  isLoading,
}: {
  message: string;
  details: string[];
  isLoading: boolean;
}) {
  return (
    <section id="overview" className="border-t border-[var(--line)] py-10">
      <div className="max-w-4xl border-y border-[var(--line)] py-8">
        <SectionHeading eyebrow="Dashboard paused" title="Complete the roster to unlock live analysis" />
        <p className="mt-5 text-base leading-7 text-[var(--negative)]">{message}</p>
        {details.length ? (
          <ul className="mt-4 space-y-2 text-sm leading-6 text-white/58">
            {details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
        ) : null}
        <p className="mt-5 text-sm leading-6 text-white/46">
          Fill all six builder slots or paste a full Showdown import above. Once the roster is complete, the overview,
          preview, meta board, and all downstream charts will resume updating live.
        </p>
        {isLoading ? <p className="mt-4 text-sm leading-6 text-white/38">A live analysis request is still finishing.</p> : null}
      </div>
    </section>
  );
}

function renderInlineDocumentText(text: string): ReactNode {
  return text
    .split(/(`[^`]+`)/g)
    .filter(Boolean)
    .map((fragment, index) =>
      fragment.startsWith("`") && fragment.endsWith("`") ? (
        <code
          key={`${fragment}-${index}`}
          className="rounded bg-white/8 px-1.5 py-0.5 text-[0.92em] text-white/86"
        >
          {fragment.slice(1, -1)}
        </code>
      ) : (
        <span key={`${fragment}-${index}`}>{fragment}</span>
      ),
    );
}

type SiteDocumentBlock =
  | { type: "heading1"; text: string }
  | { type: "heading2"; text: string }
  | { type: "heading3"; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] };

function parseSiteDocument(content: string) {
  const blocks: SiteDocumentBlock[] = [];
  const paragraphLines: string[] = [];
  const listItems: string[] = [];

  function flushParagraph() {
    if (!paragraphLines.length) {
      return;
    }

    blocks.push({ type: "paragraph", text: paragraphLines.join(" ") });
    paragraphLines.length = 0;
  }

  function flushList() {
    if (!listItems.length) {
      return;
    }

    blocks.push({ type: "list", items: [...listItems] });
    listItems.length = 0;
  }

  for (const rawLine of content.split(/\r?\n/)) {
    const trimmedLine = rawLine.trim();

    if (!trimmedLine) {
      flushParagraph();
      flushList();
      continue;
    }

    if (trimmedLine.startsWith("### ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading3", text: trimmedLine.slice(4) });
      continue;
    }

    if (trimmedLine.startsWith("## ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading2", text: trimmedLine.slice(3) });
      continue;
    }

    if (trimmedLine.startsWith("# ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading1", text: trimmedLine.slice(2) });
      continue;
    }

    if (trimmedLine.startsWith("- ")) {
      flushParagraph();
      listItems.push(trimmedLine.slice(2));
      continue;
    }

    flushList();
    paragraphLines.push(trimmedLine);
  }

  flushParagraph();
  flushList();

  return blocks;
}

function SiteDocumentBody({ content }: { content: string }) {
  const blocks = parseSiteDocument(content);

  return (
    <div className="space-y-5 text-[0.97rem] leading-7 text-[var(--fg-muted)]">
      {blocks.map((block, index) => {
        if (block.type === "heading1") {
          return (
            <h2
              key={`${block.type}-${index}`}
              className="[font-family:var(--font-title)] text-[2rem] font-semibold uppercase tracking-[0.08em] text-white sm:text-[2.4rem]"
            >
              {block.text}
            </h2>
          );
        }

        if (block.type === "heading2") {
          return (
            <h3
              key={`${block.type}-${index}`}
              className="pt-3 [font-family:var(--font-display)] text-[0.72rem] uppercase tracking-[0.28em] text-white/40"
            >
              {block.text}
            </h3>
          );
        }

        if (block.type === "heading3") {
          return (
            <h4 key={`${block.type}-${index}`} className="text-lg font-semibold text-white/90">
              {block.text}
            </h4>
          );
        }

        if (block.type === "list") {
          return (
            <ul key={`${block.type}-${index}`} className="space-y-3 pl-5 marker:text-white/46">
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`} className="list-disc">
                  {renderInlineDocumentText(item)}
                </li>
              ))}
            </ul>
          );
        }

        return (
          <p key={`${block.type}-${index}`} className="text-[0.98rem] leading-7 text-[var(--fg-muted)]">
            {renderInlineDocumentText(block.text)}
          </p>
        );
      })}
    </div>
  );
}

function SiteDocumentDialog({
  activeDocument,
  documents,
  onClose,
  onOpenDocument,
}: {
  activeDocument: SiteDocument | null;
  documents: SiteDocument[];
  onClose: () => void;
  onOpenDocument: (documentId: SiteDocumentId) => void;
}) {
  if (!activeDocument) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 bg-[#04060b]/84 px-4 py-6 sm:px-6" onClick={onClose}>
      <div className="mx-auto flex h-full w-full max-w-5xl items-start justify-center">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="site-document-title"
          className="mt-10 flex max-h-[calc(100vh-5rem)] w-full flex-col overflow-hidden border border-[var(--line)] bg-[#090b10]/96 shadow-[0_28px_80px_rgba(0,0,0,0.55)] backdrop-blur"
          onClick={(event) => event.stopPropagation()}
        >
          <div className="flex items-start justify-between gap-4 border-b border-[var(--line)] px-5 py-5 sm:px-7">
            <div className="max-w-3xl">
              <p className="[font-family:var(--font-display)] text-[0.64rem] uppercase tracking-[0.3em] text-white/34">
                {activeDocument.eyebrow}
              </p>
              <h2 id="site-document-title" className="mt-3 text-2xl font-semibold text-white sm:text-[2rem]">
                {activeDocument.title}
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--fg-muted)]">{activeDocument.description}</p>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="border border-white/18 px-3 py-2 [font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.22em] text-white/66 transition hover:border-white/40 hover:text-white"
            >
              Close
            </button>
          </div>

          <div className="flex flex-wrap gap-2 border-b border-[var(--line)] px-5 py-3 sm:px-7">
            {documents.map((document) => {
              const isActive = document.id === activeDocument.id;

              return (
                <button
                  key={document.id}
                  type="button"
                  onClick={() => onOpenDocument(document.id)}
                  className={[
                    "px-3 py-2 [font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.22em] transition",
                    isActive
                      ? "border border-white/48 bg-white/10 text-white"
                      : "border border-white/12 text-white/58 hover:border-white/28 hover:text-white",
                  ].join(" ")}
                >
                  {document.label}
                </button>
              );
            })}
          </div>

          <div className="overflow-y-auto px-5 py-6 sm:px-7 sm:py-7">
            <SiteDocumentBody content={activeDocument.content} />
          </div>
        </div>
      </div>
    </div>
  );
}

function SiteHeader({
  regulationLabel,
  documentLinks,
  onOpenDocument,
}: {
  regulationLabel: string;
  documentLinks: Array<{ id: SiteDocumentId; label: string }>;
  onOpenDocument: (documentId: SiteDocumentId) => void;
}) {
  const navItems = [
    { href: "#overview", label: "Overview" },
    { href: "#roster", label: "Roster" },
    { href: "#analyze", label: "Analyze" },
    { href: "#graphs", label: "Graphs" },
    { href: "#meta", label: "Meta" },
    { href: "#preview", label: "Preview" },
  ];

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--line)] bg-black/35 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1680px] flex-wrap items-center justify-between gap-4 px-5 py-4 sm:px-8 lg:px-10">
        <div className="[font-family:var(--font-display)] text-[0.72rem] uppercase tracking-[0.42em] text-white/38">
          PCA
        </div>
        <nav className="hidden items-center gap-7 md:flex">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="[font-family:var(--font-display)] text-[0.68rem] uppercase tracking-[0.26em] text-white/64 transition-colors hover:text-white"
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="flex flex-wrap items-center justify-end gap-2 sm:gap-3">
          {documentLinks.map((document) => (
            <button
              key={document.id}
              type="button"
              onClick={() => onOpenDocument(document.id)}
              className="border border-white/14 px-3 py-2 [font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.22em] text-white/70 transition hover:border-white/36 hover:text-white"
            >
              {document.label}
            </button>
          ))}

          <div className="min-w-[150px] text-right sm:min-w-[170px]">
            <p className="[font-family:var(--font-display)] text-[0.64rem] uppercase tracking-[0.3em] text-white/32">
              Pokemon Champions
            </p>
            <p className="mt-1.5 text-sm text-white/58">{regulationLabel}</p>
          </div>
        </div>
      </div>
    </header>
  );
}

function TeamBuilderSlotRail({
  members,
  selectedIndex,
  regulationId,
  onSelect,
}: {
  members: ParsedTeamMember[];
  selectedIndex: number;
  regulationId: string;
  onSelect: (index: number) => void;
}) {
  return (
    <div className="mt-5 space-y-2.5">
      {members.map((member, index) => {
        const isActive = index === selectedIndex;
        const assignedStatPoints = totalEffortValues(member.evs);
        const moveCount = countFilledMoves(member.moves);
        const primaryLabel = member.displayName.trim() || member.species.trim() || "Empty slot";
        const secondaryLabel = member.species.trim()
          ? `${member.item?.trim() || "No item"} · ${member.ability?.trim() || "No ability"}`
          : "Choose a species to start building.";

        return (
          <button
            key={`builder-slot-${index + 1}`}
            type="button"
            onClick={() => onSelect(index)}
            className={`block w-full border px-3 py-3 text-left transition-colors ${
              isActive
                ? "border-white/70 bg-white/6"
                : "border-[var(--line)] bg-transparent hover:border-white/28 hover:bg-white/[0.03]"
            }`}
          >
            <div className="flex items-start gap-3">
              {member.species.trim() ? (
                <PokemonSprite species={member.species} label={primaryLabel} small />
              ) : (
                <div className="flex h-14 w-14 items-center justify-center border border-[var(--line)] [font-family:var(--font-display)] text-[0.68rem] uppercase tracking-[0.22em] text-white/30 sm:h-16 sm:w-16">
                  {String(index + 1).padStart(2, "0")}
                </div>
              )}

              <div className="min-w-0 flex-1">
                <p className="[font-family:var(--font-display)] text-[0.54rem] uppercase tracking-[0.3em] text-white/34">
                  Slot {index + 1}
                </p>
                <p className="mt-2 truncate text-sm leading-6 text-white/84">{primaryLabel}</p>
                {member.species.trim() ? (
                  <BuilderSpeciesTypingBadges
                    key={`${member.species}-${regulationId}-compact`}
                    species={member.species}
                    regulationId={regulationId}
                    compact
                    className="mt-2"
                  />
                ) : null}
                <p className="truncate text-[11px] uppercase tracking-[0.16em] text-white/34">{secondaryLabel}</p>
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between gap-4 border-t border-[var(--line)] pt-3 text-[11px] uppercase tracking-[0.16em] text-white/36">
              <span>{moveCount} / {BUILDER_MOVE_COUNT} moves</span>
              <span>{assignedStatPoints} / {CHAMPIONS_TOTAL_SPS} SP</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function TeamBuilderEditor({
  member,
  slotIndex,
  speciesOptions,
  speciesTypes,
  regulationId,
  lockedItem,
  speciesChoices,
  itemChoices,
  abilityChoices,
  moveChoices,
  isSpeciesOptionsLoading,
  speciesOptionsError,
  onFieldChange,
  onMoveChange,
  onEvChange,
  onClear,
}: {
  member: ParsedTeamMember;
  slotIndex: number;
  speciesOptions: BuilderSpeciesOptions | null;
  speciesTypes: string[];
  regulationId: string;
  lockedItem: string | null;
  speciesChoices: string[];
  itemChoices: string[];
  abilityChoices: string[];
  moveChoices: string[];
  isSpeciesOptionsLoading: boolean;
  speciesOptionsError: string | null;
  onFieldChange: (
    slotIndex: number,
    field: "species" | "item" | "ability" | "nature" | "level",
    value: string,
  ) => void;
  onMoveChange: (slotIndex: number, moveIndex: number, value: string) => void;
  onEvChange: (slotIndex: number, stat: EffortValueStat, value: string) => void;
  onClear: (slotIndex: number) => void;
}) {
  const title = member.displayName.trim() || member.species.trim() || `Slot ${slotIndex + 1}`;
  const assignedStatPoints = totalEffortValues(member.evs);
  const budgetDelta = CHAMPIONS_TOTAL_SPS - assignedStatPoints;
  const budgetMessage =
    budgetDelta >= 0 ? `${budgetDelta} SP remaining` : `${Math.abs(budgetDelta)} SP over budget`;
  const liveStats = speciesOptions ? buildLiveMemberStats(member, speciesOptions.base_stats) : null;

  return (
    <section className="space-y-8">
      <div className="flex flex-col gap-5 border-b border-[var(--line)] pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-4">
          {member.species.trim() ? (
            <PokemonSprite species={member.species} label={title} />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center border border-[var(--line)] [font-family:var(--font-display)] text-[0.76rem] uppercase tracking-[0.24em] text-white/30 lg:h-24 lg:w-24">
              Slot {slotIndex + 1}
            </div>
          )}

          <div>
            <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.32em] text-white/36">
              Pokebase Builder
            </p>
            <h3 className="mt-3 [font-family:var(--font-display)] text-[1.18rem] uppercase tracking-[0.14em] text-white sm:text-[1.32rem]">
              {title}
            </h3>
            {member.species.trim() ? (
              <BuilderSpeciesTypingBadges
                key={`${member.species}-${regulationId}-expanded`}
                species={member.species}
                regulationId={regulationId}
                initialTypes={speciesTypes}
                className="mt-3"
              />
            ) : null}
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--fg-muted)]">
              Tune the set details here. Changes sync straight into the Showdown export below.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => onClear(slotIndex)}
          className="border-b border-white/60 pb-2 [font-family:var(--font-display)] text-[0.7rem] uppercase tracking-[0.24em] text-white/78 transition-colors hover:text-[var(--accent)]"
        >
          Clear slot
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
            Species
          </span>
          <select
            value={member.species}
            onChange={(event) => onFieldChange(slotIndex, "species", event.target.value)}
            className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
          >
            <option value="" className="bg-[#090b10] text-white">Select species</option>
            {speciesChoices.map((option) => (
              <option key={option} value={option} className="bg-[#090b10] text-white">
                {option}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-2">
          <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
            Item
          </span>
          <select
            value={lockedItem ?? member.item ?? ""}
            onChange={(event) => onFieldChange(slotIndex, "item", event.target.value)}
            disabled={Boolean(lockedItem)}
            className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45 disabled:border-white/10 disabled:text-white/28"
          >
            <option value="" className="bg-[#090b10] text-white">No item</option>
            {itemChoices.map((option) => (
              <option key={option} value={option} className="bg-[#090b10] text-white">
                {option}
              </option>
            ))}
          </select>
          {lockedItem ? <p className="text-xs leading-5 text-white/42">Locked to {lockedItem} for this Mega Evolution.</p> : null}
        </label>

        <label className="space-y-2">
          <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
            Ability
          </span>
          <select
            value={member.ability ?? ""}
            onChange={(event) => onFieldChange(slotIndex, "ability", event.target.value)}
            disabled={!member.species.trim() || isSpeciesOptionsLoading}
            className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45 disabled:border-white/10 disabled:text-white/28"
          >
            <option value="" className="bg-[#090b10] text-white">Select ability</option>
            {abilityChoices.map((option) => (
              <option key={option} value={option} className="bg-[#090b10] text-white">
                {option}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-2">
          <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
            Nature
          </span>
          <select
            value={member.nature ?? ""}
            onChange={(event) => onFieldChange(slotIndex, "nature", event.target.value)}
            className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
          >
            <option value="" className="bg-[#090b10] text-white">Select nature</option>
            {NATURE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value} className="bg-[#090b10] text-white">
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="border-t border-[var(--line)] pt-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.3em] text-white/34">
              Moves
            </p>
          </div>
          <p className={`text-[0.68rem] uppercase tracking-[0.22em] ${speciesOptionsError ? "text-[var(--negative)]" : "text-white/34"}`}>
            {countFilledMoves(member.moves)} / {BUILDER_MOVE_COUNT} filled
          </p>
        </div>
        <p className={`mt-2 text-sm leading-6 ${speciesOptionsError ? "text-[var(--negative)]" : "text-white/42"}`}>
            {speciesOptionsError
              ? speciesOptionsError
              : isSpeciesOptionsLoading
                ? "Loading ability and move options..."
                : member.species.trim()
                  ? `${abilityChoices.length} abilities · ${moveChoices.length} moves available`
                  : "No species selected yet."}
        </p>

        <div className="mt-6 grid gap-5 md:grid-cols-2 md:gap-6">
          {Array.from({ length: BUILDER_MOVE_COUNT }, (_, moveIndex) => {
            const moveValue = member.moves[moveIndex] ?? "";
            const availableMoveChoices = buildSelectOptions(moveValue, moveChoices);
            const trimmedMove = moveValue.trim();

            return (
              <div key={`move-slot-${moveIndex + 1}`} className="flex h-full flex-col gap-4">
                <label className="block space-y-2">
                  <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                    Move {moveIndex + 1}
                  </span>
                  <select
                    value={moveValue}
                    onChange={(event) => onMoveChange(slotIndex, moveIndex, event.target.value)}
                    disabled={!member.species.trim() || isSpeciesOptionsLoading}
                    className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45 disabled:border-white/10 disabled:text-white/28"
                  >
                    <option value="" className="bg-[#090b10] text-white">Select move</option>
                    {availableMoveChoices.map((option) => (
                      <option key={`${moveIndex}-${option}`} value={option} className="bg-[#090b10] text-white">
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                {trimmedMove ? (
                  <BuilderMoveDetailCard
                    key={`builder-move-details-${slotIndex}-${moveIndex}-${normalizeAssetId(trimmedMove)}`}
                    moveName={trimmedMove}
                  />
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      <div className="border-t border-[var(--line)] pt-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.3em] text-white/34">
              SP spread
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--fg-muted)]">
              The Champions builder stores stat points in the Showdown EV slots for analyzer compatibility.
            </p>
          </div>
          <div className="text-sm leading-6 text-right">
            <p className="text-white/72">{assignedStatPoints} / {CHAMPIONS_TOTAL_SPS} assigned</p>
            <p className={budgetDelta >= 0 ? "text-white/42" : "text-[var(--negative)]"}>{budgetMessage}</p>
          </div>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {MEMBER_STAT_ORDER.map(({ key, label }) => {
            const evKey = key as EffortValueStat;
            return (
              <label key={`sp-${evKey}`} className="space-y-2">
                <span className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
                  {label}
                </span>
                <input
                  type="number"
                  min={0}
                  max={CHAMPIONS_TOTAL_SPS}
                  step={1}
                  value={member.evs[evKey] ?? ""}
                  onChange={(event) => onEvChange(slotIndex, evKey, event.target.value)}
                  className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
                  placeholder="0"
                />
              </label>
            );
          })}
        </div>

        {member.species.trim() ? (
          liveStats ? (
            <BuilderStatPreview member={member} stats={liveStats} forcedItem={lockedItem} />
          ) : (
            <p className="mt-5 text-sm leading-6 text-white/42">
              {isSpeciesOptionsLoading ? "Loading live stat preview..." : "Species stats are unavailable for the selected Pokemon."}
            </p>
          )
        ) : null}

        <p className="mt-4 text-xs leading-6 text-white/34">
          Entries that exceed the remaining budget are clipped automatically when you type.
        </p>
      </div>
    </section>
  );
}

function MetricRail({ analysis }: { analysis: PokemonTeamAnalysis }) {
  const styleLabel = formatLabel(analysis.team_package_profile.style.label);
  const modePackageLabel = analysis.team_package_profile.modes.labels.length
    ? analysis.team_package_profile.modes.labels.map(formatLabel).join(" / ")
    : "No dominant mode package";
  const winConditionLabel = analysis.team_package_profile.win_conditions.labels.length
    ? analysis.team_package_profile.win_conditions.labels.map(formatLabel).join(" / ")
    : "No clear endgame plan";
  const items = [
    {
      label: "Primary",
      value: formatLabel(analysis.team_archetype),
    },
    {
      label: "Style shell",
      value: styleLabel,
    },
    {
      label: "Mode package",
      value: modePackageLabel,
    },
    {
      label: "Endgame plan",
      value: winConditionLabel,
    },
    {
      label: "Speed tier",
      value: formatLabel(analysis.speed_profile.team_tier),
    },
    {
      label: "Pilot load",
      value: `${formatLabel(analysis.team_difficulty.label)} · ${analysis.team_difficulty.score.toFixed(1)}`,
    },
    {
      label: "Good into",
      value: analysis.matchup_profile.favorable.length
        ? analysis.matchup_profile.favorable.map(formatLabel).join(" / ")
        : "No standout edge",
    },
    {
      label: "Watch for",
      value: analysis.matchup_profile.unfavorable.length
        ? analysis.matchup_profile.unfavorable.map(formatLabel).join(" / ")
        : "No major liability",
    },
    {
      label: "Utility",
      value: `${analysis.utility_moves} actions`,
    },
  ];

  return (
    <div id="overview" className="mt-7 grid gap-4 border-y border-[var(--line)] py-5 md:grid-cols-2 md:gap-0 lg:grid-cols-3 2xl:grid-cols-6">
      {items.map((item, index) => (
        <div
          key={item.label}
          className={`pr-4 ${index < items.length - 1 ? "2xl:border-r 2xl:border-[var(--line)] 2xl:pr-5" : ""} ${index > 0 ? "2xl:pl-5" : ""}`}
        >
          <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.3em] text-white/34">
            {item.label}
          </p>
          <p className="mt-2.5 text-sm leading-6 text-white/88 sm:text-[0.95rem]">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

function CompactMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t border-[var(--line)] pt-3">
      <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.3em] text-white/34">
        {label}
      </p>
      <p className="mt-2 text-sm leading-6 text-white/88">{value}</p>
    </div>
  );
}

function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div>
      <p className="[font-family:var(--font-display)] text-[0.64rem] uppercase tracking-[0.34em] text-white/35">
        {eyebrow}
      </p>
      <h2 className="mt-3 [font-family:var(--font-display)] text-[1.2rem] uppercase tracking-[0.14em] text-white sm:text-[1.32rem]">
        {title}
      </h2>
    </div>
  );
}

function SummaryList({ heading, values, fallback }: { heading: string; values: string[]; fallback: string }) {
  return (
    <div>
      <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.28em] text-white/34">
        {heading}
      </p>
      <p className="mt-2 text-sm leading-6 text-white/68">{values.length ? values.join(" / ") : fallback}</p>
    </div>
  );
}

function CompactScoreList({ heading, rows }: { heading: string; rows: Array<{ label: string; value: number; note?: string }> }) {
  return (
    <div>
      <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.28em] text-white/34">
        {heading}
      </p>
      <div className="mt-3 space-y-2.5">
        {rows.map((row) => {
          const valueText = row.value > 0 ? `+${row.value.toFixed(2)}` : row.value.toFixed(2);
          return (
            <div key={row.label} className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4 border-t border-[var(--line)] pt-2.5">
              <div>
                <span className="text-sm leading-6 text-white/72">{formatLabel(row.label)}</span>
                {row.note ? <p className="mt-1 text-xs leading-5 text-white/42">{row.note}</p> : null}
              </div>
              <span className={`font-mono text-xs ${row.value >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"}`}>
                {valueText}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SpeedTrack({ analysis }: { analysis: PokemonTeamAnalysis }) {
  const members = analysis.speed_profile.members;
  const benchmarks = analysis.speed_profile.benchmarks.groups.natural?.benchmarks ?? [];
  const numericFloor = Math.min(...members.map((member) => member.battle_speed), ...benchmarks.map((row) => row.target_speed)) - 12;
  const numericCeiling = Math.max(...members.map((member) => member.battle_speed), ...benchmarks.map((row) => row.target_speed)) + 12;
  const minValue = Math.max(0, numericFloor);
  const maxValue = numericCeiling;
  const width = 940;
  const height = 260;
  const paddingX = 58;
  const baseline = 150;
  const chartWidth = width - paddingX * 2;
  const scale = (value: number) => paddingX + ((value - minValue) / Math.max(1, maxValue - minValue)) * chartWidth;
  const ticks = 6;

  return (
    <div className="border-y border-[var(--line)] py-6">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full overflow-visible">
        {Array.from({ length: ticks + 1 }, (_, index) => {
          const value = minValue + ((maxValue - minValue) / ticks) * index;
          const x = scale(value);
          return (
            <g key={value}>
              <line x1={x} y1={52} x2={x} y2={210} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 8" />
              <text x={x} y={230} fill="rgba(244,246,251,0.42)" fontSize="12" textAnchor="middle">
                {Math.round(value)}
              </text>
            </g>
          );
        })}

        <line x1={paddingX} y1={baseline} x2={width - paddingX} y2={baseline} stroke="rgba(255,255,255,0.16)" />

        {benchmarks.map((benchmark) => {
          const x = scale(benchmark.target_speed);
          return (
            <g key={benchmark.slug}>
              <line x1={x} y1={62} x2={x} y2={baseline} stroke="rgba(111,211,255,0.28)" strokeDasharray="3 6" />
              <text x={x} y={42} fill="rgba(244,246,251,0.45)" fontSize="12" textAnchor="middle">
                {benchmark.label.replace(/^Timid |^Jolly /, "")}
              </text>
            </g>
          );
        })}

        {members.map((member, index) => {
          const x = scale(member.battle_speed);
          const y = index % 2 === 0 ? baseline - 48 - (index % 3) * 6 : baseline + 48 + (index % 3) * 6;
          const textY = index % 2 === 0 ? y - 10 : y + 18;

          return (
            <g key={member.pokemon}>
              <line x1={x} y1={baseline} x2={x} y2={y} stroke="rgba(255,255,255,0.25)" />
              <circle cx={x} cy={baseline} r={7} fill="rgba(6,7,10,1)" stroke="var(--accent)" strokeWidth="2" />
              <circle cx={x} cy={y} r={4} fill="var(--accent)" />
              <text x={x} y={textY} fill="rgba(244,246,251,0.9)" fontSize="12" textAnchor="middle">
                {member.pokemon}
              </text>
              <text x={x} y={textY + 16} fill="rgba(244,246,251,0.45)" fontSize="11" textAnchor="middle">
                {member.battle_speed} · {formatLabel(member.tier)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function DistributionChart({ distribution }: { distribution: PokemonTeamAnalysis["speed_profile"]["distribution"] }) {
  const entries = Object.entries(distribution);
  const maxValue = Math.max(...entries.map(([, details]) => details.count), 1);

  return (
    <div>
      <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.28em] text-white/34">
        Tier distribution
      </p>
      <div className="mt-4 grid grid-cols-3 gap-4 lg:grid-cols-6">
        {entries.map(([label, details]) => (
          <div key={label}>
            <div className="flex h-20 items-end border-b border-[var(--line)] pb-2.5">
              <div
                className="w-full bg-[var(--accent)]"
                style={{
                  height: `${(details.count / maxValue) * 100}%`,
                  opacity: details.count === 0 ? 0.18 : 0.9,
                }}
              />
            </div>
            <p className="mt-2.5 text-[11px] uppercase tracking-[0.16em] text-white/46">{formatLabel(label)}</p>
            <p className="mt-1.5 text-sm text-white/74">{details.count}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function PlainList({ heading, values }: { heading: string; values: string[] }) {
  return (
    <div>
      <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.28em] text-white/34">
        {heading}
      </p>
      <div className="mt-3 space-y-2.5">
        {values.map((value) => (
          <div key={value} className="border-t border-[var(--line)] pt-2.5 text-sm leading-6 text-white/68">
            {value}
          </div>
        ))}
      </div>
    </div>
  );
}

function MetaCommonPokemonBoard({ rows }: { rows: MetaCommonPokemonRowData[] }) {
  if (!rows.length) {
    return null;
  }

  return (
    <div>
      <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.28em] text-white/34">
        Most common meta Pokemon
      </p>
      <div className="mt-3 grid gap-4 xl:grid-cols-2">
        {rows.map((row) => (
          <article key={row.species} className="border border-[var(--line)] bg-black/30 px-4 py-4">
            <div className="flex items-start justify-between gap-4">
              <p className="text-sm leading-6 text-white/82">{row.species}</p>
              <span className="text-[0.68rem] uppercase tracking-[0.18em] text-[var(--accent)]">
                {row.meta_share.toFixed(1)}% board share
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-white/60">
              <span className="text-white/38">Why it is used:</span> {row.why_used}
            </p>
            <p className="mt-3 text-sm leading-6 text-white/60">
              <span className="text-white/38">What it does:</span> {row.what_it_does}
            </p>
            {row.featured_teams.length ? (
              <p className="mt-3 border-t border-[var(--line)] pt-3 text-sm leading-6 text-white/52">
                <span className="text-white/34">Common shells:</span> {row.featured_teams.join(" / ")}
              </p>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

function TeamPreviewPlanCard({
  plan,
  rosterLookup,
}: {
  plan: TeamPreviewPlanCardData;
  rosterLookup: Map<string, RosterEntry>;
}) {
  return (
    <article className="border-y border-[var(--line)] py-5">
      <p className="[font-family:var(--font-display)] text-[0.68rem] uppercase tracking-[0.26em] text-white/38">
        {plan.label}
      </p>
      <p className="mt-3 text-sm leading-6 text-white/72">{plan.summary}</p>
      <div className="mt-5 space-y-4">
        <PreviewMemberStrip label="Lead" members={plan.leads} rosterLookup={rosterLookup} />
        <PreviewMemberStrip label="Back" members={plan.back} rosterLookup={rosterLookup} />
        <PreviewReasonList members={plan.pick_four} reasons={plan.member_reasons} rosterLookup={rosterLookup} />
      </div>
    </article>
  );
}

function BuilderMoveDetailCard({ moveName }: { moveName: string }) {
  const [details, setDetails] = useState<BuilderMoveDetails | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const trimmedMoveName = moveName.trim();
    if (!trimmedMoveName) {
      return;
    }

    const abortController = new AbortController();

    void fetch(`/api/builder-move?move=${encodeURIComponent(trimmedMoveName)}`, {
      signal: abortController.signal,
    })
      .then(async (response) => {
        const payload = (await response.json()) as BuilderMoveDetails & { message?: string };

        if (!response.ok) {
          throw new Error(payload.message ?? "The builder move request failed.");
        }

        setDetails(payload);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (abortController.signal.aborted) {
          return;
        }

        setError(reason instanceof Error ? reason.message : "The builder move request failed.");
      });

    return () => {
      abortController.abort();
    };
  }, [moveName]);

  const isLoading = Boolean(moveName.trim()) && !details && !error;

  if (error) {
    return (
      <article className="flex h-full flex-col border border-[var(--line)] bg-black/45 px-5 py-5">
        <p className="[font-family:var(--font-display)] text-[0.6rem] uppercase tracking-[0.28em] text-white/34">
          {moveName}
        </p>
        <p className="mt-3 text-sm leading-6 text-[var(--negative)]">{error}</p>
      </article>
    );
  }

  if (isLoading || !details) {
    return (
      <article className="flex h-full flex-col border border-[var(--line)] bg-black/45 px-5 py-5">
        <p className="[font-family:var(--font-display)] text-[0.6rem] uppercase tracking-[0.28em] text-white/34">
          {moveName}
        </p>
        <p className="mt-3 text-sm leading-6 text-white/42">Loading move details...</p>
      </article>
    );
  }

  const secondaryNotes = buildMoveDetailNotes(details);

  return (
    <article className="flex h-full flex-col border border-[var(--line)] bg-black/45 px-5 py-5">
      <div className="flex items-center justify-between gap-4">
        <p className="[font-family:var(--font-display)] text-[0.6rem] uppercase tracking-[0.28em] text-white/34">
          {details.name}
        </p>
        <p className="text-[11px] uppercase tracking-[0.18em] text-white/34">
          {formatLabel(details.type_name)} · {formatLabel(details.damage_class)}
        </p>
      </div>
      <p className="mt-5 text-sm leading-6 text-white/64">
        Power {formatMoveNumericValue(details.power)}
        {"  "}
        Accuracy {formatMovePercentage(details.accuracy)}
      </p>
      <p className="mt-1 text-sm leading-6 text-white/64">
        {details.pp} PP
        {"  "}
        Priority {details.priority > 0 ? `+${details.priority}` : details.priority}
      </p>
      <p className="mt-3 text-sm leading-7 text-[var(--fg-muted)]">{details.short_effect || "No effect text available."}</p>
      <p className="mt-3 text-sm leading-6 text-white/52">Target {formatLabel(details.target_name)}</p>
      {secondaryNotes.length ? (
        <p className="mt-auto border-t border-[var(--line)] pt-3 text-sm leading-6 text-white/52">{secondaryNotes.join(" ")}</p>
      ) : null}
    </article>
  );
}

function PreviewReasonList({
  members,
  reasons,
  rosterLookup,
}: {
  members: string[];
  reasons: Record<string, string>;
  rosterLookup: Map<string, RosterEntry>;
}) {
  if (!members.length) {
    return null;
  }

  return (
    <div className="border-t border-[var(--line)] pt-4">
      <p className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
        Why these four
      </p>
      <div className="mt-3 space-y-3">
        {members.map((memberName) => {
          const rosterMember = rosterLookup.get(memberName);
          const reason = reasons[memberName];

          return (
            <div key={`reason-${memberName}`} className="grid grid-cols-[auto_minmax(0,1fr)] gap-3 border-t border-[var(--line)] pt-3 first:border-t-0 first:pt-0">
              <PokemonSprite species={rosterMember?.species ?? memberName} label={memberName} small />
              <div>
                <p className="text-sm leading-6 text-white/82">{memberName}</p>
                <p className="text-sm leading-6 text-white/58">{reason}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MetaImpactBoard({ rows }: { rows: MetaMatchupRowData[] }) {
  const visibleRows = rows.slice(0, 8);
  const maxImpact = Math.max(...visibleRows.map((row) => Math.abs(row.impact_score)), 1);

  return (
    <div>
      <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.28em] text-white/34">
        Tournament matchup board
      </p>
      <div className="mt-3.5 space-y-4">
        {visibleRows.map((row) => {
          const width = `${(Math.abs(row.impact_score) / maxImpact) * 50}%`;
          const positive = row.impact_score >= 0;

          return (
            <div key={row.slug} className="border-t border-[var(--line)] pt-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm leading-6 text-white/82">{row.label}</p>
                  <p className="text-[0.68rem] uppercase tracking-[0.18em] text-white/34">
                    {row.meta_share.toFixed(1)}% meta pull · {row.result_label}
                  </p>
                </div>
                <span className={`text-[0.68rem] uppercase tracking-[0.18em] ${positive ? "text-[var(--positive)]" : "text-[var(--negative)]"}`}>
                  {formatLabel(row.standing)}
                </span>
              </div>
              <p className="mt-2 text-sm leading-6 text-white/54">{row.source}</p>
              {row.context_reasons.length ? (
                <div className="mt-3 space-y-1.5 text-sm leading-6 text-white/54">
                  {row.context_reasons.slice(0, 2).map((reason) => (
                    <p key={`${row.slug}-${reason}`}>
                      <span className="text-white/34">Why:</span> {reason}
                    </p>
                  ))}
                </div>
              ) : null}
              <div className="mt-3 grid gap-2 text-sm leading-6 text-white/62">
                <p>
                  <span className="text-white/38">Modes:</span> {row.modes.join(" / ")}
                </p>
                <p>
                  <span className="text-white/38">Cores:</span> {row.key_cores.join(" / ")}
                </p>
                <p>
                  <span className="text-white/38">Pokemon:</span> {row.key_pokemon.join(", ")}
                </p>
              </div>
              <div className="relative mt-3 h-px bg-[var(--line)]">
                <div className="absolute inset-y-[-6px] left-1/2 w-px bg-white/20" />
                {positive ? (
                  <div className="absolute left-1/2 top-0 h-px bg-[var(--positive)]" style={{ width }} />
                ) : (
                  <div className="absolute right-1/2 top-0 h-px bg-[var(--negative)]" style={{ width }} />
                )}
              </div>
              <div className="mt-2 flex items-center justify-between gap-4 font-mono text-[0.68rem] text-white/42">
                <span>context {row.contextual_score.toFixed(2)}</span>
                <span>matchup {row.matchup_score.toFixed(2)}</span>
                <span>popular {row.popularity_score.toFixed(1)}%</span>
                <span>results {row.result_score.toFixed(1)}%</span>
                <span>{positive ? "+" : ""}{row.impact_score.toFixed(2)} impact</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PreviewMemberStrip({
  label,
  members,
  rosterLookup,
}: {
  label: string;
  members: string[];
  rosterLookup: Map<string, RosterEntry>;
}) {
  if (!members.length) {
    return null;
  }

  return (
    <div className="border-t border-[var(--line)] pt-4">
      <p className="[font-family:var(--font-display)] text-[0.58rem] uppercase tracking-[0.28em] text-white/34">
        {label}
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {members.map((memberName) => {
          const rosterMember = rosterLookup.get(memberName);
          return (
            <div key={`${label}-${memberName}`} className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3">
              <PokemonSprite
                species={rosterMember?.species ?? memberName}
                label={memberName}
                small
              />
              <span className="text-sm leading-6 text-white/78">{memberName}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DivergingBars({
  heading,
  rows,
  positiveColor,
  negativeColor,
}: {
  heading: string;
  rows: Array<{ label: string; value: number; note?: string }>;
  positiveColor: string;
  negativeColor: string;
}) {
  const maxValue = Math.max(...rows.map((row) => Math.abs(row.value)), 1);

  return (
    <div>
      <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.28em] text-white/34">
        {heading}
      </p>
      <div className="mt-3.5 space-y-4">
        {rows.map((row) => {
          const width = `${(Math.abs(row.value) / maxValue) * 50}%`;
          const positive = row.value >= 0;
          return (
            <div key={row.label} className="grid gap-3">
              <div className="flex items-center justify-between text-sm text-white/72">
                <span>{formatLabel(row.label)}</span>
                <span className="font-mono text-xs text-white/45">{row.value.toFixed(2)}</span>
              </div>
              {row.note ? <p className="text-xs leading-5 text-white/42">{row.note}</p> : null}
              <div className="relative h-px bg-[var(--line)]">
                <div className="absolute inset-y-[-6px] left-1/2 w-px bg-white/20" />
                {positive ? (
                  <div className="absolute left-1/2 top-0 h-px" style={{ width, background: positiveColor }} />
                ) : (
                  <div className="absolute right-1/2 top-0 h-px" style={{ width, background: negativeColor }} />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BarLedger({
  heading,
  rows,
  valueFormatter,
  accentResolver,
}: {
  heading: string;
  rows: Array<{ label: string; value: number; note?: string }>;
  valueFormatter: (value: number, row: { label: string; value: number; note?: string }) => string;
  accentResolver: (label: string) => string;
}) {
  const maxValue = Math.max(...rows.map((row) => row.value), 1);

  return (
    <div>
      <p className="[font-family:var(--font-display)] text-[0.62rem] uppercase tracking-[0.28em] text-white/34">
        {heading}
      </p>
      <div className="mt-3.5 space-y-4">
        {rows.map((row) => (
          <div key={row.label} className="space-y-2.5">
            <div className="flex items-center justify-between gap-6 text-sm leading-6 text-white/72">
              <span>{formatLabel(row.label)}</span>
              <span className="text-right text-white/42">{valueFormatter(row.value, row)}</span>
            </div>
            <div className="h-px bg-[var(--line)]">
              <div
                className="h-px"
                style={{
                  width: `${(row.value / maxValue) * 100}%`,
                  background: accentResolver(row.label),
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MemberRow({ member }: { member: RosterEntry }) {
  const benchmarkSummary = summarizeBenchmarkTags(member.speed?.benchmark_tags ?? []);
  const speedContextSummary = summarizeSpeedContexts(member.speed?.speed_contexts ?? []);
  const natureEffect = getNatureEffect(member.nature);
  const natureUpLabel = natureEffect.increase ? memberStatLabel(natureEffect.increase) : null;
  const natureDownLabel = natureEffect.decrease ? memberStatLabel(natureEffect.decrease) : null;

  return (
    <article className="grid gap-6 border-t border-[var(--line)] py-6 lg:grid-cols-[92px_minmax(0,1fr)_320px] lg:items-start">
      <div className="flex justify-start lg:justify-center">
        <PokemonSprite species={member.species} label={member.displayName} />
      </div>

      <div>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="[font-family:var(--font-display)] text-[0.94rem] uppercase tracking-[0.14em] text-white">
              {member.displayName}
            </h3>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm leading-6 text-white/52">
              <span>{member.ability ? `Ability · ${member.ability}` : "No ability provided"}</span>
              {member.nature ? (
                <span>
                  Nature · <span className="text-white/74">{member.nature}</span>
                  {natureUpLabel ? <span className="text-[var(--positive)]"> +{natureUpLabel}</span> : null}
                  {natureDownLabel ? <span className="text-[var(--negative)]"> -{natureDownLabel}</span> : null}
                </span>
              ) : null}
              {member.level ? <span>Level {member.level}</span> : null}
            </div>
          </div>
          <div className="flex items-center gap-3 text-[11px] uppercase tracking-[0.18em] text-white/38">
            {member.item ? <ItemSprite item={member.item} label={member.item} /> : null}
            <span>{member.item ?? "No item listed"}</span>
          </div>
        </div>
        <p className="mt-4 text-sm leading-7 text-white/76">{member.moves.join(" / ")}</p>
        <StatBars member={member} />
      </div>

      <div className="grid gap-3 text-sm leading-6 text-white/66">
        <div>
          <p className="[font-family:var(--font-display)] text-[0.6rem] uppercase tracking-[0.28em] text-white/32">
            Roles
          </p>
          <p className="mt-2">{member.roles.length ? member.roles.map(formatLabel).join(" / ") : "No inferred roles."}</p>
        </div>
        <div>
          <p className="[font-family:var(--font-display)] text-[0.6rem] uppercase tracking-[0.28em] text-white/32">
            Speed
          </p>
          <p className="mt-2">
            {member.speed
              ? `${member.speed.battle_speed} raw speed · ${formatLabel(member.speed.tier)}`
              : "Speed unlocks after the first analysis run."}
          </p>
          {member.speed ? <p className="mt-1 text-[13px] leading-6 text-white/42">{speedContextSummary}</p> : null}
        </div>
        <div>
          <p className="[font-family:var(--font-display)] text-[0.6rem] uppercase tracking-[0.28em] text-white/32">
            Benchmarks
          </p>
          <p className="mt-2">{benchmarkSummary}</p>
        </div>
      </div>
    </article>
  );
}

function StatBars({ member }: { member: RosterEntry }) {
  const stats = member.speed?.stats;

  if (!stats) {
    return null;
  }

  const natureEffect = getNatureEffect(member.nature);
  const itemStatDeltas = resolveItemStatDeltas(member, stats);
  const visualCap = Math.max(
    MEMBER_STAT_VISUAL_CAP,
    ...MEMBER_STAT_ORDER.map(({ key }) => stats[key] + Math.max(itemStatDeltas[key] ?? 0, 0)),
  );

  return (
    <div className="mt-5">
      <p className="[font-family:var(--font-display)] text-[0.6rem] uppercase tracking-[0.28em] text-white/32">Stats</p>
      <div className="mt-3 grid gap-x-4 gap-y-3 sm:grid-cols-2">
        {MEMBER_STAT_ORDER.map(({ key, label }) => {
          const value = stats[key];
          const itemDelta = itemStatDeltas[key] ?? 0;
          const adjustedValue = value + itemDelta;
          const baseWidth = `${Math.min(value / visualCap, 1) * 100}%`;
          const adjustedWidth = `${Math.min(adjustedValue / visualCap, 1) * 100}%`;
          const color = statBarColor(value);
          const labelClass =
            key === natureEffect.increase
              ? "text-[var(--positive)]"
              : key === natureEffect.decrease
                ? "text-[var(--negative)]"
                : "text-white/52";
          const valueClass =
            key === natureEffect.increase
              ? "text-[var(--positive)]"
              : key === natureEffect.decrease
                ? "text-[var(--negative)]"
                : "text-white/78";

          return (
            <div key={key} className="space-y-1.5">
              <div className={`flex items-center justify-between gap-4 text-[11px] uppercase tracking-[0.14em] ${labelClass}`}>
                <span>{label}</span>
                <span className={valueClass}>
                  {value}
                  {itemDelta !== 0 ? (
                    <span className={itemDelta > 0 ? "text-white/86" : "text-white/58"}>
                      {` (${itemDelta > 0 ? "+" : ""}${itemDelta})`}
                    </span>
                  ) : null}
                </span>
              </div>
              <div className="relative h-px bg-[var(--line)] overflow-visible">
                <div className="absolute left-0 top-0 h-px" style={{ width: baseWidth, background: color }} />
                {itemDelta > 0 ? (
                  <div
                    className="absolute top-0 h-px bg-white/92"
                    style={{ left: baseWidth, width: `calc(${adjustedWidth} - ${baseWidth})` }}
                  />
                ) : null}
                {itemDelta < 0 ? (
                  <div
                    className="absolute top-0 h-px bg-white/45"
                    style={{ left: adjustedWidth, width: `calc(${baseWidth} - ${adjustedWidth})` }}
                  />
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BuilderStatPreview({
  member,
  stats,
  forcedItem,
}: {
  member: ParsedTeamMember;
  stats: MemberStatBlock;
  forcedItem: string | null;
}) {
  const natureEffect = getNatureEffect(member.nature);
  const effectiveItem = forcedItem ?? member.item;
  const itemStatDeltas = resolveItemStatDeltas({ species: member.species, item: effectiveItem }, stats);
  const visualCap = Math.max(
    MEMBER_STAT_VISUAL_CAP,
    ...MEMBER_STAT_ORDER.map(({ key }) => stats[key] + Math.max(itemStatDeltas[key] ?? 0, 0)),
  );

  return (
    <div className="mt-6 border-t border-[var(--line)] pt-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <p className="[font-family:var(--font-display)] text-[0.6rem] uppercase tracking-[0.28em] text-white/32">Live stats</p>
        {member.nature ? <p className="text-xs leading-5 text-white/42">{formatNatureOptionLabel(member.nature)}</p> : null}
      </div>
      <div className="mt-3 grid gap-x-4 gap-y-3 sm:grid-cols-2">
        {MEMBER_STAT_ORDER.map(({ key, label }) => {
          const value = stats[key];
          const itemDelta = itemStatDeltas[key] ?? 0;
          const adjustedValue = value + itemDelta;
          const baseWidth = `${Math.min(value / visualCap, 1) * 100}%`;
          const adjustedWidth = `${Math.min(adjustedValue / visualCap, 1) * 100}%`;
          const color = statBarColor(value);
          const labelClass =
            key === natureEffect.increase
              ? "text-[var(--positive)]"
              : key === natureEffect.decrease
                ? "text-[var(--negative)]"
                : "text-white/52";
          const valueClass =
            key === natureEffect.increase
              ? "text-[var(--positive)]"
              : key === natureEffect.decrease
                ? "text-[var(--negative)]"
                : "text-white/86";

          return (
            <div key={`builder-live-stat-${key}`} className="space-y-1.5">
              <div className={`flex items-center justify-between gap-4 text-[11px] uppercase tracking-[0.14em] ${labelClass}`}>
                <span>{label}</span>
                <span className={valueClass}>
                  {adjustedValue}
                  {itemDelta !== 0 ? (
                    <span className="text-white/48">{` (raw ${value}${itemDelta > 0 ? ` +${itemDelta}` : ` ${itemDelta}`})`}</span>
                  ) : null}
                </span>
              </div>
              <div className="relative h-px overflow-visible bg-[var(--line)]">
                <div className="absolute left-0 top-0 h-px" style={{ width: baseWidth, background: color }} />
                {itemDelta > 0 ? (
                  <div
                    className="absolute top-0 h-px bg-white/92"
                    style={{ left: baseWidth, width: `calc(${adjustedWidth} - ${baseWidth})` }}
                  />
                ) : null}
                {itemDelta < 0 ? (
                  <div
                    className="absolute top-0 h-px bg-white/45"
                    style={{ left: adjustedWidth, width: `calc(${baseWidth} - ${adjustedWidth})` }}
                  />
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PokemonSprite({ species, label, small = false }: { species: string; label: string; small?: boolean }) {
  const [failed, setFailed] = useState(false);
  const url = buildPokemonSpriteUrl(species);
  const sizeClass = small ? "h-14 w-14 sm:h-16 sm:w-16" : "h-20 w-20 lg:h-24 lg:w-24";

  if (failed) {
    return (
      <div
        className={`flex ${sizeClass} items-center justify-center border border-[var(--line)] [font-family:var(--font-display)] text-[0.68rem] uppercase tracking-[0.22em] text-white/34`}
      >
        {label.slice(0, 2)}
      </div>
    );
  }

  return (
    <Image
      src={url}
      alt={label}
      width={small ? 64 : 96}
      height={small ? 64 : 96}
      unoptimized
      onError={() => setFailed(true)}
      loading="lazy"
      sizes={small ? "64px" : "96px"}
      className={`${sizeClass} object-contain drop-shadow-[0_22px_45px_rgba(0,0,0,0.48)]`}
    />
  );
}

function BuilderSpeciesTypingBadges({
  species,
  regulationId,
  initialTypes = [],
  compact = false,
  className = "",
}: {
  species: string;
  regulationId: string;
  initialTypes?: string[];
  compact?: boolean;
  className?: string;
}) {
  const normalizedSpecies = species.trim();
  const [resolvedTypes, setResolvedTypes] = useState<string[]>([]);
  const displayTypes = initialTypes.length ? initialTypes : resolvedTypes;

  useEffect(() => {
    if (!normalizedSpecies || initialTypes.length) {
      return;
    }

    const abortController = new AbortController();

    void fetch(
      `/api/builder-species?species=${encodeURIComponent(normalizedSpecies)}&regulationId=${encodeURIComponent(regulationId)}`,
      {
        signal: abortController.signal,
      },
    )
      .then(async (response) => {
        const payload = (await response.json()) as BuilderSpeciesOptions & { message?: string };

        if (!response.ok) {
          throw new Error(payload.message ?? "The builder species request failed.");
        }

        setResolvedTypes(Array.isArray(payload.types) ? payload.types : []);
      })
      .catch(() => {
        if (abortController.signal.aborted) {
          return;
        }

        setResolvedTypes([]);
      });

    return () => {
      abortController.abort();
    };
  }, [normalizedSpecies, regulationId, initialTypes.length]);

  if (!displayTypes.length) {
    return null;
  }

  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className}`.trim()}>
      {displayTypes.map((typeName) => (
        <TypeBadge key={`${normalizedSpecies}-${typeName}-${compact ? "compact" : "full"}`} typeName={typeName} compact={compact} />
      ))}
    </div>
  );
}

function TypeBadge({ typeName, compact = false }: { typeName: string; compact?: boolean }) {
  const accent = TYPE_ACCENTS[typeName] ?? "#9bb0c7";
  const foreground = readableAccentForeground(accent);
  const label = formatLabel(typeName);

  if (compact) {
    return (
      <span className="inline-flex" title={label} aria-label={label}>
        <TypeIcon typeName={typeName} accent={accent} foreground={foreground} compact />
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border border-white/12 px-2.5 py-1 text-[0.68rem] uppercase tracking-[0.16em]"
      style={{
        backgroundColor: `${accent}22`,
        color: "rgba(255,255,255,0.86)",
      }}
    >
      <TypeIcon typeName={typeName} accent={accent} foreground={foreground} />
      <span>{label}</span>
    </span>
  );
}

function TypeIcon({
  typeName,
  accent,
  foreground,
  compact = false,
}: {
  typeName: string;
  accent: string;
  foreground: string;
  compact?: boolean;
}) {
  const iconLabel = TYPE_ICON_LABELS[typeName] ?? formatLabel(typeName).slice(0, 2).toUpperCase();
  const size = compact ? 18 : 20;
  const textSize = iconLabel.length > 1 ? (compact ? 7 : 7.5) : (compact ? 9 : 10);

  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 20 20"
      className="shrink-0"
    >
      <circle cx="10" cy="10" r="10" fill={accent} />
      <text
        x="10"
        y="10"
        fill={foreground}
        fontSize={textSize}
        fontWeight="700"
        textAnchor="middle"
        dominantBaseline="central"
        style={{ letterSpacing: iconLabel.length > 1 ? "0.02em" : "0" }}
      >
        {iconLabel}
      </text>
    </svg>
  );
}

function ItemSprite({ item, label }: { item: string; label: string }) {
  const [failed, setFailed] = useState(false);
  const url = buildItemSpriteUrl(item);

  if (failed) {
    return (
      <div className="flex h-8 w-8 items-center justify-center border border-[var(--line)] [font-family:var(--font-display)] text-[0.52rem] uppercase tracking-[0.18em] text-white/34">
        {label.slice(0, 2)}
      </div>
    );
  }

  return (
    <Image
      src={url}
      alt={label}
      width={32}
      height={32}
      unoptimized
      onError={() => setFailed(true)}
      loading="lazy"
      sizes="32px"
      className="h-8 w-8 object-contain"
    />
  );
}

function rankedRows(values: Record<string, number>, limit: number) {
  return Object.entries(values)
    .map(([label, value]) => ({ label, value }))
    .sort((left, right) => right.value - left.value || left.label.localeCompare(right.label))
    .slice(0, limit);
}

function readableAccentForeground(accent: string) {
  if (!/^#[0-9a-f]{6}$/i.test(accent)) {
    return "#ffffff";
  }

  const red = parseInt(accent.slice(1, 3), 16);
  const green = parseInt(accent.slice(3, 5), 16);
  const blue = parseInt(accent.slice(5, 7), 16);
  const luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255;
  return luminance > 0.68 ? "#0b0f16" : "#f7fbff";
}

function rankedBreakdownRows(values: Record<string, { count: number; moves?: string[]; members?: string[] }>, limit: number) {
  return Object.entries(values)
    .map(([label, details]) => ({
      label,
      value: details.count,
      note: details.moves?.length ? details.moves.join(" / ") : details.members?.join(" / ") ?? "",
    }))
    .filter((row) => row.value > 0)
    .sort((left, right) => right.value - left.value || left.label.localeCompare(right.label))
    .slice(0, limit);
}

function scoreRows(
  values: Record<string, number>,
  details?: Record<string, { reasons?: string[] }>,
) {
  return Object.entries(values)
    .map(([label, value]) => ({
      label,
      value,
      note: details?.[label]?.reasons?.[0],
    }))
    .sort((left, right) => right.value - left.value);
}

function buildRoster(parsedTeam: ParsedTeamMember[], analysis: PokemonTeamAnalysis): RosterEntry[] {
  const speedByName = new Map(analysis.speed_profile.members.map((member) => [member.pokemon, member]));

  return parsedTeam.map((member) => ({
    ...member,
    roles: analysis.member_roles[member.displayName] ?? [],
    speed: speedByName.get(member.displayName),
  }));
}

function canonicalizeAnalysisForRegulation(
  analysis: PokemonTeamAnalysis,
  regulation: RegulationCatalogEntry | undefined,
) {
  if (!regulation) {
    return analysis;
  }

  const canonicalizeMemberName = (memberName: string) => canonicalizeAnalysisMemberName(memberName, regulation);
  const memberRoles = Object.fromEntries(
    Object.entries(analysis.member_roles).map(([memberName, roles]) => [canonicalizeMemberName(memberName), roles]),
  );
  const pokemonRoleBreakdown = Object.fromEntries(
    Object.entries(analysis.pokemon_role_breakdown).map(([label, details]) => [
      label,
      details.members
        ? {
            ...details,
            members: details.members.map(canonicalizeMemberName),
          }
        : details,
    ]),
  );
  const benchmarkGroups = Object.fromEntries(
    Object.entries(analysis.speed_profile.benchmarks.groups).map(([slug, group]) => [
      slug,
      {
        ...group,
        best_member: group.best_member ? canonicalizeMemberName(group.best_member) : null,
        benchmarks: group.benchmarks.map((benchmark) => ({
          ...benchmark,
          hit_members: benchmark.hit_members.map(canonicalizeMemberName),
          tie_members: benchmark.tie_members.map(canonicalizeMemberName),
        })),
      },
    ]),
  );
  const speedDistribution = Object.fromEntries(
    Object.entries(analysis.speed_profile.distribution).map(([tier, details]) => [
      tier,
      {
        ...details,
        members: details.members.map(canonicalizeMemberName),
      },
    ]),
  );

  return {
    ...analysis,
    speed_profile: {
      ...analysis.speed_profile,
      fastest: {
        ...analysis.speed_profile.fastest,
        pokemon: canonicalizeMemberName(analysis.speed_profile.fastest.pokemon),
      },
      slowest: {
        ...analysis.speed_profile.slowest,
        pokemon: canonicalizeMemberName(analysis.speed_profile.slowest.pokemon),
      },
      base_speed_extremes: {
        fastest: {
          ...analysis.speed_profile.base_speed_extremes.fastest,
          pokemon: canonicalizeMemberName(analysis.speed_profile.base_speed_extremes.fastest.pokemon),
        },
        slowest: {
          ...analysis.speed_profile.base_speed_extremes.slowest,
          pokemon: canonicalizeMemberName(analysis.speed_profile.base_speed_extremes.slowest.pokemon),
        },
      },
      distribution: speedDistribution,
      benchmarks: {
        ...analysis.speed_profile.benchmarks,
        groups: benchmarkGroups,
      },
      members: analysis.speed_profile.members.map((member) => ({
        ...member,
        pokemon: canonicalizeMemberName(member.pokemon),
      })),
    },
    member_roles: memberRoles,
    pokemon_role_breakdown: pokemonRoleBreakdown,
    team_preview: {
      ...analysis.team_preview,
      bring_plans: analysis.team_preview.bring_plans.map((plan) => ({
        ...plan,
        leads: plan.leads.map(canonicalizeMemberName),
        back: plan.back.map(canonicalizeMemberName),
        pick_four: plan.pick_four.map(canonicalizeMemberName),
        member_reasons: Object.fromEntries(
          Object.entries(plan.member_reasons).map(([memberName, reason]) => [canonicalizeMemberName(memberName), reason]),
        ),
      })),
      watch_pokemon: analysis.team_preview.watch_pokemon.map(canonicalizeMemberName),
    },
  };
}

function canonicalizeAnalysisMemberName(memberName: string, regulation: RegulationCatalogEntry) {
  const trimmedMemberName = memberName.trim();
  if (!trimmedMemberName) {
    return memberName;
  }

  return resolveRegulationSpeciesAlias(trimmedMemberName, regulation) ?? trimmedMemberName;
}

function canonicalizeParsedTeamForRegulation(
  parsedTeam: ParsedTeamMember[],
  regulation: RegulationCatalogEntry | undefined,
) {
  return parsedTeam.map((member) => canonicalizeParsedMemberForRegulation(member, regulation));
}

function canonicalizeParsedMemberForRegulation(
  member: ParsedTeamMember,
  regulation: RegulationCatalogEntry | undefined,
): ParsedTeamMember {
  const canonicalSpecies = resolveRegulationMemberSpecies(member, regulation);
  if (!canonicalSpecies || canonicalSpecies === member.species.trim()) {
    return member;
  }

  const usesSpeciesAsDisplayName = !member.displayName.trim() || member.displayName.trim() === member.species.trim();
  return {
    ...member,
    species: canonicalSpecies,
    displayName: usesSpeciesAsDisplayName ? canonicalSpecies : member.displayName,
  };
}

function resolveRegulationMemberSpecies(
  member: ParsedTeamMember,
  regulation: RegulationCatalogEntry | undefined,
) {
  const species = member.species.trim();
  if (!species || !regulation) {
    return species;
  }

  const resolvedSpecies = resolveRegulationSpeciesAlias(species, regulation) ?? species;
  return resolveMegaSpeciesFromItem(resolvedSpecies, member.item, regulation) ?? resolvedSpecies;
}

function resolveRegulationSpeciesAlias(
  speciesName: string,
  regulation: RegulationCatalogEntry,
) {
  const lookup = buildRegulationSpeciesLookup(regulation);
  return lookup.get(normalizeAssetId(speciesName)) ?? null;
}

function buildRegulationSpeciesLookup(regulation: RegulationCatalogEntry) {
  const lookup = new Map<string, string>();
  const officialSpecies = [
    ...(regulation.eligible_species ?? []),
    ...(regulation.allowed_mega_evolutions ?? []),
  ];

  for (const officialName of officialSpecies) {
    appendSpeciesAlias(lookup, officialName, officialName);

    const megaMatch = officialName.match(/^Mega\s+(.+?)(?:\s+([XY]))?$/i);
    if (megaMatch) {
      const baseName = megaMatch[1].trim();
      const suffix = megaMatch[2]?.toUpperCase();
      appendSpeciesAlias(lookup, `${baseName}-Mega${suffix ? `-${suffix}` : ""}`, officialName);
      appendSpeciesAlias(lookup, `${baseName} Mega${suffix ? ` ${suffix}` : ""}`, officialName);
      continue;
    }

    const genderMatch = officialName.match(/^(.*)\s+\((Male|Female)\)$/i);
    if (genderMatch) {
      const baseName = genderMatch[1].trim();
      const shortGender = genderMatch[2].toLowerCase() === "male" ? "M" : "F";
      appendSpeciesAlias(lookup, `${baseName} (${shortGender})`, officialName);
      appendSpeciesAlias(lookup, `${baseName}-${shortGender.toLowerCase()}`, officialName);
      appendSpeciesAlias(lookup, `${baseName}-${genderMatch[2].toLowerCase()}`, officialName);
      continue;
    }

    const regionalMatch = officialName.match(/^(.*)\s+\((Alolan|Galarian|Hisuian) Form\)$/i);
    if (regionalMatch) {
      const baseName = regionalMatch[1].trim();
      const regionName = regionalMatch[2].toLowerCase();
      const shortRegion =
        regionName === "alolan" ? "alola" : regionName === "galarian" ? "galar" : "hisui";
      appendSpeciesAlias(lookup, `${regionName} ${baseName}`, officialName);
      appendSpeciesAlias(lookup, `${baseName} ${regionName}`, officialName);
      appendSpeciesAlias(lookup, `${baseName}-${regionName}`, officialName);
      appendSpeciesAlias(lookup, `${shortRegion} ${baseName}`, officialName);
      appendSpeciesAlias(lookup, `${baseName} ${shortRegion}`, officialName);
      appendSpeciesAlias(lookup, `${baseName}-${shortRegion}`, officialName);
    }
  }

  return lookup;
}

function appendSpeciesAlias(lookup: Map<string, string>, alias: string, officialName: string) {
  const aliasKey = normalizeAssetId(alias);
  if (!aliasKey || lookup.has(aliasKey)) {
    return;
  }

  lookup.set(aliasKey, officialName);
}

function resolveMegaSpeciesFromItem(
  speciesName: string,
  itemName: string | null | undefined,
  regulation: RegulationCatalogEntry,
) {
  const normalizedItem = normalizeAssetId(itemName ?? "");
  if (!normalizedItem) {
    return null;
  }

  const requiredItems = regulation.required_items_by_mega_species ?? {};
  for (const [megaSpecies, requiredItem] of Object.entries(requiredItems)) {
    if (normalizeAssetId(requiredItem) !== normalizedItem) {
      continue;
    }

    const baseSpecies = megaBaseSpeciesName(megaSpecies);
    if (!baseSpecies) {
      continue;
    }

    const normalizedSpecies = normalizeAssetId(speciesName);
    if (normalizedSpecies === normalizeAssetId(megaSpecies) || normalizedSpecies === normalizeAssetId(baseSpecies)) {
      return megaSpecies;
    }
  }

  return null;
}

function megaBaseSpeciesName(megaSpecies: string) {
  const match = megaSpecies.trim().match(/^Mega\s+(.+?)(?:\s+[XY])?$/i);
  return match ? match[1].trim() : null;
}

function normalizeBuilderMembers(parsedTeam: ParsedTeamMember[]) {
  const members = parsedTeam.slice(0, BUILDER_TEAM_SIZE).map((member) => normalizeBuilderMember(member));

  while (members.length < BUILDER_TEAM_SIZE) {
    members.push(createEmptyTeamMember());
  }

  return members;
}

function normalizeBuilderMember(member: ParsedTeamMember): ParsedTeamMember {
  const species = member.species.trim();
  const displayName = member.displayName.trim() || species;

  return {
    displayName,
    species,
    item: cleanOptionalText(member.item),
    ability: cleanDisplayText(member.ability),
    level:
      typeof member.level === "number" && Number.isFinite(member.level)
        ? clampNumber(member.level, 1, 100)
        : 50,
    nature: cleanDisplayText(member.nature),
    moves: Array.from({ length: BUILDER_MOVE_COUNT }, (_, index) => formatBuilderOptionValue(member.moves[index])),
    evs: sanitizeEvs(member.evs),
  };
}

function createEmptyTeamMember(): ParsedTeamMember {
  return {
    displayName: "",
    species: "",
    item: null,
    ability: null,
    level: 50,
    nature: null,
    moves: Array.from({ length: BUILDER_MOVE_COUNT }, () => ""),
    evs: {},
  };
}

function sanitizeEvs(evs: Partial<Record<EffortValueStat, number>> | undefined) {
  const nextEvs: Partial<Record<EffortValueStat, number>> = {};

  for (const { key } of MEMBER_STAT_ORDER) {
    const evKey = key as EffortValueStat;
    const value = evs?.[evKey];
    if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
      continue;
    }

    nextEvs[evKey] = clampNumber(value, 0, 252);
  }

  return nextEvs;
}

function cleanOptionalText(value: string | null | undefined) {
  const cleanedValue = value?.trim() ?? "";
  return cleanedValue || null;
}

function cleanDisplayText(value: string | null | undefined) {
  const cleanedValue = cleanOptionalText(value);
  return cleanedValue ? formatBuilderOptionValue(cleanedValue) : null;
}

function countFilledMoves(moves: string[]) {
  return moves.filter((move) => move.trim()).length;
}

function totalEffortValues(evs: Partial<Record<EffortValueStat, number>>) {
  return Object.values(evs).reduce((total, value) => total + (value ?? 0), 0);
}

function clampNumber(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, Math.floor(value)));
}

function buildLiveMemberStats(member: ParsedTeamMember, baseStats: MemberStatBlock): MemberStatBlock {
  return {
    hp: normalizedHpStat(baseStats.hp, member.evs.hp ?? 0),
    attack: normalizedNonHpStat(baseStats.attack, member.evs.attack ?? 0, natureMultiplier(member.nature, "attack")),
    defense: normalizedNonHpStat(baseStats.defense, member.evs.defense ?? 0, natureMultiplier(member.nature, "defense")),
    special_attack: normalizedNonHpStat(
      baseStats.special_attack,
      member.evs.special_attack ?? 0,
      natureMultiplier(member.nature, "special_attack"),
    ),
    special_defense: normalizedNonHpStat(
      baseStats.special_defense,
      member.evs.special_defense ?? 0,
      natureMultiplier(member.nature, "special_defense"),
    ),
    speed: normalizedNonHpStat(baseStats.speed, member.evs.speed ?? 0, natureMultiplier(member.nature, "speed")),
  };
}

function normalizedHpStat(baseStat: number, effortValue: number) {
  const baseComponent = ((2 * baseStat + CHAMPIONS_FIXED_IV) * CHAMPIONS_LEVEL) / 100;
  return Math.floor(baseComponent) + CHAMPIONS_LEVEL + 10 + effortValue;
}

function normalizedNonHpStat(baseStat: number, effortValue: number, appliedNatureMultiplier: number) {
  const baseComponent = ((2 * baseStat + CHAMPIONS_FIXED_IV) * CHAMPIONS_LEVEL) / 100;
  return Math.floor((Math.floor(baseComponent) + 5) * appliedNatureMultiplier) + effortValue;
}

function natureMultiplier(nature: string | null, stat: BattleStatKey) {
  const natureEffect = getNatureEffect(nature);
  if (natureEffect.increase === stat) {
    return 1.1;
  }
  if (natureEffect.decrease === stat) {
    return 0.9;
  }
  return 1;
}

function summarizeBenchmarkTags(tags: BenchmarkTag[]) {
  if (tags.length === 0) {
    return "No benchmark ties or hits yet.";
  }

  return tags
    .map((tag) => `${tag.benchmark_label} (${formatLabel(tag.status)})`)
    .join(" / ");
}

function summarizeSpeedContexts(contexts: SpeedContext[]) {
  if (contexts.length === 0) {
    return "No additional item or ability speed contexts inferred.";
  }

  return contexts
    .slice(0, 3)
    .map((context) => `${context.label} ${context.speed}`)
    .join(" / ");
}

function statBarColor(value: number) {
  let color: string = MEMBER_STAT_COLOR_STOPS[0].color;

  for (const stop of MEMBER_STAT_COLOR_STOPS) {
    if (value < stop.minimum) {
      break;
    }
    color = stop.color;
  }

  return color;
}

function getNatureEffect(nature: string | null) {
  return NATURE_EFFECTS[normalizeAssetId(nature ?? "")] ?? {};
}

function formatNatureOptionLabel(nature: string) {
  const normalizedNature = normalizeAssetId(nature);
  const title = normalizedNature ? normalizedNature.charAt(0).toUpperCase() + normalizedNature.slice(1) : nature;
  const effect = NATURE_EFFECTS[normalizedNature];

  if (!effect?.increase || !effect?.decrease) {
    return title;
  }

  return `${title} (+${NATURE_STAT_LABELS[effect.increase]} / -${NATURE_STAT_LABELS[effect.decrease]})`;
}

function resolveRequiredMegaItem(
  speciesName: string,
  regulation: RegulationCatalogEntry | undefined,
  fallbackItem: string | null = null,
) {
  const trimmedSpeciesName = speciesName.trim();
  if (!trimmedSpeciesName) {
    return fallbackItem;
  }

  return regulation?.required_items_by_mega_species?.[trimmedSpeciesName] ?? fallbackItem;
}

function memberStatLabel(stat: keyof MemberStatBlock) {
  return MEMBER_STAT_ORDER.find((row) => row.key === stat)?.label ?? formatLabel(stat);
}

function resolveItemStatDeltas(member: Pick<RosterEntry, "item" | "species">, stats: MemberStatBlock) {
  const deltas: Partial<Record<keyof MemberStatBlock, number>> = {};

  for (const modifier of getItemStatModifiers(member)) {
    const baseValue = stats[modifier.stat];
    const adjustedValue = Math.floor((baseValue * modifier.numerator) / modifier.denominator);
    const delta = adjustedValue - baseValue;

    if (delta !== 0) {
      deltas[modifier.stat] = delta;
    }
  }

  return deltas;
}

function getItemStatModifiers(member: Pick<RosterEntry, "item" | "species">): ItemStatModifier[] {
  const itemId = normalizeAssetId(member.item ?? "");
  const speciesId = normalizeAssetId(member.species);

  switch (itemId) {
    case "choice-band":
      return [{ stat: "attack", numerator: 3, denominator: 2 }];
    case "choice-specs":
      return [{ stat: "special_attack", numerator: 3, denominator: 2 }];
    case "choice-scarf":
      return [{ stat: "speed", numerator: 3, denominator: 2 }];
    case "assault-vest":
      return [{ stat: "special_defense", numerator: 3, denominator: 2 }];
    case "eviolite":
      return [
        { stat: "defense", numerator: 3, denominator: 2 },
        { stat: "special_defense", numerator: 3, denominator: 2 },
      ];
    case "deep-sea-tooth":
      return speciesId === "clamperl" ? [{ stat: "special_attack", numerator: 2, denominator: 1 }] : [];
    case "deep-sea-scale":
      return speciesId === "clamperl" ? [{ stat: "special_defense", numerator: 2, denominator: 1 }] : [];
    case "light-ball":
      return speciesId === "pikachu"
        ? [
            { stat: "attack", numerator: 2, denominator: 1 },
            { stat: "special_attack", numerator: 2, denominator: 1 },
          ]
        : [];
    case "thick-club":
      return ["cubone", "marowak", "marowak-alola"].includes(speciesId)
        ? [{ stat: "attack", numerator: 2, denominator: 1 }]
        : [];
    case "metal-powder":
      return speciesId === "ditto"
        ? [
            { stat: "defense", numerator: 2, denominator: 1 },
            { stat: "special_defense", numerator: 2, denominator: 1 },
          ]
        : [];
    case "quick-powder":
      return speciesId === "ditto" ? [{ stat: "speed", numerator: 2, denominator: 1 }] : [];
    case "iron-ball":
    case "macho-brace":
    case "power-anklet":
    case "power-band":
    case "power-belt":
    case "power-bracer":
    case "power-lens":
    case "power-weight":
      return [{ stat: "speed", numerator: 1, denominator: 2 }];
    default:
      return [];
  }
}

function buildItemSpriteUrl(itemName: string) {
  return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/${normalizeAssetId(itemName)}.png`;
}

function formatMoveNumericValue(value: number | null) {
  return value === null ? "—" : String(value);
}

function formatMovePercentage(value: number | null) {
  return value === null ? "—" : `${value}%`;
}

function buildMoveDetailNotes(details: BuilderMoveDetails) {
  const notes: string[] = [];

  if (details.effect_chance !== null) {
    notes.push(`${details.effect_chance}% overall effect chance.`);
  }

  if (details.ailment_name && details.ailment_name !== "none") {
    notes.push(
      `Can inflict ${formatLabel(details.ailment_name)}${details.ailment_chance > 0 ? ` (${details.ailment_chance}%)` : ""}.`,
    );
  }

  if (details.flinch_chance > 0) {
    notes.push(`${details.flinch_chance}% flinch chance.`);
  }

  if (details.healing > 0) {
    notes.push(`Restores ${details.healing}% HP.`);
  }

  if (details.stat_changes.length) {
    const statChanges = details.stat_changes
      .map(({ stat_name, change }) => `${change > 0 ? "+" : ""}${change} ${formatLabel(stat_name)}`)
      .join(" / ");

    notes.push(
      details.stat_chance > 0
        ? `${details.stat_chance}% chance to apply ${statChanges}.`
        : `Applies ${statChanges}.`,
    );
  }

  return notes;
}

function describeCoverageGap(
  typeName: string,
  gap:
    | PokemonTeamAnalysis["target_coverage"][string]
    | undefined,
) {
  if (!gap) {
    return `${formatLabel(typeName)} · No recorded attacking lines.`;
  }

  const neutralLines = Math.max(gap.neutral_or_better_lines - gap.super_effective_lines, 0);

  return `${formatLabel(typeName)} · Best hit is ${describeBestMultiplier(gap.best_multiplier)}. ${gap.super_effective_lines} super-effective line${gap.super_effective_lines === 1 ? "" : "s"}; ${neutralLines} neutral line${neutralLines === 1 ? "" : "s"}; ${gap.resisted_lines} resisted; ${gap.immune_lines} immune.`;
}

function describeBestMultiplier(multiplier: number) {
  if (multiplier <= 0) {
    return "blocked by immunity (0x)";
  }
  if (multiplier < 1) {
    return `resisted (${multiplier.toFixed(1)}x)`;
  }
  if (multiplier === 1) {
    return "neutral (1.0x)";
  }

  return `super-effective (${multiplier.toFixed(1)}x)`;
}

function normalizeAssetId(value: string) {
  return value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[♀]/g, "f")
    .replace(/[♂]/g, "m")
    .replace(/[’'.:%]/g, "")
    .replace(/[()/_\s]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}
