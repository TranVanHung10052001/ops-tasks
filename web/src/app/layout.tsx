import type { Metadata } from "next";
import "./globals.css";
import TopBar from "@/components/layout/top-bar";
import ChannelSidebar from "@/components/layout/channel-sidebar";
import AIPanel from "@/components/layout/ai-panel";

export const metadata: Metadata = {
  title: "Đài Điều Vận · Ahamove Truck Ops",
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
    <html lang="vi">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="min-h-screen">
        <TopBar />
        <ChannelSidebar />
        <main className="ml-[220px] mr-[320px] mt-10 min-h-[calc(100vh-40px)]">
          {children}
        </main>
        <AIPanel />
      </body>
    </html>
  );
}
