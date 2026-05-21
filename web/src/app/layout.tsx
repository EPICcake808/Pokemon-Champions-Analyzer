import type { Metadata } from "next";
import { Chakra_Petch, JetBrains_Mono, Manrope, Michroma } from "next/font/google";
import "./globals.css";

const bodyFont = Manrope({
  variable: "--font-body",
  subsets: ["latin"],
});

const displayFont = Michroma({
  variable: "--font-display",
  subsets: ["latin"],
  weight: "400",
});

const titleFont = Chakra_Petch({
  variable: "--font-title",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const monoFont = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Pokemon Champions Analyzer",
  description: "A Next.js control room for the deterministic Pokemon Champions team analyzer.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${bodyFont.variable} ${displayFont.variable} ${titleFont.variable} ${monoFont.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[var(--bg)] text-[var(--fg)]">{children}</body>
    </html>
  );
}
