import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";
import { AppProvider } from "@/context/AppContext";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Lexaro | Legal Help. Simplified. Localized.",
  description:
    "Legal Help. Simplified. Localized. AI legal assistant for India in 22 Indian languages.",
  keywords: ["legal assistant", "India", "AI", "multilingual", "voice", "BNS", "IPC", "Lexaro"],
  openGraph: {
    title: "Lexaro | Legal Help. Simplified. Localized.",
    description: "Legal Help. Simplified. Localized. AI legal assistant for India.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <body className={`${inter.variable} ${playfair.variable} font-sans antialiased`}>
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
