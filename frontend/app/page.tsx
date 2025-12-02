/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect, useState } from "react";
import { Chart } from "../components/Chart";

type Candle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

type Report = {
  executive_summary?: string;
  technical_outlook?: string;
  risks?: string;
  strategy?: string;
  technical_indicators?: any;
  confidence?: string;
};

const TIMEFRAMES = [
  { label: "1D", period: "5d", interval: "30m" },
  { label: "1W", period: "1mo", interval: "1h" },
  { label: "1M", period: "6mo", interval: "1d" },
  { label: "1Y", period: "1y", interval: "1d" },
];

export default function Dashboard() {
  const [ticker, setTicker] = useState("AAPL");
  const [selectedFrame, setSelectedFrame] = useState(TIMEFRAMES[3]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [news, setNews] = useState<any[]>([]);
  const [report, setReport] = useState<Report>({});
  const [status, setStatus] = useState<"idle" | "loading" | "analyzing">("idle");

  useEffect(() => {
    loadMarketData();
  }, [selectedFrame]);

  const loadMarketData = async () => {
    setStatus("loading");
    try {
      const [pricesRes, newsRes] = await Promise.all([
        fetch(
          `http://localhost:8000/api/market/history?ticker=${ticker}&period=${selectedFrame.period}&interval=${selectedFrame.interval}`
        ),
        fetch(`http://localhost:8000/api/market/news?ticker=${ticker}`),
      ]);
      const pricesJson = await pricesRes.json();
      const newsJson = await newsRes.json();
      setCandles(pricesJson.candles);
      setNews(newsJson.news || []);
    } catch (error) {
      console.error(error);
    } finally {
      setStatus("idle");
    }
  };

  const handleAnalyze = async () => {
    setStatus("analyzing");
    setReport({});
    try {
      const res = await fetch(`http://localhost:8000/api/analyze?ticker=${ticker}`, { method: "POST" });
      const { task_id } = await res.json();
      pollTask(task_id);
    } catch (error) {
      console.error(error);
      setStatus("idle");
    }
  };

  const pollTask = async (taskId: string) => {
    const interval = setInterval(async () => {
      const res = await fetch(`http://localhost:8000/api/analyze/${taskId}`);
      const task = await res.json();
      if (task.status === "complete") {
        clearInterval(interval);
        setReport(task.result?.draft_report || {});
        setStatus("idle");
      }
      if (task.status === "error") {
        clearInterval(interval);
        console.error(task.error);
        setStatus("idle");
      }
    }, 1500);
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
        <header className="flex flex-col gap-4 rounded-2xl bg-slate-900/80 p-5 backdrop-blur">
          <div className="flex flex-wrap items-center gap-3">
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="w-32 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-lg font-semibold focus:outline-none"
              placeholder="AAPL"
            />
            <div className="flex gap-2">
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf.label}
                  className={`rounded-xl px-3 py-2 text-sm font-semibold ${
                    tf.label === selectedFrame.label ? "bg-emerald-500 text-slate-900" : "bg-slate-800 text-slate-200"
                  }`}
                  onClick={() => setSelectedFrame(tf)}
                >
                  {tf.label}
                </button>
              ))}
            </div>
            <button
              onClick={loadMarketData}
              className="rounded-xl bg-blue-500 px-4 py-2 font-semibold text-white hover:bg-blue-400"
              disabled={status === "loading"}
            >
              Refresh
            </button>
            <button
              onClick={handleAnalyze}
              className="rounded-xl bg-emerald-500 px-4 py-2 font-semibold text-slate-900 hover:bg-emerald-400"
              disabled={status !== "idle"}
            >
              {status === "analyzing" ? "Analyzing..." : "Analyze"}
            </button>
          </div>
          <p className="text-sm text-slate-300">
            Autonomous multi-agent analysis: researcher → analyst → writer → critic. Reports return in Thai with raw metrics.
          </p>
        </header>

        <Chart candles={candles} />

        <section className="grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2 rounded-2xl bg-slate-900/80 p-5">
            <h2 className="mb-3 text-lg font-semibold">AI Insight (JSON Render)</h2>
            {report.executive_summary ? (
              <div className="space-y-2 text-sm leading-relaxed text-slate-200">
                <p>
                  <span className="font-semibold text-emerald-400">Executive Summary:</span> {report.executive_summary}
                </p>
                <p>
                  <span className="font-semibold text-blue-400">Technical Outlook:</span> {report.technical_outlook}
                </p>
                <p>
                  <span className="font-semibold text-amber-400">Risks:</span> {report.risks}
                </p>
                <p>
                  <span className="font-semibold text-fuchsia-400">Strategy:</span> {report.strategy}
                </p>
                <p className="text-xs text-slate-400">Confidence: {report.confidence}</p>
                <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 text-[11px] text-slate-200">
{JSON.stringify(report.technical_indicators, null, 2)}
                </pre>
              </div>
            ) : (
              <p className="text-sm text-slate-400">Trigger analysis to see the autonomous report.</p>
            )}
          </div>
          <div className="rounded-2xl bg-slate-900/80 p-5">
            <h2 className="mb-3 text-lg font-semibold">News & Sentiment</h2>
            <div className="flex max-h-96 flex-col gap-3 overflow-auto">
              {news.length === 0 && <p className="text-sm text-slate-400">No news fetched (soft fail safe).</p>}
              {news.map((item) => (
                <a
                  key={item.url + item.title}
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 hover:border-emerald-400"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-100 group-hover:text-emerald-300">{item.title}</p>
                    <span className="rounded-lg bg-slate-800 px-2 py-1 text-xs text-emerald-300">
                      {item.score ? item.score.toFixed(2) : "Neutral"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{item.excerpt}</p>
                </a>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
