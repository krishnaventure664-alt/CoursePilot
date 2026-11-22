// frontend/app/admin/page.tsx
"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { UserButton, useUser, useAuth } from "@clerk/nextjs";

function getAdminApiUrl(): string {
  if (typeof window !== "undefined") {
    try {
      const params = new URLSearchParams(window.location.search);
      const serverParam = params.get("server");
      if (serverParam && (serverParam.startsWith("http://") || serverParam.startsWith("https://"))) {
        return serverParam.trim().replace(/\/+$/, "");
      }
    } catch {}
    const saved = localStorage.getItem("coursepilot_api_url");
    if (saved && (saved.startsWith("http://") || saved.startsWith("https://"))) {
      return saved.trim().replace(/\/+$/, "");
    }
  }
  return (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").trim().replace(/\/+$/, "");
}

type FeedbackItem = {
  id: number;
  user_id: string;
  user_email: string;
  feedback_type: string;
  rating: number;
  message: string;
  context: Record<string, any>;
  created_at: number;
};

type AdminMetrics = {
  total_users: number;
  total_courses_indexed: number;
  study_notes_synthesized: number;
  quizzes_formulated: number;
  flashcards_generated: number;
  questions_answered: number;
  total_feedback_submissions?: number;
  positive_feedback_count?: number;
  user_satisfaction_percentage?: number;
};

export default function AdminPage() {
  const { user, isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const API_URL = getAdminApiUrl();

  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);

  // Authenticated API Fetch
  const authFetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const token = await getToken();
    const headers = new Headers(init?.headers || {});
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    headers.set("ngrok-skip-browser-warning", "true");
    return fetch(input, { ...init, headers });
  };

  // Determine admin authorization
  const isAdmin = useMemo(() => {
    if (!user) return false;
    const userEmail = user.primaryEmailAddress?.emailAddress?.toLowerCase() || "";
    const adminEmailsEnv = (process.env.NEXT_PUBLIC_ADMIN_EMAILS || "krishnaventure664@gmail.com")
      .toLowerCase()
      .split(",")
      .map((e) => e.trim());
    return adminEmailsEnv.includes(userEmail) || userEmail === "krishnaventure664@gmail.com";
  }, [user]);

  // Load feedback & platform metrics
  const loadData = async () => {
    setLoading(true);
    try {
      const [fbRes, mRes] = await Promise.all([
        authFetch(`${API_URL}/admin/feedback`),
        authFetch(`${API_URL}/admin/metrics`),
      ]);

      if (fbRes.ok) {
        const fbData = await fbRes.json();
        setFeedback(fbData.feedback || []);
      }
      if (mRes.ok) {
        const mData = await mRes.json();
        setMetrics(mData);
      }
    } catch (err) {
      console.error("Failed to load admin data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isLoaded && isSignedIn && isAdmin) {
      void loadData();
    } else if (isLoaded) {
      setLoading(false);
    }
  }, [isLoaded, isSignedIn, isAdmin]);

  // Filter feedback items
  const filteredFeedback = useMemo(() => {
    return feedback.filter((item) => {
      const matchesType =
        selectedType === "all" ||
        (selectedType === "bug" && item.feedback_type === "bug") ||
        (selectedType === "feature" && item.feedback_type === "feature") ||
        (selectedType === "general" && item.feedback_type === "general") ||
        (selectedType === "rating" && item.feedback_type === "answer_rating");

      const query = searchQuery.toLowerCase().trim();
      if (!query) return matchesType;

      const emailMatch = item.user_email?.toLowerCase().includes(query);
      const messageMatch = item.message?.toLowerCase().includes(query);
      const courseMatch = item.context?.course_title?.toLowerCase().includes(query);
      const questionMatch = item.context?.question?.toLowerCase().includes(query);

      return matchesType && (emailMatch || messageMatch || courseMatch || questionMatch);
    });
  }, [feedback, selectedType, searchQuery]);

  // KPI Calculations
  const stats = useMemo(() => {
    const total = feedback.length;
    const bugs = feedback.filter((f) => f.feedback_type === "bug").length;
    const features = feedback.filter((f) => f.feedback_type === "feature").length;
    const general = feedback.filter((f) => f.feedback_type === "general").length;
    const ratings = feedback.filter((f) => f.rating > 0);
    const avgRating = ratings.length > 0 ? (ratings.reduce((acc, f) => acc + f.rating, 0) / ratings.length).toFixed(1) : "5.0";

    return { total, bugs, features, general, avgRating };
  }, [feedback]);

  // Export CSV
  const handleExportCSV = () => {
    if (feedback.length === 0) return;
    const headers = ["ID", "Date", "Student Email", "Type", "Rating", "Message", "Context"];
    const rows = feedback.map((item) => [
      item.id,
      new Date(item.created_at * 1000).toISOString(),
      `"${item.user_email || "Anonymous"}"`,
      `"${item.feedback_type}"`,
      item.rating,
      `"${(item.message || "").replace(/"/g, '""')}"`,
      `"${JSON.stringify(item.context || {}).replace(/"/g, '""')}"`,
    ]);

    const csvContent = "\uFEFF" + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `coursepilot_feedback_${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyEmail = (email: string) => {
    if (!email) return;
    void navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
  };

  // Loading State
  if (!isLoaded || loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-white dark:bg-zinc-950">
        <div className="flex flex-col items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-white"></div>
          <span className="text-xs text-zinc-500">Loading Admin Dashboard...</span>
        </div>
      </div>
    );
  }

  // Unauthorized State
  if (!isSignedIn || !isAdmin) {
    return (
      <div className="flex min-h-screen w-screen items-center justify-center bg-zinc-50 p-4 dark:bg-zinc-950">
        <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-8 text-center shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h2 className="mt-4 text-base font-bold text-zinc-900 dark:text-white">
            Access Restricted
          </h2>
          <p className="mt-2 text-xs text-zinc-500">
            This dashboard is reserved for CoursePilot platform administrators. Your signed-in email ({user?.primaryEmailAddress?.emailAddress || "Guest"}) does not have administrative privileges.
          </p>
          <div className="mt-6 flex flex-col gap-2">
            <Link
              href="/"
              className="inline-flex justify-center rounded-lg bg-zinc-900 px-4 py-2 text-xs font-semibold text-white hover:bg-zinc-800 dark:bg-white dark:text-zinc-900"
            >
              Return to Workspace
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Admin Dashboard View
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 antialiased dark:bg-zinc-950 dark:text-zinc-100">
      {/* Top Header */}
      <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/80 backdrop-blur-md dark:border-zinc-800 dark:bg-zinc-900/80">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-zinc-900 text-xs font-bold text-white dark:bg-white dark:text-zinc-900">
                CP
              </div>
              <span className="text-sm font-semibold tracking-tight">CoursePilot</span>
            </Link>
            <span className="text-zinc-300 dark:text-zinc-700">/</span>
            <span className="rounded bg-zinc-100 px-2 py-0.5 text-[11px] font-semibold text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
              Admin &amp; Feedback
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="flex items-center gap-1.5 rounded-md border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-100 dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-800"
            >
              <span>←</span>
              <span>Workspace</span>
            </Link>
            <UserButton />
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {/* Page Title & Actions */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-2xl">
              User Feedback &amp; Quality Oversight
            </h1>
            <p className="mt-1 text-xs text-zinc-500">
              Live feedback submissions, feature requests, and lecture ratings from authenticated users.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => void loadData()}
              className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs font-medium text-zinc-700 shadow-xs hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
              title="Refresh feedback submissions"
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
            <button
              onClick={handleExportCSV}
              disabled={feedback.length === 0}
              className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-zinc-900 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-zinc-800 disabled:opacity-50 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Export CSV
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
          <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Total Feedback</span>
            <div className="mt-2 text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">{stats.total}</div>
            <span className="mt-1 block text-[11px] text-zinc-500">Student submissions</span>
          </div>

          <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Avg Satisfaction</span>
            <div className="mt-2 text-2xl font-bold tracking-tight text-emerald-600 dark:text-emerald-400">
              {stats.avgRating} <span className="text-sm font-normal text-zinc-400">/ 5.0</span>
            </div>
            <span className="mt-1 block text-[11px] text-zinc-500">Based on user ratings</span>
          </div>

          <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Bug Reports</span>
            <div className="mt-2 text-2xl font-bold tracking-tight text-red-500">{stats.bugs}</div>
            <span className="mt-1 block text-[11px] text-zinc-500">Issue submissions</span>
          </div>

          <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Feature Ideas</span>
            <div className="mt-2 text-2xl font-bold tracking-tight text-purple-600 dark:text-purple-400">{stats.features}</div>
            <span className="mt-1 block text-[11px] text-zinc-500">Product requests</span>
          </div>

          <div className="col-span-2 sm:col-span-4 lg:col-span-1 rounded-xl border border-zinc-200 bg-white p-4 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Active Students</span>
            <div className="mt-2 text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">
              {metrics?.total_users ?? 1}
            </div>
            <span className="mt-1 block text-[11px] text-zinc-500">Verified users</span>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-zinc-200 bg-zinc-100 p-0.5 text-xs font-medium dark:border-zinc-800 dark:bg-zinc-900">
            {[
              { id: "all", label: "All" },
              { id: "general", label: "General" },
              { id: "bug", label: "Bugs" },
              { id: "feature", label: "Feature Ideas" },
              { id: "rating", label: "Answer Ratings" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedType(tab.id)}
                className={`cursor-pointer rounded-md px-3 py-1.5 transition-all ${
                  selectedType === tab.id
                    ? "bg-white font-semibold text-zinc-900 shadow-xs dark:bg-zinc-800 dark:text-white"
                    : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-72">
            <input
              type="text"
              placeholder="Search by student, message, course..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs outline-none focus:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900"
            />
          </div>
        </div>

        {/* Feedback Feed */}
        <div className="mt-4 space-y-3">
          {filteredFeedback.length === 0 ? (
            <div className="rounded-xl border border-zinc-200 bg-white p-12 text-center text-zinc-400 dark:border-zinc-800 dark:bg-zinc-900">
              <svg className="mx-auto h-8 w-8 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p className="mt-3 text-xs font-medium">No feedback matching this filter.</p>
            </div>
          ) : (
            filteredFeedback.map((item) => {
              const formattedDate = new Date(item.created_at * 1000).toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              });

              const isBug = item.feedback_type === "bug";
              const isFeature = item.feedback_type === "feature";
              const isAnswerRating = item.feedback_type === "answer_rating";

              return (
                <div
                  key={item.id}
                  className="rounded-xl border border-zinc-200 bg-white p-5 shadow-xs transition-colors hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-700"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-2">
                      {/* Category Badge */}
                      <span
                        className={`rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                          isBug
                            ? "bg-red-50 text-red-700 dark:bg-red-950/50 dark:text-red-300"
                            : isFeature
                            ? "bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300"
                            : isAnswerRating
                            ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
                            : "bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300"
                        }`}
                      >
                        {isBug ? "Bug Report" : isFeature ? "Feature Request" : isAnswerRating ? "Answer Rating" : "General Feedback"}
                      </span>

                      {/* Rating Stars or Value */}
                      {item.rating > 0 ? (
                        <div className="flex items-center text-amber-500 text-xs">
                          {"★".repeat(Math.min(item.rating, 5))}
                          <span className="ml-1 text-[11px] font-medium text-zinc-500">
                            ({item.rating}/5)
                          </span>
                        </div>
                      ) : item.rating === -1 ? (
                        <span className="rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-800 dark:bg-red-950/60 dark:text-red-300">
                          Needs Work
                        </span>
                      ) : null}
                    </div>

                    <div className="flex items-center gap-3 text-xs text-zinc-400">
                      <span>{formattedDate}</span>
                    </div>
                  </div>

                  {/* Feedback Message */}
                  <div className="mt-3 text-xs leading-relaxed text-zinc-800 dark:text-zinc-200">
                    <p className="font-medium">{item.message || "(No written text provided)"}</p>
                  </div>

                  {/* Student Details & Context */}
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-zinc-100 pt-3 text-[11px] dark:border-zinc-800">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-zinc-500">From:</span>
                      <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                        {item.user_email || "Anonymous Student"}
                      </span>
                      {item.user_email && (
                        <button
                          onClick={() => copyEmail(item.user_email)}
                          className="cursor-pointer text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                          title="Copy email to reply"
                        >
                          {copiedEmail === item.user_email ? (
                            <span className="text-emerald-600 font-semibold">Copied!</span>
                          ) : (
                            <span>Copy</span>
                          )}
                        </button>
                      )}
                    </div>

                    {item.context && Object.keys(item.context).length > 0 && (
                      <div className="flex items-center gap-1.5 text-zinc-400">
                        {item.context.course_title && (
                          <span className="truncate max-w-xs" title={item.context.course_title}>
                            Course: {item.context.course_title}
                          </span>
                        )}
                        {item.context.tab && (
                          <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                            Tab: {item.context.tab}
                          </span>
                        )}
                        {item.context.question && (
                          <span className="truncate max-w-xs italic" title={item.context.question}>
                            &quot;{item.context.question}&quot;
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </main>
    </div>
  );
}
