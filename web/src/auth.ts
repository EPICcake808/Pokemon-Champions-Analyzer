import NextAuth from "next-auth";
import { DrizzleAdapter } from "@auth/drizzle-adapter";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";

import { db } from "@/db";
import { accounts, sessions, users, verificationTokens } from "@/db/schema";
import { verifyPassword } from "@/lib/auth/password";
import { getAuthSecret, isGoogleAuthConfigured } from "@/lib/auth/runtime";
import { ensureUserHasUsername, findUserById, findUserByIdentifier, toAuthProviderUser } from "@/lib/auth/users";

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: DrizzleAdapter(db, {
    usersTable: users,
    accountsTable: accounts,
    sessionsTable: sessions,
    verificationTokensTable: verificationTokens,
  }),
  pages: {
    signIn: "/",
  },
  providers: [
    ...(isGoogleAuthConfigured()
      ? [
          Google({
            allowDangerousEmailAccountLinking: true,
            profile(profile) {
              const email = typeof profile.email === "string" ? profile.email.toLowerCase() : null;
              const name = typeof profile.name === "string" && profile.name.trim() ? profile.name : email?.split("@")[0] ?? null;
              const image = typeof profile.picture === "string" ? profile.picture : null;

              return {
                id: profile.sub,
                name,
                email,
                image,
              };
            },
          }),
        ]
      : []),
    Credentials({
      name: "Credentials",
      credentials: {
        identifier: {
          label: "Username or email",
          type: "text",
        },
        password: {
          label: "Password",
          type: "password",
        },
      },
      async authorize(credentials) {
        const identifier = typeof credentials?.identifier === "string" ? credentials.identifier : "";
        const password = typeof credentials?.password === "string" ? credentials.password : "";

        if (!identifier.trim() || !password) {
          return null;
        }

        const user = await findUserByIdentifier(identifier);
        if (!user?.passwordHash) {
          return null;
        }

        const passwordMatches = await verifyPassword(password, user.passwordHash);
        if (!passwordMatches) {
          return null;
        }

        return toAuthProviderUser(user);
      },
    }),
  ],
  secret: getAuthSecret(),
  session: {
    strategy: "jwt",
  },
  trustHost: true,
  events: {
    async createUser({ user }) {
      await ensureUserHasUsername(user.id ?? "", [user.name, user.email]);
    },
  },
  callbacks: {
    async signIn({ account, profile }) {
      if (account?.provider !== "google") {
        return true;
      }

      if (!profile || typeof profile !== "object" || !("email_verified" in profile)) {
        return false;
      }

      return Boolean((profile as { email_verified?: unknown }).email_verified);
    },
    async jwt({ token, user }) {
      const userId = user?.id ?? token.sub;
      if (!userId) {
        return token;
      }

      const currentUser = await findUserById(userId);
      if (!currentUser) {
        return token;
      }

      token.sub = currentUser.id;
      token.name = currentUser.name ?? currentUser.username ?? token.name;
      token.email = currentUser.email ?? token.email;
      token.picture = currentUser.image ?? token.picture;
      token.username = currentUser.username ?? null;
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.sub ?? session.user.id;
        session.user.username = typeof token.username === "string" ? token.username : null;
      }

      return session;
    },
  },
});
