import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "ADGM Compliance Copilot",
  description: "AI-powered ADGM regulatory compliance platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex flex-col overflow-hidden min-w-0">
          {children}
        </main>
      </body>
    </html>
  );
}
