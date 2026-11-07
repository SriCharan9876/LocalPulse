import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import GeminiRateLimitModal from "@/components/ui/GeminiRateLimitModal";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "LocalPulse AI — Hyperlocal MSME Demand Intelligence, Copilot & Growth Engine",
  description: "Autonomous retail operations for Indian neighborhood stores: weekday-aware forecasting, 18-tool Indic voice copilot, 6-factor collaboration bundles with 12% margin protection, and live spatial radar.",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[#edece4] text-[#16181a] font-sans selection:bg-[#16181a] selection:text-[#e0fd53]">
        <AuthProvider>
          {children}
          <GeminiRateLimitModal />
        </AuthProvider>
      </body>
    </html>
  );
}
