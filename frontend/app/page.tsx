// frontend/app/page.tsx

"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { UserButton, useUser, useAuth } from "@clerk/nextjs";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Course = {
  id: number;
  url: string;
  title: string;
  status: string;
};

type Video = {
  video_id: string;
  title: string;
  position: number;
  status: string;
  has_notes?: number | boolean;
};

function isValidNoteContent(content: string | null | undefined): boolean {
  if (!content) return false;
  const trimmed = content.trim();
  if (trimmed.length < 50) return false;
  if (trimmed === "No notes available." || trimmed === "Failed to load notes.") return false;
  if (
    trimmed.includes("Failed to generate notes") ||
    trimmed.includes("No lecture content found") ||
    trimmed.includes("Failed to compile course handbook")
  ) {
    return false;
  }
  return true;
}

type CourseProgress = {
  course_id: number;
  status: string;
  completed: number;
  total: number;
  percentage: number;
  current_video?: string | null;
};

type Source = {
  video_id: string;
  start: number;
  end: number;
  text: string;
  rerank_score: number;
  depth_score?: number;
  duration_label?: string;
};

type AnswerResult = {
  question: string;
  course_id: number;
  answer: string;
  sources: Source[];
};

type QuizQuestion = {
  id: number;
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
};

type Flashcard = {
  id: number;
  front: string;
  back: string;
  category: string;
  status: string;
};

