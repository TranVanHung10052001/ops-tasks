import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import TopBar from "@/components/layout/top-bar";
import ChannelSidebar from "@/components/layout/channel-sidebar";
import AIPanel from "@/components/layout/ai-panel";

export const metadata: Metadata = {
  title: "Ops Center · Ahamove Truck Ops",
  description: "Hệ thống điều phối nhóm vận hành xe tải Ahamove",
};

const themeInit = `
try {
  var t = localStorage.getItem('ops-theme');
  if (t === 'sang') document.documentElement.setAttribute('data-theme','sang');
} catch(e) {}
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="min-h-screen">
        <TopBar />
        <Suspense fallback={<aside className="w-[220px] bg-surface-deep border-r border-divider fixed left-0 top-10 bottom-0" />}>
          <ChannelSidebar />
        </Suspense>
        <main className="ml-[220px] mr-0 xl:mr-[320px] mt-10 min-h-[calc(100vh-40px)]">
          {children}
        </main>
        <AIPanel />
      </body>
    </html>
  );
}
