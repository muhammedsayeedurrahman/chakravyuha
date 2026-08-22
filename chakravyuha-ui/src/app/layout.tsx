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
  title: "Chakravyuha | Civic and Legal Action Assistant",
  description:
    "Plain-language, source-aware civic and legal pathways for citizens in India.",
  keywords: ["civic assistant", "legal assistant", "India", "RTI", "government schemes", "CPGRAMS", "multilingual"],
  openGraph: {
    title: "Chakravyuha | Civic and Legal Action Assistant",
    description: "Understand an issue, prepare an action, and see the next practical step.",
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