/* -------------------------------------------------------------
   NOTION-STYLE CLEAN DOCUMENT RENDERER
------------------------------------------------------------- */
function NotionDocumentViewer({ content }: { content: string }) {
  if (!content) return null;

  const lines = content.split("\n");
  const renderedElements: React.ReactNode[] = [];
  let tableRows: string[][] = [];
  let inTable = false;

  function flushTable(key: number) {
    if (tableRows.length === 0) return null;
    const header = tableRows[0];
    const body = tableRows.slice(1);
    tableRows = [];
    inTable = false;

    return (
      <div key={`tbl-${key}`} className="my-5 overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900">
            <tr>
              {header.map((col, idx) => (
                <th key={idx} className="px-4 py-2.5 font-semibold text-zinc-900 dark:text-zinc-100">
                  {col.replace(/\*\*/g, "").trim()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {body.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/50">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="px-4 py-2.5 text-zinc-700 dark:text-zinc-300">
                    {cell.replace(/\*\*/g, "").trim()}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  function formatInline(text: string) {
    const clean = text.replace(/\$/g, "").replace(/\\text\{([^}]+)\}/g, "$1");
    const parts = clean.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, idx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={idx} className="font-semibold text-zinc-900 dark:text-zinc-100">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  }

  lines.forEach((rawLine, index) => {
    const line = rawLine.trim();

    if (line.startsWith("|") && line.endsWith("|")) {
      if (line.includes("---")) return;
      const cols = line
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim());
      tableRows.push(cols);
      inTable = true;
      return;
    } else if (inTable) {
      renderedElements.push(flushTable(index));
    }

    if (!line) {
      renderedElements.push(<div key={index} className="h-3" />);
      return;
    }

    if (line.startsWith("# ")) {
      renderedElements.push(
        <h1 key={index} className="mt-9 mb-4 text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">
          {formatInline(line.replace("# ", ""))}
        </h1>
      );
      return;
    }

    if (line.startsWith("## ")) {
      renderedElements.push(
        <h2 key={index} className="mt-8 mb-3.5 border-b border-zinc-200 pb-2.5 text-lg font-bold tracking-tight text-zinc-900 dark:border-zinc-800 dark:text-white">
          {formatInline(line.replace("## ", ""))}
        </h2>
      );
      return;
    }

    if (line.startsWith("### ")) {
      renderedElements.push(
        <h3 key={index} className="mt-6 mb-2.5 text-[14px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
          {formatInline(line.replace("### ", ""))}
        </h3>
      );
      return;
    }

    if (line.startsWith("* ") || line.startsWith("- ")) {
      renderedElements.push(
        <div key={index} className="my-2 flex items-start gap-2.5 text-[15px] leading-relaxed text-zinc-800 dark:text-zinc-200">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
          <span>{formatInline(line.slice(2))}</span>
        </div>
      );
      return;
    }

    if (line.includes("→")) {
      renderedElements.push(
        <div key={index} className="my-3.5 rounded-xl border border-blue-100 bg-blue-50/50 px-4 py-3 text-[14.5px] font-medium leading-relaxed text-blue-950 dark:border-blue-900/40 dark:bg-blue-950/20 dark:text-blue-200">
          {formatInline(line)}
        </div>
      );
      return;
    }

    renderedElements.push(
      <p key={index} className="my-2 text-[15px] leading-relaxed text-zinc-800 dark:text-zinc-200">
        {formatInline(line)}
      </p>
    );
  });

  if (inTable) {
    renderedElements.push(flushTable(999999));
  }

  return <div className="space-y-1.5 text-zinc-800 dark:text-zinc-200">{renderedElements}</div>;
}


function LectureProcessingCard({
  video,
  videos,
  onSelectVideo,
}: {
  video: Video;
  videos: Video[];
  onSelectVideo: (vid: string) => void;
}) {
  const completedVideos = videos.filter((v: Video) => v.status === "completed");
  return (
    <div className="rounded-xl border border-amber-200/70 bg-amber-50/40 p-8 text-center dark:border-amber-900/40 dark:bg-amber-950/20">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 text-amber-600 dark:bg-amber-900/40 dark:text-amber-400">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-amber-600 border-t-transparent dark:border-amber-400" />
      </div>
      <h3 className="mt-4 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        {video.status === "processing" ? "Transcribing & Indexing Lecture..." : "Lecture Queued for Processing"}
      </h3>
      <p className="mx-auto mt-1 max-w-md text-xs text-zinc-500 dark:text-zinc-400">
        This marathon lecture has no pre-existing YouTube subtitles and is being transcribed locally using GPU Whisper. Notes, quizzes, and flashcards will unlock automatically as soon as indexing finishes.
      </p>
      {completedVideos.length > 0 && (
        <div className="mt-5 border-t border-amber-200/50 pt-4 dark:border-amber-900/30">
          <p className="text-[11px] font-medium text-zinc-500">
            Available ready lecture{completedVideos.length > 1 ? "s" : ""}:
          </p>
          <div className="mt-2 flex flex-wrap justify-center gap-2">
            {completedVideos.map((cv) => (
              <button
                key={cv.video_id}
                onClick={() => onSelectVideo(cv.video_id)}
                className="flex cursor-pointer items-center rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 transition hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
              >
                <span className="mr-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                <span>Lecture {cv.position}: {cv.title.length > 40 ? cv.title.slice(0, 40) + "..." : cv.title}</span>
              </button>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}


export default function Home() {
  const router = useRouter();
  const { user, isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.replace("/sign-in");
    }
  }, [isLoaded, isSignedIn, router]);

  const authFetch = useMemo(() => {
    return async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      let token: string | null = null;
      try {
        token = await getToken();
      } catch {
        // Fallback for offline or local dev
      }
      const headers = new Headers(init?.headers || {});
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      return fetch(input, { ...init, headers });
    };
  }, [getToken]);
  const [notesDepth, setNotesDepth] = useState<"quick" | "deep">("quick");

  // Client-side instant memory caches (0ms tab and video switching)
  const notesMemoryCache = useMemo(() => new Map<string, string>(), []);
  const quizMemoryCache = useMemo(() => new Map<string, { quiz: QuizQuestion[]; setInfo: any }>(), []);
  const cardsMemoryCache = useMemo(() => new Map<string, { flashcards: Flashcard[]; setInfo: any }>(), []);
  const answerMemoryCache = useMemo(() => new Map<string, AnswerResult>(), []);
  const [courses, setCourses] = useState<(Course & { videos: Video[] })[]>([]);
  const [activeCourse, setActiveCourse] = useState<Course | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [selectedVideoId, setSelectedVideoId] = useState<string>("");

  function handleSelectVideo(vid: string) {
    setNotesMode("single");
    setSelectedVideoId(vid);
    if (activeTab === "notes") void loadNotes(vid);
    if (activeTab === "quiz") void loadQuiz(vid);
    if (activeTab === "flashcards") void loadFlashcards(vid);
    prefetchStudyTools(vid);
  }
  const [videoSearch, setVideoSearch] = useState("");

  const [activeTab, setActiveTab] = useState<"notes" | "ask" | "quiz" | "flashcards">("notes");

  // Live Background Progress
  const [progress, setProgress] = useState<CourseProgress | null>(null);

  // Modal & Loading States
  const [showAddModal, setShowAddModal] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  // Admin Check
  const isAdmin = useMemo(() => {
    if (!user) return false;
    const userEmail = user.primaryEmailAddress?.emailAddress?.toLowerCase() || "";
    const adminEmailsEnv = (process.env.NEXT_PUBLIC_ADMIN_EMAILS || "krishnaventure664@gmail.com")
      .toLowerCase()
      .split(",")
      .map((e) => e.trim());
    return adminEmailsEnv.includes(userEmail) || userEmail === "krishnaventure664@gmail.com";
  }, [user]);


  // User Feedback State
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackType, setFeedbackType] = useState<"general" | "bug" | "feature">("general");
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackToast, setFeedbackToast] = useState(false);
  const [answerFeedbackGiven, setAnswerFeedbackGiven] = useState<"up" | "down" | null>(null);


  const [newPlaylistUrl, setNewPlaylistUrl] = useState("");
  const [courseLoading, setCourseLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Master Course Notes State (All Notes At Once)
  const [notesMode, setNotesMode] = useState<"single" | "all">("single");

  // Q&A State
  const [question, setQuestion] = useState("");
  const [answerResult, setAnswerResult] = useState<AnswerResult | null>(null);
  const [answerLoading, setAnswerLoading] = useState(false);

  // Notes State
  const [notes, setNotes] = useState<string>("");
  const [notesLoading, setNotesLoading] = useState(false);
  const [copyToast, setCopyToast] = useState(false);

  // Quiz State
  const [quiz, setQuiz] = useState<QuizQuestion[]>([]);
  const [quizLoading, setQuizLoading] = useState(false);
  const [userAnswers, setUserAnswers] = useState<Record<number, number>>({});
  const [showQuizResults, setShowQuizResults] = useState(false);
  const [quizSetInfo, setQuizSetInfo] = useState<{
    set_index: number;
    total_sets: number;
    all_covered: boolean;
    message: string;
  } | null>(null);

  // Flashcards State
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [cardsLoading, setCardsLoading] = useState(false);
  const [flippedCardId, setFlippedCardId] = useState<number | null>(null);
  const [cardsSetInfo, setCardsSetInfo] = useState<{
    set_index: number;
    total_sets: number;
    all_covered: boolean;
    message: string;
  } | null>(null);

  // Stable state refs to eliminate polling closures and interval tearing
  const activeCourseRef = useRef(activeCourse);
  activeCourseRef.current = activeCourse;
  const selectedVideoIdRef = useRef(selectedVideoId);
  selectedVideoIdRef.current = selectedVideoId;
  const notesRef = useRef(notes);
  notesRef.current = notes;
  const notesDepthRef = useRef(notesDepth);
  notesDepthRef.current = notesDepth;
  const activeTabRef = useRef(activeTab);
  activeTabRef.current = activeTab;
  const notesModeRef = useRef(notesMode);
  notesModeRef.current = notesMode;
  const quizRef = useRef(quiz);
  quizRef.current = quiz;
  const flashcardsRef = useRef(flashcards);
  flashcardsRef.current = flashcards;
  const wasIndexingRef = useRef(false);

  const [error, setError] = useState("");
  const [isBackendConnecting, setIsBackendConnecting] = useState(true);

  // 1. Initial Load with Auto-Retry
  useEffect(() => {
    let isMounted = true;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    async function loadSavedCourses(attemptsLeft = 25) {
      try {
        const userParam = user?.id ? `?user_id=${encodeURIComponent(user.id)}` : "";
        const response = await authFetch(`${API_URL}/courses${userParam}`);
        if (!response.ok) throw new Error("Backend starting");
        const data = await response.json();
        if (!isMounted) return;

        setIsBackendConnecting(false);
        const saved = data.courses ?? [];
        setCourses(saved);

        if (saved.length > 0) {
          const first = saved[0];
          setActiveCourse({
            id: first.id,
            url: first.url,
            title: first.title,
            status: first.status,
          });
          const vList = first.videos ?? [];
          setVideos(vList);
          if (vList.length > 0) {
            const preferred = vList.find((v: Video) => v.status === "completed") || vList[0];
            setSelectedVideoId(preferred.video_id);
            setNotesMode("single");
            void loadNotes(preferred.video_id, first.id);
          }
        }
      } catch (err) {
        if (!isMounted) return;
        if (attemptsLeft > 0) {
          setIsBackendConnecting(true);
          retryTimer = setTimeout(() => {
            void loadSavedCourses(attemptsLeft - 1);
          }, 600);
        } else {
          setIsBackendConnecting(false);
          console.error("Failed to connect to backend:", err);
        }
      }
    }

    void loadSavedCourses();

    return () => {
      isMounted = false;
      if (retryTimer) clearTimeout(retryTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  // 2. Real-time background indexing progress polling (Auto-refreshes UI seamlessly with Zero-F5 requirement)
  useEffect(() => {
    const courseId = activeCourse?.id;
    if (!courseId) return;

    let isMounted = true;
    let timerId: ReturnType<typeof setTimeout> | null = null;
    wasIndexingRef.current = activeCourse.status === "indexing";

    async function checkProgress() {
      if (!isMounted) return;
      const currentCourseId = activeCourseRef.current?.id;
      if (!currentCourseId) return;

      try {
        const res = await authFetch(`${API_URL}/courses/${currentCourseId}/progress`);
        if (!res.ok || !isMounted) {
          if (isMounted) timerId = setTimeout(checkProgress, 3000);
          return;
        }
        const data: CourseProgress = await res.json();
        if (!isMounted) return;
        setProgress(data);

        const userParam = user?.id ? `?user_id=${encodeURIComponent(user.id)}` : "";

        if (data.status === "indexing") {
          wasIndexingRef.current = true;
          // Refresh sidebar video statuses so green checkmarks & notes appear progressively
          const courseRes = await authFetch(`${API_URL}/courses${userParam}`);
          if (!courseRes.ok || !isMounted) {
            if (isMounted) timerId = setTimeout(checkProgress, 2500);
            return;
          }
          const courseData = await courseRes.json();
          if (!isMounted) return;

          const allCourses = ((courseData.courses ?? []) as (Course & { videos: Video[] })[]);
          const current = allCourses.find((c) => c.id === currentCourseId);
          if (current?.videos) {
            setVideos(current.videos);

            // Progressive auto-loader: as soon as the active lecture completes or has notes, render them immediately!
            const curVidId = selectedVideoIdRef.current;
            const currentVid = current.videos.find((v: Video) => v.video_id === curVidId);
            const isVidReady = Boolean(currentVid && (currentVid.status === "completed" || currentVid.has_notes));

            if (currentVid && isVidReady && !isValidNoteContent(notesRef.current)) {
              void loadNotes(currentVid.video_id, currentCourseId, notesDepthRef.current, true);
            }
            if (currentVid && isVidReady && activeTabRef.current === "quiz" && quizRef.current.length === 0) {
              void loadQuiz(currentVid.video_id, true);
            }
            if (currentVid && isVidReady && activeTabRef.current === "flashcards" && flashcardsRef.current.length === 0) {
              void loadFlashcards(currentVid.video_id, true);
            }
            if (currentVid && isVidReady) {
              prefetchStudyTools(currentVid.video_id, currentCourseId);
            }
          }

          if (isMounted) {
            timerId = setTimeout(checkProgress, 2500);
          }
        } else {
          // Course has finished indexing (or was already completed)
          const needsRefresh =
            wasIndexingRef.current ||
            activeCourseRef.current?.status === "indexing" ||
            !isValidNoteContent(notesRef.current);

          if (needsRefresh) {
            wasIndexingRef.current = false;
            const courseRes = await authFetch(`${API_URL}/courses${userParam}`);
            if (!courseRes.ok || !isMounted) return;
            const courseData = await courseRes.json();
            if (!isMounted) return;

            const allCourses = (courseData.courses ?? []) as (Course & { videos: Video[] })[];
            setCourses(allCourses);

            const updatedCurrent = allCourses.find((c) => c.id === currentCourseId);
            if (updatedCurrent) {
              setActiveCourse(updatedCurrent);
              const updatedVideos = updatedCurrent.videos ?? [];
              setVideos(updatedVideos);

              const targetVidId =
                selectedVideoIdRef.current && selectedVideoIdRef.current !== "ALL"
                  ? selectedVideoIdRef.current
                  : (updatedVideos[0]?.video_id || "");

              if (!selectedVideoIdRef.current && targetVidId) {
                setSelectedVideoId(targetVidId);
              }

              if (targetVidId) {
                if (notesModeRef.current === "all") {
                  void loadAllNotes(updatedCurrent.id, notesDepthRef.current);
                } else {
                  void loadNotes(targetVidId, updatedCurrent.id, notesDepthRef.current, true);
                }
                if (activeTabRef.current === "quiz" && quizRef.current.length === 0) {
                  void loadQuiz(targetVidId, true);
                }
                if (activeTabRef.current === "flashcards" && flashcardsRef.current.length === 0) {
                  void loadFlashcards(targetVidId, true);
                }
                prefetchStudyTools(targetVidId, updatedCurrent.id);
              }
            }
          }
        }
      } catch (e) {
        console.error("Progress polling error:", e);
        if (isMounted) timerId = setTimeout(checkProgress, 4000);
      }
    }

    void checkProgress();

    return () => {
      isMounted = false;
      if (timerId) {
        clearTimeout(timerId);
      }
    };
  }, [activeCourse?.id, user?.id]);

  // 3. Fast Add Course (< 1 second response)
  async function handleAddCourse(e: React.FormEvent) {
    e.preventDefault();
    const url = newPlaylistUrl.trim();
    if (!url) return;

    setCourseLoading(true);
    setError("");

    try {
      const res = await authFetch(`${API_URL}/courses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, user_id: user?.id || "default" }),
      });
      const data = await res.json();
      if (!res.ok || !data.course?.id) {
        throw new Error(data.message || "Failed to process course.");
      }

      setActiveCourse(data.course);
      const vList = data.videos ?? [];
      setVideos(vList);
      if (vList.length > 0) {
        const preferred = vList.find((v: Video) => v.status === "completed") || vList[0];
        setSelectedVideoId(preferred.video_id);
        setNotesMode("single");
        if (data.course.status === "completed" || preferred.status === "completed") {
          void loadNotes(preferred.video_id, data.course.id, notesDepth, true);
        }
      }
      setShowAddModal(false);
      setNewPlaylistUrl("");

      const userParam = user?.id ? `?user_id=${encodeURIComponent(user.id)}` : "";
      const listRes = await authFetch(`${API_URL}/courses${userParam}`);
      const listData = await listRes.json();
      setCourses(listData.courses ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error adding course.");
    } finally {
      setCourseLoading(false);
    }
  }


  // Feedback & Metrics Handlers
  async function handleSubmitFeedback(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!feedbackMessage.trim() && feedbackRating === 0) return;
    try {
      setFeedbackLoading(true);
      await authFetch(`${API_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedback_type: feedbackType,
          rating: feedbackRating,
          message: feedbackMessage,
          context: {
            course_id: activeCourse?.id,
            course_title: activeCourse?.title,
            tab: activeTab,
          },
          user_email: user?.primaryEmailAddress?.emailAddress || "",
        }),
      });
      setFeedbackToast(true);
      setFeedbackMessage("");
      setTimeout(() => {
        setFeedbackToast(false);
        setShowFeedbackModal(false);
      }, 1500);
    } catch (err) {
      console.error("Error submitting feedback:", err);
    } finally {
      setFeedbackLoading(false);
    }
  }

  async function handleQuickAnswerFeedback(rating: 1 | -1) {
    if (!answerResult || answerFeedbackGiven) return;
    try {
      setAnswerFeedbackGiven(rating === 1 ? "up" : "down");
      await authFetch(`${API_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedback_type: "answer_rating",
          rating: rating,
          message: rating === 1 ? "Helpful answer" : "Inaccurate or unhelpful answer",
          context: {
            question: answerResult.question,
            course_id: activeCourse?.id,
            sources_count: answerResult.sources?.length || 0,
          },
          user_email: user?.primaryEmailAddress?.emailAddress || "",
        }),
      });
    } catch (err) {
      console.error("Error submitting answer feedback:", err);
    }
  }


  // 4. Delete Course & Free Storage
  async function handleDeleteCourse(courseId: number) {
    const courseToDelete = courses.find((c) => c.id === courseId);
    const confirmed = window.confirm(
      `Are you sure you want to delete "${courseToDelete?.title || "this course"}"?\n\nThis will permanently delete all video transcripts, notes, quizzes, flashcards, vector embeddings, and free up storage.`
    );
    if (!confirmed) return;

    setDeleteLoading(true);
    try {
      const res = await authFetch(`${API_URL}/courses/${courseId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete course.");

      const updatedCourses = courses.filter((c) => c.id !== courseId);
      setCourses(updatedCourses);

      if (updatedCourses.length > 0) {
        const nextCourse = updatedCourses[0];
        setActiveCourse(nextCourse);
        const vList = nextCourse.videos ?? [];
        setVideos(vList);
        if (vList.length > 0) {
          const preferred = vList.find((v: Video) => v.status === "completed") || vList[0];
          setSelectedVideoId(preferred.video_id);
          setNotesMode("single");
          void loadNotes(preferred.video_id, nextCourse.id);
        } else {
          setSelectedVideoId("");
          setNotes("");
        }
      } else {
        setActiveCourse(null);
        setVideos([]);
        setSelectedVideoId("");
        setNotes("");
        setQuiz([]);
        setFlashcards([]);
        setAnswerResult(null);
    setAnswerFeedbackGiven(null);
        setProgress(null);
      }
    } catch (err) {
      console.error("Delete course error:", err);
      alert("Failed to delete course.");
    } finally {
      setDeleteLoading(false);
    }
  }

  // 4b. Resume / Retry Indexing
  async function handleResumeIndexing() {
    if (!activeCourse) return;
    try {
      await authFetch(`${API_URL}/courses/${activeCourse.id}/resume`, { method: "POST" });
    } catch (err) {
      console.error("Failed to resume indexing:", err);
    }
  }

  // 5. Ask Question (Instant 0ms memory cache + Fast GPU retrieval)
  async function handleAskQuestion(e: React.FormEvent) {
    e.preventDefault();
    const cleanQ = question.trim();
    if (!activeCourse || !cleanQ) return;

    // Normalizing punctuation (?, !, .) enables 0ms cache hits across phrasing variations
    const normKey = `${activeCourse.id}_${cleanQ.toLowerCase().replace(/[?!.,;:]+$/, "").replace(/\s+/g, " ")}`;
    if (answerMemoryCache.has(normKey)) {
      setAnswerResult(answerMemoryCache.get(normKey)!);
      setAnswerLoading(false);
      return;
    }

    setAnswerLoading(true);
    setError("");
    setAnswerResult(null);

    try {
      const params = new URLSearchParams({
        question: cleanQ,
        course_id: String(activeCourse.id),
      });
      const res = await authFetch(`${API_URL}/ask?${params.toString()}`);
      if (!res.ok) throw new Error("Could not get answer.");
      const data: AnswerResult = await res.json();
      if (data && data.answer && !data.answer.includes("could not find enough information")) {
        answerMemoryCache.set(normKey, data);
      }
      setAnswerResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get answer.");
    } finally {
      setAnswerLoading(false);
    }
  }

  // 6. Automatic Full Notes Loaders with 0ms Client Cache & Poisoning Protection
  async function loadNotes(vid: string, cId?: number, depth: "quick" | "deep" = notesDepth, forceRefresh: boolean = false) {
    const courseId = cId ?? activeCourseRef.current?.id ?? activeCourse?.id;
    if (!courseId || !vid) return;
    const cacheKey = `${courseId}_${vid}_${depth}`;

    if (!forceRefresh && notesMemoryCache.has(cacheKey)) {
      const cached = notesMemoryCache.get(cacheKey)!;
      if (isValidNoteContent(cached)) {
        setNotesMode("single");
        setNotes(cached);
        setNotesLoading(false);
        return;
      }
    }

    setNotesLoading(true);
    setNotesMode("single");
    setNotes("");
    try {
      const endpoint = depth === "deep" ? "detailed-notes" : "notes";
      const refreshParam = forceRefresh ? "&refresh=true" : "";
      const res = await authFetch(`${API_URL}/courses/${courseId}/${endpoint}?video_id=${vid}${refreshParam}`);
      const data = await res.json();
      const loaded = data.notes || "No notes available.";
      if (isValidNoteContent(loaded)) {
        notesMemoryCache.set(cacheKey, loaded);
      }
      setNotes(loaded);
    } catch {
      setNotes("Failed to load notes.");
    } finally {
      setNotesLoading(false);
    }
  }

  async function loadAllNotes(cId?: number, depth: "quick" | "deep" = notesDepth) {
    const courseId = cId ?? activeCourseRef.current?.id ?? activeCourse?.id;
    if (!courseId) return;
    const cacheKey = `${courseId}_ALL_${depth}`;

    if (notesMemoryCache.has(cacheKey)) {
      const cached = notesMemoryCache.get(cacheKey)!;
      if (isValidNoteContent(cached)) {
        setNotesMode("all");
        setSelectedVideoId("ALL");
        setNotes(cached);
        setNotesLoading(false);
        return;
      }
    }

    setNotesLoading(true);
    setNotesMode("all");
    setSelectedVideoId("ALL");
    try {
      const endpoint = depth === "deep" ? "detailed-handbook" : "all-notes";
      const res = await authFetch(`${API_URL}/courses/${courseId}/${endpoint}`);
      const data = await res.json();
      const loaded = data.handbook || "No notes available.";
      if (isValidNoteContent(loaded)) {
        notesMemoryCache.set(cacheKey, loaded);
      }
      setNotes(loaded);
    } catch {
      setNotes("Failed to compile course handbook.");
    } finally {
      setNotesLoading(false);
    }
  }

  async function loadQuiz(vid?: string, refresh: boolean = false) {
    const courseId = activeCourseRef.current?.id ?? activeCourse?.id;
    if (!courseId) return;
    const cacheKey = `${courseId}_${vid || "ALL"}`;

    if (!refresh && quizMemoryCache.has(cacheKey)) {
      const cached = quizMemoryCache.get(cacheKey)!;
      if (cached.quiz && cached.quiz.length > 0) {
        setQuiz(cached.quiz);
        setQuizSetInfo(cached.setInfo);
        setUserAnswers({});
        setShowQuizResults(false);
        setQuizLoading(false);
        return;
      }
    }

    setQuizLoading(true);
    setQuiz([]);
    setUserAnswers({});
    setShowQuizResults(false);
    if (!refresh) {
      setQuizSetInfo(null);
    }
    try {
      const base = vid && vid !== "ALL"
        ? `${API_URL}/courses/${courseId}/quiz?video_id=${vid}`
        : `${API_URL}/courses/${courseId}/quiz`;
      let url = base;
      if (refresh) {
        const nextSet = quizSetInfo ? quizSetInfo.set_index : 1;
        url += `${url.includes("?") ? "&" : "?"}refresh=true&set_index=${nextSet}`;
      }
      const res = await fetch(url);
      const data = await res.json();
      const qList = data.quiz || [];
      const sInfo = data.set_index !== undefined ? {
        set_index: data.set_index,
        total_sets: data.total_sets || 1,
        all_covered: !!data.all_covered,
        message: data.message || "",
      } : null;
      if (qList.length > 0) {
        quizMemoryCache.set(cacheKey, { quiz: qList, setInfo: sInfo });
      }
      setQuiz(qList);
      if (sInfo) {
        setQuizSetInfo(sInfo);
      }
    } catch {
      setQuiz([]);
    } finally {
      setQuizLoading(false);
    }
  }

  async function loadFlashcards(vid?: string, refresh: boolean = false) {
    const courseId = activeCourseRef.current?.id ?? activeCourse?.id;
    if (!courseId) return;
    const cacheKey = `${courseId}_${vid || "ALL"}`;

    if (!refresh && cardsMemoryCache.has(cacheKey)) {
      const cached = cardsMemoryCache.get(cacheKey)!;
      if (cached.flashcards && cached.flashcards.length > 0) {
        setFlashcards(cached.flashcards);
        setCardsSetInfo(cached.setInfo);
        setFlippedCardId(null);
        setCardsLoading(false);
        return;
      }
    }

    setCardsLoading(true);
    setFlashcards([]);
    setFlippedCardId(null);
    if (!refresh) {
      setCardsSetInfo(null);
    }
    try {
      const base = vid && vid !== "ALL"
        ? `${API_URL}/courses/${courseId}/flashcards?video_id=${vid}`
        : `${API_URL}/courses/${courseId}/flashcards`;
      let url = base;
      if (refresh) {
        const nextSet = cardsSetInfo ? cardsSetInfo.set_index : 1;
        url += `${url.includes("?") ? "&" : "?"}refresh=true&set_index=${nextSet}`;
      }
      const res = await fetch(url);
      const data = await res.json();
      const fcList = data.flashcards || [];
      const sInfo = data.set_index !== undefined ? {
        set_index: data.set_index,
        total_sets: data.total_sets || 1,
        all_covered: !!data.all_covered,
        message: data.message || "",
      } : null;
      if (fcList.length > 0) {
        cardsMemoryCache.set(cacheKey, { flashcards: fcList, setInfo: sInfo });
      }
      setFlashcards(fcList);
      if (sInfo) {
        setCardsSetInfo(sInfo);
      }
    } catch {
      setFlashcards([]);
    } finally {
      setCardsLoading(false);
    }
  }

  async function updateCardStatus(cardId: number, status: "mastered" | "reviewing") {
    try {
      await authFetch(`${API_URL}/flashcards/${cardId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      setFlashcards((prev) =>
        prev.map((c) => (c.id === cardId ? { ...c, status } : c))
      );
    } catch (err) {
      console.error("Failed to update card status:", err);
    }
  }

  function prefetchStudyTools(vid?: string, cId?: number) {
    const courseId = cId ?? activeCourseRef.current?.id ?? activeCourse?.id;
    if (!courseId || !vid || vid === "ALL") return;
    const quizKey = `${courseId}_${vid}`;
    const cardKey = `${courseId}_${vid}`;

    if (!quizMemoryCache.has(quizKey)) {
      authFetch(`${API_URL}/courses/${courseId}/quiz?video_id=${vid}`)
        .then((res) => res.json())
        .then((data) => {
          const qList = data.quiz || [];
          if (qList.length > 0) {
            const sInfo = data.set_index !== undefined ? {
              set_index: data.set_index,
              total_sets: data.total_sets || 1,
              all_covered: !!data.all_covered,
              message: data.message || "",
            } : null;
            quizMemoryCache.set(quizKey, { quiz: qList, setInfo: sInfo });
            if (activeTabRef.current === "quiz" && selectedVideoIdRef.current === vid) {
              setQuiz(qList);
              if (sInfo) setQuizSetInfo(sInfo);
            }
          }
        })
        .catch(() => {});
    }

    if (!cardsMemoryCache.has(cardKey)) {
      authFetch(`${API_URL}/courses/${courseId}/flashcards?video_id=${vid}`)
        .then((res) => res.json())
        .then((data) => {
          const fcList = data.flashcards || [];
          if (fcList.length > 0) {
            const sInfo = data.set_index !== undefined ? {
              set_index: data.set_index,
              total_sets: data.total_sets || 1,
              all_covered: !!data.all_covered,
              message: data.message || "",
            } : null;
            cardsMemoryCache.set(cardKey, { flashcards: fcList, setInfo: sInfo });
            if (activeTabRef.current === "flashcards" && selectedVideoIdRef.current === vid) {
              setFlashcards(fcList);
              if (sInfo) setCardsSetInfo(sInfo);
            }
          }
        })
        .catch(() => {});
    }
  }

  function handleTabChange(tab: "notes" | "ask" | "quiz" | "flashcards") {
    setActiveTab(tab);
    const targetVid = selectedVideoId === "ALL" ? undefined : selectedVideoId;
    if (tab === "notes" && selectedVideoId && (!notes || !isValidNoteContent(notes))) {
      if (notesMode === "all") void loadAllNotes();
      else void loadNotes(selectedVideoId);
    } else if (tab === "quiz") {
      const courseId = activeCourseRef.current?.id ?? activeCourse?.id;
      const cacheKey = `${courseId}_${targetVid || "ALL"}`;
      if (quizMemoryCache.has(cacheKey)) {
        const cached = quizMemoryCache.get(cacheKey)!;
        setQuiz(cached.quiz);
        setQuizSetInfo(cached.setInfo);
        setUserAnswers({});
        setShowQuizResults(false);
      } else {
        void loadQuiz(targetVid);
      }
    } else if (tab === "flashcards") {
      const courseId = activeCourseRef.current?.id ?? activeCourse?.id;
      const cacheKey = `${courseId}_${targetVid || "ALL"}`;
      if (cardsMemoryCache.has(cacheKey)) {
        const cached = cardsMemoryCache.get(cacheKey)!;
        setFlashcards(cached.flashcards);
        setCardsSetInfo(cached.setInfo);
        setFlippedCardId(null);
      } else {
        void loadFlashcards(targetVid);
      }
    }
  }

  /* -------------------------------------------------------------
     EXECUTIVE STUDY NOTES HTML & PDF GENERATOR
  ------------------------------------------------------------- */
  function generatePrintableNotesHtml(
    rawNotes: string,
    lectureTitle: string,
    courseTitle: string,
    autoPrint: boolean = true
  ): string {
    const text = rawNotes
      .replace(/\\longrightarrow|\\rightarrow/g, " → ")
      .replace(/\\uparrow/g, "↑")
      .replace(/\\downarrow/g, "↓")
      .replace(/\\text\{([^}]+)\}/g, "$1")
      .replace(/\$\$([^\$]+)\$\$/g, "$1")
      .replace(/\$([^\$]+)\$/g, "$1")
      .replace(/\\[a-zA-Z]+/g, "");

    const lines = text.split("\n");
    let bodyHtml = "";
    let tableRows: string[][] = [];
    let inTable = false;

    function flushTable(): string {
      if (tableRows.length === 0) return "";
      const header = tableRows[0];
      const body = tableRows.slice(1);
      tableRows = [];
      inTable = false;

      let res = `<div class="note-table-wrap"><table class="note-table"><thead><tr>`;
      header.forEach((col) => {
        res += `<th>${formatInline(col.replace(/\*\*/g, "").trim())}</th>`;
      });
      res += `</tr></thead><tbody>`;
      body.forEach((row) => {
        res += `<tr>`;
        row.forEach((cell) => {
          res += `<td>${formatInline(cell.replace(/\*\*/g, "").trim())}</td>`;
        });
        res += `</tr>`;
      });
      res += `</tbody></table></div>`;
      return res;
    }

    function formatInline(str: string): string {
      let clean = str.replace(/\$/g, "");
      clean = clean.replace(/\*\*([^*]+)\*\*/g, '<strong class="note-bold">$1</strong>');
      clean = clean.replace(/\*([^*]+)\*/g, "<em>$1</em>");
      clean = clean.replace(/`([^`]+)`/g, '<code class="note-code">$1</code>');
      return clean;
    }

    lines.forEach((rawLine) => {
      const line = rawLine.trim();

      if (line.startsWith("|") && line.endsWith("|")) {
        if (line.includes("---")) return;
        const cols = line
          .split("|")
          .slice(1, -1)
          .map((c) => c.trim());
        tableRows.push(cols);
        inTable = true;
        return;
      } else if (inTable) {
        bodyHtml += flushTable();
      }

      if (!line) {
        bodyHtml += `<div class="note-gap"></div>`;
        return;
      }

      if (line === "---" || line === "***") {
        bodyHtml += `<hr class="note-divider" />`;
        return;
      }

      if (line.startsWith("# ")) {
        const heading = line.replace("# ", "").replace(/\*\*/g, "");
        bodyHtml += `<h1 class="note-h1">${formatInline(heading)}</h1>`;
        return;
      }

      if (line.startsWith("## ")) {
        const heading = line.replace("## ", "").replace(/\*\*/g, "");
        bodyHtml += `<h2 class="note-h2">${formatInline(heading)}</h2>`;
        return;
      }

      if (line.startsWith("### ")) {
        const heading = line.replace("### ", "").replace(/\*\*/g, "");
        bodyHtml += `<h3 class="note-h3">${formatInline(heading)}</h3>`;
        return;
      }

      if (line.startsWith("* ") || line.startsWith("- ")) {
        const itemText = line.slice(2);
        bodyHtml += `<div class="note-bullet"><span class="note-dot"></span><span class="note-bullet-text">${formatInline(itemText)}</span></div>`;
        return;
      }

      if (line.includes("→")) {
        bodyHtml += `<div class="note-callout">${formatInline(line)}</div>`;
        return;
      }

      bodyHtml += `<p class="note-p">${formatInline(line)}</p>`;
    });

    if (inTable) bodyHtml += flushTable();

    const formattedDate = new Date().toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });

    const isDeep = notesDepth === "deep";

    return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${lectureTitle} - CoursePilot Notes</title>
    <style>
      @page {
        size: A4;
        margin: 14mm 16mm 16mm 16mm;
      }
      * {
        box-sizing: border-box;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #18181b;
        background: #f8fafc;
        margin: 0;
        padding: 24px 20px;
        line-height: 1.65;
        -webkit-font-smoothing: antialiased;
      }
      .no-print {
        display: flex;
        align-items: center;
        justify-content: space-between;
        max-width: 860px;
        margin: 0 auto 20px auto;
        padding: 12px 18px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }
      .print-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #18181b;
        color: #ffffff;
        font-size: 13px;
        font-weight: 600;
        padding: 8px 16px;
        border-radius: 8px;
        border: none;
        cursor: pointer;
      }
      .print-btn:hover {
        background: #27272a;
      }
      .html-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #ffffff;
        color: #334155;
        border: 1px solid #cbd5e1;
        font-size: 13px;
        font-weight: 600;
        padding: 8px 16px;
        border-radius: 8px;
        cursor: pointer;
      }
      .html-btn:hover {
        background: #f1f5f9;
      }
      .note-card {
        max-width: 860px;
        margin: 0 auto;
        background: #ffffff;
        border: 1px solid #e4e4e7;
        border-radius: 16px;
        padding: 36px 42px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      }
      .app-header {
        border-bottom: 1px solid #e4e4e7;
        padding-bottom: 20px;
        margin-bottom: 28px;
      }
      .brand-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
      }
      .brand-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #09090b;
        color: #ffffff;
        font-size: 11px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        letter-spacing: 0.3px;
      }
      .notes-mode-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1d4ed8;
        font-size: 11.5px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 9999px;
      }
      .main-title {
        font-size: 22px;
        font-weight: 700;
        color: #09090b;
        letter-spacing: -0.4px;
        margin: 0 0 6px 0;
        line-height: 1.3;
      }
      .meta-subtitle {
        font-size: 13px;
        color: #71717a;
        margin: 0;
      }
      .note-h1 {
        margin-top: 36px;
        margin-bottom: 16px;
        font-size: 24px;
        font-weight: 700;
        letter-spacing: -0.4px;
        color: #09090b;
        line-height: 1.3;
      }
      .note-h2 {
        margin-top: 32px;
        margin-bottom: 14px;
        border-bottom: 1px solid #e4e4e7;
        padding-bottom: 10px;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: -0.2px;
        color: #09090b;
        page-break-after: avoid;
      }
      .note-h3 {
        margin-top: 24px;
        margin-bottom: 10px;
        font-size: 13.5px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #2563eb;
        page-break-after: avoid;
      }
      .note-p {
        margin: 8px 0;
        font-size: 15px;
        line-height: 1.65;
        color: #27272a;
      }
      .note-bullet {
        margin: 8px 0;
        display: flex;
        align-items: flex-start;
        gap: 10px;
        font-size: 15px;
        line-height: 1.65;
        color: #27272a;
      }
      .note-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #3b82f6;
        margin-top: 9px;
        flex-shrink: 0;
      }
      .note-bullet-text {
        flex: 1;
      }
      .note-callout {
        margin: 14px 0;
        border-radius: 12px;
        border: 1px solid #dbeafe;
        background: #eff6ff;
        padding: 14px 18px;
        font-size: 14.5px;
        font-weight: 500;
        line-height: 1.6;
        color: #172554;
        page-break-inside: avoid;
      }
      .note-table-wrap {
        margin: 20px 0;
        border: 1px solid #e4e4e7;
        border-radius: 12px;
        overflow: hidden;
        page-break-inside: avoid;
      }
      .note-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
        font-size: 13.5px;
      }
      .note-table thead th {
        background: #f8fafc;
        border-bottom: 1px solid #e4e4e7;
        padding: 10px 16px;
        font-weight: 600;
        color: #09090b;
      }
      .note-table tbody td {
        padding: 10px 16px;
        border-bottom: 1px solid #e4e4e7;
        color: #334155;
      }
      .note-table tbody tr:last-child td {
        border-bottom: none;
      }
      .note-table tbody tr:nth-child(even) td {
        background: #fafafa;
      }
      .note-code {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 12.5px;
        background: #f4f4f5;
        border: 1px solid #e4e4e7;
        padding: 2px 6px;
        border-radius: 4px;
        color: #09090b;
      }
      .note-bold {
        font-weight: 600;
        color: #09090b;
      }
      .note-divider {
        border: none;
        border-top: 1px solid #e4e4e7;
        margin: 24px 0;
      }
      .note-gap {
        height: 12px;
      }

      @media print {
        body {
          background: #ffffff !important;
          padding: 0 !important;
        }
        .no-print {
          display: none !important;
        }
        .note-card {
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
          max-width: 100% !important;
        }
        .note-h2, .note-h3 {
          page-break-after: avoid;
        }
        .note-callout, .note-table-wrap {
          page-break-inside: avoid;
        }
      }
    </style>
  </head>
  <body>
    <div class="no-print">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-weight: 700; font-size: 13px; color: #09090b;">CoursePilot</span>
        <span style="font-size: 12px; color: #71717a;">• Exact Study Notes</span>
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
        <button class="html-btn" onclick="downloadHtmlFile()">Download HTML</button>
        <button class="html-btn" onclick="window.close()">Close</button>
      </div>
    </div>

    <div class="note-card">
      <div class="app-header">
        <div class="brand-row">
          <span class="brand-badge">CoursePilot • Study Notes</span>
          <span class="notes-mode-badge">${isDeep ? "Deep Notes" : "Quick Notes"} • ${courseTitle}</span>
        </div>
        <h1 class="main-title">${lectureTitle}</h1>
        <p class="meta-subtitle">Course Study Guide • Generated ${formattedDate}</p>
      </div>

      <div class="note-body">
        ${bodyHtml}
      </div>
    </div>

    <script>
      ${autoPrint ? `window.onload = function() {
        setTimeout(function() {
          window.print();
        }, 300);
      };` : ""}
      function downloadHtmlFile() {
        var blob = new Blob([document.documentElement.outerHTML], { type: 'text/html;charset=utf-8' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = document.title.replace(/[^a-zA-Z0-9_\-]/g, '_') + '.html';
        a.click();
      }
    </script>
  </body>
</html>`;
  }

  function downloadHtml() {
    if (!notes) return;
    const isMasterHandbook = notesMode === "all" || selectedVideoId === "ALL";
    const currentVideo = videos.find((v) => v.video_id === selectedVideoId);
    const title = isMasterHandbook
      ? `${activeCourse?.title || "Course"} - Complete Study Handbook`
      : currentVideo ? currentVideo.title : activeCourse?.title || "Lecture Notes";
    const courseTitle = activeCourse?.title || "Course";

    const fullHtml = generatePrintableNotesHtml(notes, title, courseTitle, false);
    const blob = new Blob([fullHtml], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const cleanTitle = title.replace(/[^a-zA-Z0-9_\-]/g, "_").slice(0, 50);
    link.download = `${cleanTitle}_CoursePilot_Notes.html`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function downloadMarkdown() {
    if (!notes) return;
    const isMasterHandbook = notesMode === "all" || selectedVideoId === "ALL";
    const currentVideo = videos.find((v) => v.video_id === selectedVideoId);
    const title = isMasterHandbook
      ? `${activeCourse?.title || "Course"} - Complete Study Handbook`
      : currentVideo ? currentVideo.title : activeCourse?.title || "lecture-notes";
    const courseTitle = activeCourse?.title || "Course";
    const filename = `${title.replace(/[^a-z0-9]/gi, "-").toLowerCase()}.md`;

    const formattedDate = new Date().toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });

    const cleanNotes = notes
      .replace(/\\longrightarrow|\\rightarrow/g, " → ")
      .replace(/\\uparrow/g, "↑")
      .replace(/\\downarrow/g, "↓")
      .replace(/\\text\{([^}]+)\}/g, "$1")
      .replace(/\$\$([^\$]+)\$\$/g, "$1")
      .replace(/\$([^\$]+)\$/g, "$1")
      .replace(/\\[a-zA-Z]+/g, "");

    const brandedMarkdown = [
      `# ${title}`,
      ``,
      `> **Course:** ${courseTitle}`,
      `> **Document:** ${isMasterHandbook ? "Complete Course Master Handbook" : "Lecture Study Notes"}`,
      `> **Date Generated:** ${formattedDate}`,
      `> **Source:** Course Lecture Transcripts`,
      ``,
      `---`,
      ``,
      cleanNotes,
      ``,
      `---`,
      `*Generated with CoursePilot*`,
    ].join("\n");

    const blob = new Blob([brandedMarkdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function downloadPdf() {
    if (!notes) return;
    const isMasterHandbook = notesMode === "all" || selectedVideoId === "ALL";
    const currentVideo = videos.find((v) => v.video_id === selectedVideoId);
    const title = isMasterHandbook
      ? `${activeCourse?.title || "Course"} - Complete Study Handbook`
      : currentVideo ? currentVideo.title : activeCourse?.title || "Lecture Notes";
    const courseTitle = activeCourse?.title || "Course";

    const printWin = window.open("", "_blank");
    if (!printWin) return;

    const fullHtml = generatePrintableNotesHtml(notes, title, courseTitle);
    printWin.document.write(fullHtml);
    printWin.document.close();
  }

  function copyNotes() {
    if (!notes) return;
    void navigator.clipboard.writeText(notes);
    setCopyToast(true);
    setTimeout(() => setCopyToast(false), 2000);
  }

  const filteredVideos = useMemo(() => {
    if (!videoSearch.trim()) return videos;
    return videos.filter((v) =>
      v.title.toLowerCase().includes(videoSearch.toLowerCase())
    );
  }, [videos, videoSearch]);

  const activeVideo = videos.find((v) => v.video_id === selectedVideoId);

  const score = Object.entries(userAnswers).reduce((acc, [qId, optIdx]) => {
    const q = quiz.find((item) => item.id === Number(qId));
    return q && q.correct_index === optIdx ? acc + 1 : acc;
  }, 0);

  if (!isLoaded || !isSignedIn) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-white dark:bg-zinc-950">
        <div className="flex flex-col items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-zinc-900 text-xs font-bold text-white dark:bg-white dark:text-zinc-900">
              CP
            </div>
            <span className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-white">
              CoursePilot
            </span>
          </div>
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-white"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white text-zinc-900 antialiased dark:bg-zinc-950 dark:text-zinc-100">
      {/* -------------------------------------------------------------
          SIDEBAR RENDER HELPER (DESKTOP + MOBILE SHEET)
      ------------------------------------------------------------- */}
      {(() => {
        const renderSidebarContent = (isMobile: boolean) => (
          <div className="flex h-full flex-col">
            <div className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 px-4 dark:border-zinc-800">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-zinc-900 text-xs font-bold text-white dark:bg-white dark:text-zinc-900">
                  CP
                </div>
                <span className="text-sm font-semibold tracking-tight">CoursePilot</span>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => {
                    setShowAddModal(true);
                    if (isMobile) setMobileMenuOpen(false);
                  }}
                  className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-md border border-zinc-300 text-sm font-semibold text-zinc-700 hover:bg-zinc-200 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                  title="Add Playlist"
                >
                  +
                </button>
                {isMobile && (
                  <button
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-md border border-zinc-200 text-zinc-500 hover:bg-zinc-100 dark:border-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-800"
                    title="Close navigation"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            </div>

            <div className="border-b border-zinc-200 p-3 dark:border-zinc-800">
              <div className="flex items-center justify-between">
                <label htmlFor={isMobile ? "mobile-course-select" : "course-select"} className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                  Selected Course
                </label>
                {activeCourse && (
                  <button
                    onClick={() => {
                      void handleDeleteCourse(activeCourse.id);
                      if (isMobile) setMobileMenuOpen(false);
                    }}
                    disabled={deleteLoading}
                    className="cursor-pointer text-[11px] font-medium text-red-500 hover:text-red-600 hover:underline disabled:opacity-50 dark:text-red-400 dark:hover:text-red-300"
                    title="Delete this course and reclaim storage"
                  >
                    {deleteLoading ? "Deleting..." : "Delete Course"}
                  </button>
                )}
              </div>
              <select
                id={isMobile ? "mobile-course-select" : "course-select"}
                value={activeCourse?.id ?? ""}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  const found = courses.find((c) => c.id === id);
                  if (found) {
                    setActiveCourse(found);
                    setVideos(found.videos ?? []);
                    const vList = found.videos ?? [];
                    if (vList.length > 0) {
                      const preferred = vList.find((v: Video) => v.status === "completed") || vList[0];
                      setSelectedVideoId(preferred.video_id);
                      setNotesMode("single");
                      void loadNotes(preferred.video_id, found.id);
                    }
                    if (isMobile) setMobileMenuOpen(false);
                  }
                }}
                className="mt-1 w-full cursor-pointer truncate rounded-md border border-zinc-300 bg-white px-2.5 py-1.5 text-xs font-medium shadow-xs outline-none dark:border-zinc-700 dark:bg-zinc-800"
              >
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            </div>

            <div className="px-3 pt-3">
              <input
                type="text"
                placeholder="Search lectures..."
                value={videoSearch}
                onChange={(e) => setVideoSearch(e.target.value)}
                className="w-full rounded-md border border-zinc-200 bg-white px-2.5 py-1 text-xs outline-none placeholder:text-zinc-400 dark:border-zinc-800 dark:bg-zinc-950"
              />
            </div>

            <div className="flex-1 overflow-y-auto px-2 py-3">
              {/* PINNED MASTER HANDBOOK (ALL NOTES) BUTTON */}
              <button
                onClick={() => {
                  setActiveTab("notes");
                  void loadAllNotes();
                  if (isMobile) setMobileMenuOpen(false);
                }}
                className={`mb-3 flex w-full cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition-all ${
                  notesMode === "all" && activeTab === "notes"
                    ? "bg-zinc-900 font-semibold text-white shadow-xs dark:bg-white dark:text-zinc-900"
                    : "border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-100 font-medium dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
                }`}
              >
                <span className="truncate font-medium">Complete Course Handbook</span>
              </button>

              <div className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                Individual Lectures ({filteredVideos.length})
              </div>
              <div className="space-y-0.5">
                {filteredVideos.map((video) => {
                  const isSelected = selectedVideoId === video.video_id && notesMode === "single";
                  const isDone = video.status === "completed";
                  const isProcessing = video.status === "processing";
                  return (
                    <button
                      key={video.video_id}
                      onClick={() => {
                        handleSelectVideo(video.video_id);
                        if (isMobile) setMobileMenuOpen(false);
                      }}
                      className={`flex w-full cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-left text-xs transition-colors ${
                        isSelected
                          ? "bg-zinc-200 font-semibold text-zinc-950 dark:bg-zinc-800 dark:text-white"
                          : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-200"
                      }`}
                    >
                      <span className="flex h-4 w-4 shrink-0 items-center justify-center">
                        {isDone ? (
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                        ) : isProcessing ? (
                          <span className="h-2 w-2 animate-ping rounded-full bg-blue-500"></span>
                        ) : (
                          <span className="h-1.5 w-1.5 rounded-full bg-zinc-300 dark:bg-zinc-700"></span>
                        )}
                      </span>
                      <span className="font-mono text-[10px] text-zinc-400">{video.position}.</span>
                      <span className="truncate">{video.title}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="border-t border-zinc-200 p-2 space-y-1 dark:border-zinc-800">
              <button
                onClick={() => {
                  setShowFeedbackModal(true);
                  if (isMobile) setMobileMenuOpen(false);
                }}
                className="flex w-full cursor-pointer items-center justify-between rounded-md px-2.5 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800/80 dark:hover:text-zinc-200"
              >
                <span className="flex items-center gap-2">
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                  </svg>
                  Feedback
                </span>
                <span className="text-[10px] text-zinc-400">Report / Idea</span>
              </button>

              {isAdmin && (
                <Link
                  href="/admin"
                  className="flex w-full cursor-pointer items-center justify-between rounded-md px-2.5 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800/80 dark:hover:text-zinc-200"
                >
                  <span className="flex items-center gap-2">
                    <svg className="h-3.5 w-3.5 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    Admin Panel
                  </span>
                  <span className="rounded bg-zinc-200/80 px-1.5 py-0.5 text-[9px] font-semibold text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                    Owner
                  </span>
                </Link>
              )}
            </div>

            <div className="flex h-11 shrink-0 items-center justify-between border-t border-zinc-200 px-4 text-[11px] font-medium text-zinc-500 dark:border-zinc-800">
              <span>Backend</span>
              <span className="flex items-center gap-1.5">
                {isBackendConnecting ? (
                  <>
                    <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse"></span>
                    <span className="text-amber-600 dark:text-amber-400">Connecting...</span>
                  </>
                ) : (
                  <>
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                    <span className="text-emerald-600 dark:text-emerald-400">Online</span>
                  </>
                )}
              </span>
            </div>
          </div>
        );

        return (
          <>
            {/* Desktop Left Sidebar */}
            <aside className="hidden md:flex md:w-72 md:shrink-0 md:flex-col border-r border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900/60">
              {renderSidebarContent(false)}
            </aside>

            {/* Mobile Slide-Over Sheet */}
            {mobileMenuOpen && (
              <div className="fixed inset-0 z-50 flex md:hidden">
                <div
                  className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
                  onClick={() => setMobileMenuOpen(false)}
                  aria-hidden="true"
                />
                <div className="relative z-10 flex w-72 max-w-[82vw] flex-col border-r border-zinc-200 bg-zinc-50 shadow-2xl dark:border-zinc-800 dark:bg-zinc-900">
                  {renderSidebarContent(true)}
                </div>
              </div>
            )}
          </>
        );
      })()}

      {/* -------------------------------------------------------------
          MAIN WORKSPACE
      ------------------------------------------------------------- */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header Bar */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 bg-white px-3 sm:px-6 dark:border-zinc-800 dark:bg-zinc-950">
          <div className="flex items-center gap-2 min-w-0">
            {/* Mobile Hamburger Button */}
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="flex h-8 w-8 items-center justify-center rounded-md border border-zinc-200 text-zinc-600 hover:bg-zinc-100 md:hidden dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-900"
              aria-label="Open lecture menu"
              title="Open lecture menu"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="flex items-center gap-1.5 text-xs truncate min-w-0">
              <span className="hidden font-medium text-zinc-400 sm:inline truncate max-w-[120px]">{activeCourse?.title || "Course"}</span>
              <span className="hidden text-zinc-300 dark:text-zinc-700 sm:inline">/</span>
              <span className="font-semibold text-zinc-900 dark:text-white truncate max-w-[150px] sm:max-w-xs md:max-w-md">
                {notesMode === "all" && activeTab === "notes"
                  ? "Full Course Handbook"
                  : activeVideo?.title || "Select Lecture"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-3">
            <div className="flex items-center rounded-lg border border-zinc-200 bg-zinc-100 p-0.5 text-xs font-medium dark:border-zinc-800 dark:bg-zinc-900">
              <button
                onClick={() => handleTabChange("notes")}
                className={`cursor-pointer rounded-md px-2 sm:px-3.5 py-1 sm:py-1.5 transition-all text-xs ${
                  activeTab === "notes"
                    ? "bg-white font-semibold text-zinc-900 shadow-xs dark:bg-zinc-800 dark:text-white"
                    : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400"
                }`}
              >
                <span className="sm:hidden">Notes</span>
                <span className="hidden sm:inline">Lecture Notes</span>
              </button>
              <button
                onClick={() => handleTabChange("ask")}
                className={`cursor-pointer rounded-md px-2 sm:px-3.5 py-1 sm:py-1.5 transition-all text-xs ${
                  activeTab === "ask"
                    ? "bg-white font-semibold text-zinc-900 shadow-xs dark:bg-zinc-800 dark:text-white"
                    : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400"
                }`}
              >
                <span className="sm:hidden">Ask AI</span>
                <span className="hidden sm:inline">Ask AI Q&A</span>
              </button>
              <button
                onClick={() => handleTabChange("quiz")}
                className={`cursor-pointer rounded-md px-2 sm:px-3.5 py-1 sm:py-1.5 transition-all text-xs ${
                  activeTab === "quiz"
                    ? "bg-white font-semibold text-zinc-900 shadow-xs dark:bg-zinc-800 dark:text-white"
                    : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400"
                }`}
              >
                <span className="sm:hidden">Quiz</span>
                <span className="hidden sm:inline">Practice Quiz</span>
              </button>
              <button
                onClick={() => handleTabChange("flashcards")}
                className={`cursor-pointer rounded-md px-2 sm:px-3.5 py-1 sm:py-1.5 transition-all text-xs ${
                  activeTab === "flashcards"
                    ? "bg-white font-semibold text-zinc-900 shadow-xs dark:bg-zinc-800 dark:text-white"
                    : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400"
                }`}
              >
                <span className="sm:hidden">Cards</span>
                <span className="hidden sm:inline">Flashcards</span>
              </button>
            </div>

            {/* Clerk User Profile */}
            <div className="flex items-center gap-2 pl-1 sm:pl-2">
              {user && (
                <span className="hidden text-xs font-medium text-zinc-600 lg:inline-block dark:text-zinc-400">
                  {user.firstName ? `Hi, ${user.firstName}` : user.primaryEmailAddress?.emailAddress}
                </span>
              )}
              <UserButton />
            </div>
          </div>
        </header>

        {/* LIVE BACKGROUND INDEXING PROGRESS BANNER */}
        {progress && progress.status === "indexing" && progress.percentage < 100 && (
          <div className="border-b border-zinc-200 bg-zinc-50/90 px-6 py-2.5 text-xs text-zinc-800 dark:border-zinc-800 dark:bg-zinc-900/70 dark:text-zinc-200">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-zinc-900 dark:text-white">
                  Indexing playlist: {progress.percentage}%
                </span>
                <span className="text-zinc-500">
                  ({progress.completed} of {progress.total} lectures ready)
                </span>
                {progress.current_video && (
                  <span className="hidden truncate font-normal text-zinc-600 sm:inline dark:text-zinc-400">
                    • Processing: &quot;{progress.current_video}&quot;
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                  Completed lectures are ready to study
                </span>
                <button
                  onClick={handleResumeIndexing}
                  className="cursor-pointer text-[11px] font-semibold text-zinc-900 underline hover:text-zinc-700 dark:text-white dark:hover:text-zinc-300"
                  title="Resume indexing if the process was interrupted"
                >
                  Resume
                </button>
              </div>
            </div>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
              <div
                className="h-full bg-zinc-900 transition-all duration-500 dark:bg-white"
                style={{ width: `${progress.percentage}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Content Canvas */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-4xl">
            {isBackendConnecting && courses.length === 0 && (
              <div className="mb-6 flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50/80 p-3.5 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200">
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-amber-600 border-t-transparent dark:border-amber-400"></div>
                <span>Connecting to CoursePilot backend... The page will connect and load your courses automatically.</span>
              </div>
            )}
            {error && (
              <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
                {error}
              </div>
            )}

            {/* TAB: LECTURE NOTES */}
            {activeTab === "notes" && (
              <div>
                <div className="mb-6 flex flex-col gap-4 border-b border-zinc-200 pb-5 sm:flex-row sm:items-center sm:justify-between dark:border-zinc-800">
                  <div>
                    <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-white">
                      {notesMode === "all"
                        ? `Course Handbook: ${activeCourse?.title || "Course"}`
                        : activeVideo?.title || "Lecture Notes"}
                    </h1>
                    <p className="mt-0.5 text-xs text-zinc-500">
                      {notesMode === "all"
                        ? "Comprehensive notes synthesized across all course lectures"
                        : "Key concepts and structural breakdown from lecture transcript"}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {/* Quick vs Deep Notes Toggle */}
                    <div className="flex rounded-lg border border-zinc-200 bg-zinc-100 p-0.5 text-xs font-medium dark:border-zinc-800 dark:bg-zinc-900">
                      <button
                        type="button"
                        onClick={() => {
                          setNotesDepth("quick");
                          if (notesMode === "all") {
                            void loadAllNotes(undefined, "quick");
                          } else if (selectedVideoId) {
                            void loadNotes(selectedVideoId, undefined, "quick");
                          }
                        }}
                        className={`cursor-pointer rounded-md px-3 py-1 transition-all ${
                          notesDepth === "quick"
                            ? "bg-white font-semibold text-zinc-900 shadow-xs dark:bg-zinc-800 dark:text-white"
                            : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white"
                        }`}
                      >
                        Quick Notes
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setNotesDepth("deep");
                          if (notesMode === "all") {
                            void loadAllNotes(undefined, "deep");
                          } else if (selectedVideoId) {
                            void loadNotes(selectedVideoId, undefined, "deep");
                          }
                        }}
                        className={`cursor-pointer rounded-md px-3 py-1 transition-all ${
                          notesDepth === "deep"
                            ? "bg-white font-semibold text-zinc-900 shadow-xs dark:bg-zinc-800 dark:text-white"
                            : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white"
                        }`}
                      >
                        Deep Notes
                      </button>
                    </div>

                    <button
                      onClick={copyNotes}
                      disabled={!notes || notesLoading}
                      className="flex cursor-pointer items-center gap-1.5 rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 shadow-xs hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    >
                      {copyToast ? "Copied" : "Copy"}
                    </button>
                    <button
                      onClick={downloadMarkdown}
                      disabled={!notes || notesLoading}
                      className="flex cursor-pointer items-center gap-1.5 rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 shadow-xs hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    >
                      Export .md
                    </button>
                    <button
                      onClick={downloadHtml}
                      disabled={!notes || notesLoading}
                      className="flex cursor-pointer items-center gap-1.5 rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 shadow-xs hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    >
                      Export .html
                    </button>
                    <button
                      onClick={downloadPdf}
                      disabled={!notes || notesLoading || !activeCourse}
                      className={`inline-flex items-center gap-1.5 rounded-md bg-zinc-900 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white ${
                        !notes || notesLoading || !activeCourse ? "pointer-events-none opacity-50" : "cursor-pointer"
                      }`}
                    >
                      Download PDF
                    </button>
                  </div>
                </div>

                {notesLoading ? (
                  <div className="my-16 text-center text-zinc-500">
                    <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-white"></div>
                    <p className="mt-3 text-xs font-medium">
                      {notesMode === "all" ? "Compiling full course handbook..." : "Synthesizing study notes..."}
                    </p>
                  </div>
                ) : activeVideo && activeVideo.status !== "completed" && notesMode === "single" ? (
                  <LectureProcessingCard
                    video={activeVideo}
                    videos={videos}
                    onSelectVideo={handleSelectVideo}
                  />
                ) : (
                  <div className="rounded-xl border border-zinc-200 bg-white p-8 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
                    <NotionDocumentViewer content={notes} />
                  </div>
                )}
              </div>
            )}

            {/* TAB: ASK AI Q&A */}
            {activeTab === "ask" && (
              <div className="space-y-6">
                <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-bold tracking-tight text-zinc-900 dark:text-white">
                      Ask a question about this course
                    </h2>
                    <span className="text-[11px] font-medium text-blue-600 dark:text-blue-400">
                      Scope: {activeCourse?.title || "Active Course"}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-zinc-500">
                    Ask questions about this course. Answers cite verified video timestamps.
                  </p>

                  <form onSubmit={handleAskQuestion} className="mt-4 flex gap-2">
                    <input
                      type="text"
                      placeholder="e.g. Bioaccumulation vs Biomagnification mein kya difference hai?"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      disabled={answerLoading}
                      className="flex-1 rounded-lg border border-zinc-200 bg-transparent px-3.5 py-2 text-xs outline-none focus:border-zinc-400 disabled:opacity-60 dark:border-zinc-800"
                    />
                    <button
                      type="submit"
                      disabled={answerLoading}
                      className="cursor-pointer rounded-lg bg-zinc-900 px-4 py-2 text-xs font-semibold text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
                    >
                      {answerLoading ? "Searching..." : "Ask Question"}
                    </button>
                  </form>

                  {answerLoading && (
                    <div className="mt-4 flex items-center gap-3 rounded-lg border border-zinc-200 bg-zinc-50 p-3.5 text-xs text-zinc-800 dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-200">
                      <div className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-white"></div>
                      <div className="flex flex-col">
                        <span className="font-semibold text-zinc-900 dark:text-white">Searching lecture transcripts...</span>
                        <span className="text-[11px] text-zinc-500">
                          Locating relevant segments and timestamp citations
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {answerResult && (
                  <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                      Answer
                    </div>
                    <div className="mt-2 text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">
                      <NotionDocumentViewer content={answerResult.answer} />
                    </div>

                    {answerResult.sources?.length > 0 && (
                      <div className="mt-5 border-t border-zinc-100 pt-4 dark:border-zinc-800">
                        <div className="flex items-center justify-between">
                          <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                            Verified Source Timestamps (Ranked by Relevance & Explanation Depth)
                          </div>
                          <span className="text-[10px] text-zinc-400">
                            Prioritizing in-depth discussions over brief mentions
                          </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {answerResult.sources.map((src, i) => {
                            const dur = Math.max(10, Math.floor(src.end - src.start));
                            const isDeep = dur >= 120;
                            const durFormatted = src.duration_label || (dur >= 60 ? `${Math.floor(dur / 60)}m ${dur % 60}s` : `${dur}s`);
                            return (
                              <a
                                key={i}
                                href={`https://www.youtube.com/watch?v=${src.video_id}&t=${Math.floor(src.start)}s`}
                                target="_blank"
                                rel="noreferrer"
                                title={`Jump to ${Math.floor(src.start / 60)}:${(Math.floor(src.start % 60)).toString().padStart(2, "0")} (${durFormatted})`}
                                className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                                  i === 0
                                    ? "border-blue-400/80 bg-blue-50/90 text-blue-950 font-semibold shadow-xs hover:bg-blue-100 dark:border-blue-700 dark:bg-blue-950/60 dark:text-blue-100"
                                    : "border-zinc-200 bg-zinc-50 text-zinc-700 hover:border-zinc-300 hover:bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-300 dark:hover:bg-zinc-900"
                                }`}
                              >
                                <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[9px] text-white ${i === 0 ? "bg-blue-600" : "bg-zinc-500"}`}>
                                  ▶
                                </span>
                                <span>Source {i + 1}</span>
                                <span className="font-mono text-[11px] opacity-75">
                                  {Math.floor(src.start / 60)}:{(Math.floor(src.start % 60)).toString().padStart(2, "0")}
                                </span>
                                <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                                  isDeep
                                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300"
                                    : "bg-zinc-200/60 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
                                }`}>
                                  {durFormatted}
                                </span>
                              </a>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Inline Answer Feedback */}
                    <div className="mt-4 flex items-center justify-between border-t border-zinc-100 pt-3 text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                      <span className="text-[11px]">Was this answer accurate and helpful?</span>
                      <div className="flex items-center gap-1.5">
                        {answerFeedbackGiven ? (
                          <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                            ✓ Thank you for your feedback!
                          </span>
                        ) : (
                          <>
                            <button
                              onClick={() => void handleQuickAnswerFeedback(1)}
                              className="flex cursor-pointer items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-[11px] font-medium hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800"
                              title="Helpful answer"
                            >
                              <svg className="h-3 w-3 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
                              </svg>
                              Helpful
                            </button>
                            <button
                              onClick={() => void handleQuickAnswerFeedback(-1)}
                              className="flex cursor-pointer items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-[11px] font-medium hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800"
                              title="Not helpful or inaccurate"
                            >
                              <svg className="h-3 w-3 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" />
                              </svg>
                              Needs Work
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB: PRACTICE QUIZ */}
            {activeTab === "quiz" && (
              <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
                <div className="flex items-center justify-between border-b border-zinc-200 pb-4 dark:border-zinc-800">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold tracking-tight text-zinc-900 dark:text-white">
                        Lecture Knowledge Check
                      </h2>
                      {quizSetInfo && (
                        <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-[11px] font-semibold text-blue-800 dark:bg-blue-950 dark:text-blue-300">
                          Set {quizSetInfo.set_index} of {quizSetInfo.total_sets}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-500">5 multiple choice questions grounded in this lecture section.</p>
                  </div>
                  <button
                    onClick={() => void loadQuiz(selectedVideoId === "ALL" ? undefined : selectedVideoId, true)}
                    disabled={quizLoading}
                    className="cursor-pointer rounded-md border border-zinc-200 px-3 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-800"
                  >
                    {quizLoading ? "Loading..." : "New Quiz (Next Set)"}
                  </button>
                </div>

                {quizSetInfo?.all_covered && (
                  <div className="mt-4 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/70 p-3 text-xs font-medium text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-600 text-white"><svg className="h-2.5 w-2.5 stroke-current" fill="none" viewBox="0 0 24 24" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg></span>
                    <span>{quizSetInfo.message || "You have covered all questions & concepts from this lecture. Starting revision from Set 1."}</span>
                  </div>
                )}

                {quizLoading ? (
                  <div className="my-16 text-center text-zinc-500">
                    <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-white"></div>
                    <p className="mt-3 text-xs font-medium">Formulating quiz questions...</p>
                  </div>
                ) : activeVideo && activeVideo.status !== "completed" && selectedVideoId !== "ALL" ? (
                  <LectureProcessingCard
                    video={activeVideo}
                    videos={videos}
                    onSelectVideo={handleSelectVideo}
                  />
                ) : quiz.length > 0 ? (
                  <div className="mt-6 space-y-6">
                    {quiz.map((q, idx) => {
                      const selectedOpt = userAnswers[q.id];
                      return (
                        <div key={q.id} className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
                          <p className="text-sm font-semibold text-zinc-900 dark:text-white">
                            {idx + 1}. {q.question}
                          </p>

                          <div className="mt-3 grid gap-2 sm:grid-cols-2">
                            {q.options.map((opt, oIdx) => {
                              const isChosen = selectedOpt === oIdx;
                              let btnClass = "border-zinc-200 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800/60";

                              if (showQuizResults) {
                                if (oIdx === q.correct_index) {
                                  btnClass = "border-emerald-500 bg-emerald-50 text-emerald-900 font-semibold dark:bg-emerald-950/40 dark:text-emerald-200";
                                } else if (isChosen && oIdx !== q.correct_index) {
                                  btnClass = "border-red-400 bg-red-50 text-red-900 dark:bg-red-950/40 dark:text-red-200";
                                }
                              } else if (isChosen) {
                                btnClass = "border-zinc-900 bg-zinc-100 font-medium text-zinc-900 dark:border-white dark:bg-zinc-800 dark:text-white";
                              }

                              return (
                                <button
                                  key={oIdx}
                                  onClick={() => {
                                    if (!showQuizResults) {
                                      setUserAnswers((prev) => ({ ...prev, [q.id]: oIdx }));
                                    }
                                  }}
                                  className={`flex cursor-pointer items-center gap-2.5 rounded-md border p-2.5 text-left text-xs transition-colors ${btnClass}`}
                                >
                                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded border text-[10px] font-mono">
                                    {String.fromCharCode(65 + oIdx)}
                                  </span>
                                  <span>{opt}</span>
                                </button>
                              );
                            })}
                          </div>

                          {showQuizResults && (
                            <div className="mt-3 rounded-md bg-zinc-50 p-2.5 text-xs text-zinc-600 dark:bg-zinc-950 dark:text-zinc-400">
                              <span className="font-semibold text-zinc-900 dark:text-white">Explanation: </span>
                              {q.explanation}
                            </div>
                          )}
                        </div>
                      );
                    })}

                    <div className="flex items-center justify-between border-t border-zinc-200 pt-4 dark:border-zinc-800">
                      {showQuizResults ? (
                        <div className="text-xs font-semibold text-zinc-900 dark:text-white">
                          Score: <span className="text-blue-600 font-bold">{score} / {quiz.length}</span> ({Math.round((score / quiz.length) * 100)}%)
                        </div>
                      ) : (
                        <span className="text-xs text-zinc-400">
                          {Object.keys(userAnswers).length} of {quiz.length} answered
                        </span>
                      )}

                      <button
                        onClick={() => setShowQuizResults((prev) => !prev)}
                        className="cursor-pointer rounded-md bg-zinc-900 px-4 py-2 text-xs font-semibold text-white hover:bg-zinc-800 dark:bg-white dark:text-zinc-900"
                      >
                        {showQuizResults ? "Review Options" : "Check Answers"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="mt-6 text-xs text-zinc-400">No questions available.</p>
                )}
              </div>
            )}

            {/* TAB: FLASHCARDS */}
            {activeTab === "flashcards" && (
              <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
                <div className="flex items-center justify-between border-b border-zinc-200 pb-4 dark:border-zinc-800">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold tracking-tight text-zinc-900 dark:text-white">
                        Spaced Repetition Flashcards
                      </h2>
                      {cardsSetInfo && (
                        <span className="rounded-full bg-purple-100 px-2.5 py-0.5 text-[11px] font-semibold text-purple-800 dark:bg-purple-950 dark:text-purple-300">
                          Set {cardsSetInfo.set_index} of {cardsSetInfo.total_sets}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-500">Click any card to reveal its answer. Mark status to track retention.</p>
                  </div>
                  <button
                    onClick={() => void loadFlashcards(selectedVideoId === "ALL" ? undefined : selectedVideoId, true)}
                    disabled={cardsLoading}
                    className="cursor-pointer rounded-md border border-zinc-200 px-3 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-800"
                  >
                    {cardsLoading ? "Loading..." : "New Cards (Next Set)"}
                  </button>
                </div>

                {cardsSetInfo?.all_covered && (
                  <div className="mt-4 flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs font-medium text-zinc-800 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200">
                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"><svg className="h-2.5 w-2.5 stroke-current" fill="none" viewBox="0 0 24 24" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg></span>
                    <span>{cardsSetInfo.message || "You have reviewed all key concepts from this lecture. Starting revision loop from Set 1."}</span>
                  </div>
                )}

                {cardsLoading ? (
                  <div className="my-16 text-center text-zinc-500">
                    <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-white"></div>
                    <p className="mt-3 text-xs font-medium">Generating concept cards...</p>
                  </div>
                ) : activeVideo && activeVideo.status !== "completed" && selectedVideoId !== "ALL" ? (
                  <div className="mt-6">
                    <LectureProcessingCard
                      video={activeVideo}
                      videos={videos}
                      onSelectVideo={handleSelectVideo}
                    />
                  </div>
                ) : flashcards.length > 0 ? (
                  <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {flashcards.map((card) => {
                      const isFlipped = flippedCardId === card.id;
                      return (
                        <div
                          key={card.id}
                          className="flex flex-col justify-between rounded-xl border border-zinc-200 bg-zinc-50/50 p-4 shadow-xs dark:border-zinc-800 dark:bg-zinc-950/50"
                        >
                          <div>
                            <div className="flex items-center justify-between text-[10px] font-semibold">
                              <span className="rounded bg-zinc-200/80 px-2 py-0.5 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                                {card.category || "Concept"}
                              </span>
                              <span
                                className={`${
                                  card.status === "mastered"
                                    ? "text-emerald-600 font-bold"
                                    : card.status === "reviewing"
                                    ? "text-amber-600 font-bold"
                                    : "text-zinc-400"
                                }`}
                              >
                                {card.status.toUpperCase()}
                              </span>
                            </div>

                            <div
                              onClick={() => setFlippedCardId(isFlipped ? null : card.id)}
                              className="my-3 flex min-h-[110px] cursor-pointer flex-col justify-center rounded-lg border border-zinc-200 bg-white p-3.5 text-center shadow-xs transition-all hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900"
                            >
                              <span className="text-[10px] uppercase tracking-wider text-zinc-400">
                                {isFlipped ? "Answer" : "Question (Click to Flip)"}
                              </span>
                              <p className="mt-1.5 text-xs font-semibold leading-relaxed text-zinc-900 dark:text-white">
                                {isFlipped ? card.back : card.front}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 border-t border-zinc-200 pt-2.5 dark:border-zinc-800">
                            <button
                              onClick={() => void updateCardStatus(card.id, "reviewing")}
                              className="flex-1 cursor-pointer rounded border border-zinc-200 bg-white py-1 text-[11px] font-medium text-zinc-700 hover:bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
                            >
                              Need Review
                            </button>
                            <button
                              onClick={() => void updateCardStatus(card.id, "mastered")}
                              className="flex-1 cursor-pointer rounded border border-emerald-300 bg-emerald-50 py-1 text-[11px] font-semibold text-emerald-800 hover:bg-emerald-100 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
                            >
                              Mastered
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="mt-6 text-xs text-zinc-400">No flashcards available.</p>
                )}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* -------------------------------------------------------------
          ADD PLAYLIST MODAL
      ------------------------------------------------------------- */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-900">
          <h3 className="text-base font-bold tracking-tight text-zinc-900 dark:text-white">
            Add Course (Playlist or Video)
          </h3>
          <p className="mt-1 text-xs text-zinc-500">
            Provide any YouTube playlist or single lecture/marathon video URL. Lectures index progressively in the background.
          </p>

            <form onSubmit={handleAddCourse} className="mt-4 space-y-3">
              <input
                type="url"
                required
                placeholder="https://www.youtube.com/playlist?list=... or https://youtu.be/..."
                value={newPlaylistUrl}
                onChange={(e) => setNewPlaylistUrl(e.target.value)}
                disabled={courseLoading}
                className="w-full rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-xs outline-none focus:border-zinc-500 dark:border-zinc-700"
              />

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  disabled={courseLoading}
                  className="cursor-pointer rounded-md px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={courseLoading}
                  className="cursor-pointer rounded-md bg-zinc-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-white dark:text-zinc-900"
                >
                  {courseLoading ? "Creating Course..." : "Add Course"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

{/* -------------------------------------------------------------
          USER FEEDBACK MODAL
      ------------------------------------------------------------- */}
      {showFeedbackModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-900">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold tracking-tight text-zinc-900 dark:text-white">
                Submit User Feedback
              </h3>
              <button
                onClick={() => setShowFeedbackModal(false)}
                className="cursor-pointer text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                ✕
              </button>
            </div>
            <p className="mt-1 text-xs text-zinc-500">
              Your feedback is directly linked to your student session and saved in CoursePilot telemetry.
            </p>

            {feedbackToast ? (
              <div className="my-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-center text-xs font-semibold text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
                ✓ Thank you! Your feedback has been recorded in the platform database.
              </div>
            ) : (
              <form onSubmit={handleSubmitFeedback} className="mt-4 space-y-4">
                {/* Category Pills */}
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                    Feedback Category
                  </label>
                  <div className="mt-1.5 grid grid-cols-3 gap-2">
                    {(["general", "bug", "feature"] as const).map((cat) => (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => setFeedbackType(cat)}
                        className={`cursor-pointer rounded-lg border py-1.5 text-xs font-medium capitalize transition-all ${
                          feedbackType === cat
                            ? "border-zinc-900 bg-zinc-900 text-white dark:border-white dark:bg-white dark:text-zinc-900"
                            : "border-zinc-200 bg-zinc-50 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-400"
                        }`}
                      >
                        {cat === "general" ? "General" : cat === "bug" ? "Bug Report" : "Feature Idea"}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Rating selection */}
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                    Rating (1-5)
                  </label>
                  <div className="mt-1.5 flex gap-2">
                    {[1, 2, 3, 4, 5].map((val) => (
                      <button
                        key={val}
                        type="button"
                        onClick={() => setFeedbackRating(val)}
                        className={`flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg border text-xs font-semibold transition-all ${
                          feedbackRating === val
                            ? "border-zinc-900 bg-zinc-900 text-white dark:border-white dark:bg-white dark:text-zinc-900"
                            : "border-zinc-200 bg-zinc-50 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-400"
                        }`}
                      >
                        {val}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Comments */}
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                    Your comments or suggestion
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={feedbackMessage}
                    onChange={(e) => setFeedbackMessage(e.target.value)}
                    placeholder="Tell us what you loved, or what we can improve..."
                    className="mt-1.5 w-full rounded-lg border border-zinc-200 bg-transparent px-3 py-2 text-xs outline-none focus:border-zinc-400 dark:border-zinc-800"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setShowFeedbackModal(false)}
                    disabled={feedbackLoading}
                    className="cursor-pointer rounded-md px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={feedbackLoading}
                    className="cursor-pointer rounded-md bg-zinc-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-white dark:text-zinc-900"
                  >
                    {feedbackLoading ? "Submitting..." : "Submit Feedback"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

    </div>
  );
}