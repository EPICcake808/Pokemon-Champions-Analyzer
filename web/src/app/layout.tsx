import type { Metadata, Viewport } from "next";
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

// Pin the layout viewport to the device width so mobile renders at 1x instead of
// falling back to a ~980px desktop viewport (which made the site render zoomed-out
// with dark borders and broke touch navigation).
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
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
