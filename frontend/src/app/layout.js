import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "LocalPulse AI — Merchant Growth Platform",
  description: "AI-powered hyper-local demand forecasting, inventory optimization, and collaborative merchant bundling for Indian MSMEs.",
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
        </AuthProvider>
      </body>
    </html>
  );
}
