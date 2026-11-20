import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen w-full flex-col justify-between bg-zinc-50 dark:bg-zinc-950">
      {/* Top Navigation */}
      <header className="flex h-16 w-full items-center justify-between border-b border-zinc-200/80 px-6 sm:px-12 dark:border-zinc-800/80">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-zinc-900 text-xs font-bold text-white dark:bg-white dark:text-zinc-900">
            CP
          </div>
          <span className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-white">
            CoursePilot
          </span>
        </div>
        <span className="text-xs text-zinc-500">
          Academic Study Assistant
        </span>
      </header>

      {/* Main Side-by-Side Area */}
      <main className="mx-auto flex w-full max-w-6xl flex-1 items-center px-6 py-12 lg:py-16">
        <div className="grid w-full items-center gap-12 lg:grid-cols-12 lg:gap-16">
          {/* Left Column: What is CoursePilot */}
          <div className="flex flex-col lg:col-span-7">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
              Overview
            </span>

            <h1 className="mt-3 text-3xl font-bold tracking-tight text-zinc-900 sm:text-4xl lg:text-5xl dark:text-white leading-[1.15]">
              What is CoursePilot?
            </h1>

            <p className="mt-4 text-sm leading-relaxed text-zinc-600 sm:text-base dark:text-zinc-400">
              CoursePilot is an academic study assistant designed for university video courses and playlists. It indexes video transcripts to generate structured study materials, test your retention, and answer questions with verifiable citations.
            </p>

            {/* Core Capabilities */}
            <div className="mt-8 space-y-4">
              <div className="flex items-start gap-3.5">
                <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-zinc-200/70 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                  <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-zinc-900 dark:text-white">Structured Study Notes</h3>
                  <p className="text-xs text-zinc-500 leading-relaxed">Generates detailed lecture notes, concept flows, and complete course handbooks formatted for focused revision.</p>
                </div>
              </div>

              <div className="flex items-start gap-3.5">
                <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-zinc-200/70 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                  <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-zinc-900 dark:text-white">Timestamp-Cited Q&A</h3>
                  <p className="text-xs text-zinc-500 leading-relaxed">Ask questions about any lecture and receive answers with clickable timestamps to review the exact moment in the video.</p>
                </div>
              </div>

              <div className="flex items-start gap-3.5">
                <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-zinc-200/70 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                  <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 11l3 3L22 4" />
                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-zinc-900 dark:text-white">Practice Quizzes & Flashcards</h3>
                  <p className="text-xs text-zinc-500 leading-relaxed">Reinforce comprehension with multiple-choice quizzes and spaced-repetition flashcards drawn directly from course topics.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Sign Up Form */}
          <div className="flex justify-center lg:col-span-5 lg:justify-end">
            <div className="w-full max-w-sm rounded-2xl border border-zinc-200 bg-white p-2 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <SignUp
                appearance={{
                  elements: {
                    rootBox: "w-full",
                    card: "shadow-none border-none bg-transparent p-4 sm:p-6",
                    headerTitle: "text-zinc-900 dark:text-white font-bold text-lg",
                    headerSubtitle: "text-zinc-500 text-xs",
                    socialButtonsBlockButton:
                      "border-zinc-200 text-xs font-medium text-zinc-800 transition hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-800",
                    formButtonPrimary:
                      "bg-zinc-900 text-xs font-medium text-white shadow-xs transition hover:bg-zinc-800 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-100",
                    footerActionLink:
                      "text-xs font-medium text-zinc-900 hover:underline dark:text-white",
                    formFieldInput:
                      "border-zinc-200 bg-transparent text-xs text-zinc-900 dark:border-zinc-700 dark:text-white",
                    formFieldLabel:
                      "text-xs font-medium text-zinc-700 dark:text-zinc-300",
                    dividerLine: "bg-zinc-200 dark:bg-zinc-800",
                    dividerText: "text-xs text-zinc-400 font-normal",
                  },
                }}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-200/80 py-4 px-6 sm:px-12 text-xs text-zinc-400 dark:border-zinc-800/80 flex items-center justify-between">
        <span>CoursePilot</span>
        <span>Strictly Grounded in Course Transcripts</span>
      </footer>
    </div>
  );
}
