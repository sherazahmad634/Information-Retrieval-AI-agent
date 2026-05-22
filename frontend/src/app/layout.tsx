import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IR-Agent — Information Retrieval AI Agent",
  description:
    "Tool-using AI agent for grounded question answering over your own document corpus.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
