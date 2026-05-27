import { auth } from "@/auth";
import { AnalyzerWorkspace } from "@/components/analyzer-workspace";
import fallbackSampleAnalysis from "@/lib/fallback-sample-analysis.json";
import fallbackRegulationCatalog from "@/lib/fallback-regulation-catalog.json";
import { isAuthConfigured, isGoogleAuthConfigured } from "@/lib/auth/runtime";
import { getFeaturedExampleTeams } from "@/lib/example-teams";
import { getRegulationCatalog, runPokemonAnalyzer } from "@/lib/python-analyzer";
import { listSavedTeamsForUser } from "@/lib/saved-teams";
import type {
  AuthCapabilitySummary,
  AuthSessionUser,
  PokemonTeamAnalysis,
  RegulationCatalogPayload,
  SavedTeamRecord,
} from "@/lib/types";

export const dynamic = "force-dynamic";

const USE_BUNDLED_DEV_SNAPSHOT = process.env.NODE_ENV !== "production";

export default async function Home() {
  let regulationCatalog = fallbackRegulationCatalog as unknown as RegulationCatalogPayload;
  const initialLoadIssues: string[] = [];

  if (USE_BUNDLED_DEV_SNAPSHOT) {
    initialLoadIssues.push(
      "Development mode is using the bundled Regulation M-A snapshot to keep the Next.js dev server responsive. Run the analyzer after editing the team to fetch live results.",
    );
  } else {
    try {
      regulationCatalog = await getRegulationCatalog();
    } catch {
      initialLoadIssues.push(
        "The Next.js app could not reach the analyzer API for the regulation catalog. Showing the bundled Regulation M-A snapshot instead.",
      );
    }
  }

  const exampleTeams = await getFeaturedExampleTeams();
  const initialRegulationId = regulationCatalog.default_regulation_id;
  const initialExample =
    exampleTeams.find((example) => example.regulationId === initialRegulationId) ?? exampleTeams[0];

  let initialAnalysis = fallbackSampleAnalysis as unknown as PokemonTeamAnalysis;
  if (!USE_BUNDLED_DEV_SNAPSHOT) {
    const initialResult = await runPokemonAnalyzer(initialExample.teamText, initialExample.regulationId);
    if (initialResult.ok) {
      initialAnalysis = initialResult.analysis;
    } else {
      initialLoadIssues.push(initialResult.message);
    }
  }

  const initialAnalysisError = initialLoadIssues.length ? initialLoadIssues.join(" ") : null;

  const authCapabilities: AuthCapabilitySummary = {
    nativeAuthEnabled: isAuthConfigured(),
    googleAuthEnabled: isGoogleAuthConfigured(),
  };
  let initialSessionUser: AuthSessionUser | null = null;
  let initialSavedTeams: SavedTeamRecord[] = [];

  if (authCapabilities.nativeAuthEnabled) {
    const session = await auth();
    if (session?.user?.id) {
      initialSessionUser = {
        id: session.user.id,
        username: session.user.username ?? null,
        name: session.user.name ?? null,
        email: session.user.email ?? null,
        image: session.user.image ?? null,
      };
      initialSavedTeams = await listSavedTeamsForUser(session.user.id);
    }
  }

  return (
    <AnalyzerWorkspace
      initialAnalysis={initialAnalysis}
      initialAnalysisError={initialAnalysisError}
      initialTeamText={initialExample.teamText}
      initialSessionUser={initialSessionUser}
      initialSavedTeams={initialSavedTeams}
      regulationOptions={regulationCatalog.regulations}
      authCapabilities={authCapabilities}
    />
  );
}
