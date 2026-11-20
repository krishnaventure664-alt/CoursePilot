import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "https://coursepilot.vercel.app";

export const viewport: Viewport = {
  themeColor: "#09090b",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  metadataBase: new URL(baseUrl),
  title: {
    default: "CoursePilot - Turn YouTube Courses into Interactive Study Workspaces",
    template: "%s | CoursePilot",
  },
  description:
    "AI-powered university study workspace. Synthesize verified lecture notes, formulate practice quizzes, create spaced repetition flashcards, and ask questions with exact timestamp video citations.",
  keywords: [
    "CoursePilot",
    "YouTube Study Workspace",
    "AI Lecture Notes",
    "Timestamp Q&A",
    "Spaced Repetition Flashcards",
    "Practice Quizzes",
    "Video Transcription",
    "Online Course Revision",
  ],
  authors: [{ name: "CoursePilot Team" }],
  creator: "CoursePilot",
  publisher: "CoursePilot",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: baseUrl,
    title: "CoursePilot - Turn YouTube Courses into Interactive Study Workspaces",
    description:
      "Transform long YouTube video playlists into interactive notes, practice quizzes, flashcards, and verified timestamp citations.",
    siteName: "CoursePilot",
  },
  twitter: {
    card: "summary_large_image",
    title: "CoursePilot - Turn YouTube Courses into Interactive Study Workspaces",
    description:
      "Transform long YouTube video playlists into interactive notes, practice quizzes, flashcards, and verified timestamp citations.",
  },
  alternates: {
    canonical: baseUrl,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html
        lang="en"
        suppressHydrationWarning
        className="h-full antialiased font-sans"
      >
        <body suppressHydrationWarning className="min-h-full flex flex-col font-sans">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
