/**
 * AEQUITAS — Root layout
 *
 * In Next.js App Router, layout.tsx wraps every page.
 * This root layout sets the HTML shell, fonts, and global styles.
 * It renders once and persists across page navigations.
 */
import type { Metadata } from "next";
import { Inter } from "next/font/google";
// @ts-expect-error: global CSS import for Next.js App Router
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AEQUITAS",
  description: "Agentic Equity & Quantitative Intelligence Trading Analysis System",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-gray-100 antialiased`}>
        {children}
      </body>
    </html>
  );
}
