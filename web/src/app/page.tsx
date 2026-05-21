import { auth } from "@/auth";
import { AnalyzerWorkspace } from "@/components/analyzer-workspace";
import { isAuthConfigured, isGoogleAuthConfigured } from "@/lib/auth/runtime";
import { getFeaturedExampleTeams } from "@/lib/example-teams";
import { getRegulationCatalog, runPokemonAnalyzer } from "@/lib/python-analyzer";
import { listSavedTeamsForUser } from "@/lib/saved-teams";
import type { AuthCapabilitySummary, AuthSessionUser, SavedTeamRecord } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function Home() {
  const regulationCatalog = await getRegulationCatalog();
  const exampleTeams = await getFeaturedExampleTeams();
  const initialRegulationId = regulationCatalog.default_regulation_id;
  const initialExample =
    exampleTeams.find((example) => example.regulationId === initialRegulationId) ?? exampleTeams[0];
  const initialResult = await runPokemonAnalyzer(initialExample.teamText, initialExample.regulationId);

  if (!initialResult.ok) {
    throw new Error(initialResult.message);
  }

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
      initialAnalysis={initialResult.analysis}
      initialTeamText={initialExample.teamText}
      initialSessionUser={initialSessionUser}
      initialSavedTeams={initialSavedTeams}
      regulationOptions={regulationCatalog.regulations}
      authCapabilities={authCapabilities}
    />
  );
}
