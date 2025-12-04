/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect, useState } from "react";
import type { BarData, LineData } from "lightweight-charts";
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

type IndicatorSeries = {
  sma50?: LineData[];
  sma200?: LineData[];
  ema20?: LineData[];
};

type MacdSeries = {
  macd: LineData[];
  signal: LineData[];
  histogram: BarData[];
};

const TIMEFRAMES = [
  { label: "1D", period: "5d", interval: "30m" },
  { label: "1W", period: "1mo", interval: "1h" },
  { label: "1M", period: "6mo", interval: "1d" },
  { label: "1Y", period: "1y", interval: "1d" },
];

export default function Dashboard() {
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [ticker, setTicker] = useState("AAPL");
  const [selectedFrame, setSelectedFrame] = useState(TIMEFRAMES[3]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [indicators, setIndicators] = useState<IndicatorSeries>({});
  const [rsiSeries, setRsiSeries] = useState<LineData[]>([]);
  const [macdSeries, setMacdSeries] = useState<MacdSeries | null>(null);
  const [news, setNews] = useState<any[]>([]);
  const [report, setReport] = useState<Report>({});
  const [status, setStatus] = useState<"idle" | "loading" | "analyzing">("idle");
  const [errorMsg, setErrorMsg] = useState<string>("");

  useEffect(() => {
    loadMarketData();
  }, [selectedFrame]);

  const loadMarketData = async () => {
    setStatus("loading");
    setErrorMsg("");
    try {
      const [pricesRes, newsRes] = await Promise.all([
        fetch(
          `${API_BASE}/api/market/history?ticker=${ticker}&period=${selectedFrame.period}&interval=${selectedFrame.interval}`
        ),
        fetch(`${API_BASE}/api/market/news?ticker=${ticker}`),
      ]);
      const pricesJson = await pricesRes.json();
      const newsJson = await newsRes.json();
      setCandles(pricesJson.candles);
      setIndicators(pricesJson.indicators || {});
      setRsiSeries(pricesJson.rsi || []);
      setMacdSeries(pricesJson.macd || null);
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
    setErrorMsg("");
    try {
      const res = await fetch(`${API_BASE}/api/analyze?ticker=${ticker}`, { method: "POST" });
      if (!res.ok) {
        throw new Error(`Analyze failed: ${res.status}`);
      }
      const { task_id } = await res.json();
      pollTask(task_id);
    } catch (error) {
      console.error(error);
      setErrorMsg("Analyze request failed. Check API key / backend logs.");
      setStatus("idle");
    }
  };

  const pollTask = async (taskId: string) => {
    const interval = setInterval(async () => {
      const res = await fetch(`${API_BASE}/api/analyze/${taskId}`);
      const task = await res.json();
      if (task.status === "complete") {
        clearInterval(interval);
        setReport(task.result?.draft_report || {});
        setStatus("idle");
      }
      if (task.status === "error") {
        clearInterval(interval);
        console.error(task.error);
        setErrorMsg(task.error || "Agent run failed. Check backend logs or API keys.");
        setStatus("idle");
      }
    }, 1500);
  };

  return (
    <main className="relative min-h-screen">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(16,185,129,0.1),transparent_25%),radial-gradient(circle_at_80%_0%,rgba(59,130,246,0.12),transparent_20%),radial-gradient(circle_at_50%_70%,rgba(236,72,153,0.08),transparent_25%)]" />
      <div className="relative mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
        <header className="flex flex-col gap-5 rounded-2xl border border-white/5 bg-white/5 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-2 shadow-inner shadow-black/40">
              <div className="text-xs uppercase tracking-[0.2em] text-emerald-300/80">Ticker</div>
              <input
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="w-32 rounded-xl bg-transparent text-lg font-semibold text-white placeholder:text-slate-500 focus:outline-none"
                placeholder="AAPL"
              />
            </div>
            <div className="flex gap-2 rounded-2xl border border-white/10 bg-white/5 p-1 shadow-inner shadow-black/40">
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf.label}
                  className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                    tf.label === selectedFrame.label
                      ? "bg-emerald-500 text-slate-900 shadow-lg shadow-emerald-500/40"
                      : "text-slate-200 hover:bg-white/5"
                  }`}
                  onClick={() => setSelectedFrame(tf)}
                >
                  {tf.label}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={loadMarketData}
                className="rounded-xl bg-sky-500/90 px-4 py-2 font-semibold text-slate-900 shadow-lg shadow-sky-500/40 transition hover:bg-sky-400"
                disabled={status === "loading"}
              >
                Refresh
              </button>
              <button
                onClick={handleAnalyze}
                className="rounded-xl bg-emerald-500 px-4 py-2 font-semibold text-slate-900 shadow-lg shadow-emerald-500/40 transition hover:bg-emerald-400"
                disabled={status !== "idle"}
              >
                {status === "analyzing" ? "Analyzing..." : "Analyze"}
              </button>
            </div>
          </div>
          <p className="max-w-3xl text-sm text-slate-300">
            Autonomous multi-agent analysis: researcher → analyst → writer → critic. Reports return in Thai with raw metrics.
          </p>
        </header>

        <div className="rounded-2xl border border-white/5 bg-white/5 p-4 shadow-2xl shadow-black/30 backdrop-blur-xl">
          <Chart candles={candles} indicators={indicators} rsi={rsiSeries} macd={macdSeries || undefined} />
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2 rounded-2xl border border-white/5 bg-white/5 p-5 shadow-2xl shadow-black/30 backdrop-blur-xl">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">AI Insight (JSON Render)</h2>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-emerald-200">Live</span>
            </div>
            {report.executive_summary ? (
              <div className="space-y-2 text-sm leading-relaxed text-slate-200">
                <p>
                  <span className="font-semibold text-emerald-300">Executive Summary:</span> {report.executive_summary}
                </p>
                <p>
                  <span className="font-semibold text-blue-300">Technical Outlook:</span> {report.technical_outlook}
                </p>
                <p>
                  <span className="font-semibold text-amber-300">Risks:</span> {report.risks}
                </p>
                <p>
                  <span className="font-semibold text-fuchsia-300">Strategy:</span> {report.strategy}
                </p>
                <p className="text-xs text-slate-400">Confidence: {report.confidence}</p>
                <pre className="mt-2 max-h-64 overflow-auto rounded-lg border border-white/5 bg-black/60 p-3 text-[11px] text-slate-200 backdrop-blur">
{JSON.stringify(report.technical_indicators, null, 2)}
                </pre>
              </div>
            ) : (
              <div className="space-y-2 text-sm text-slate-400">
                <p>Trigger analysis to see the autonomous report.</p>
                {status === "analyzing" && <p className="text-emerald-300">Analyzing…</p>}
                {errorMsg && <p className="text-rose-300">Error: {errorMsg}</p>}
              </div>
            )}
          </div>
          <div className="rounded-2xl border border-white/5 bg-white/5 p-5 shadow-2xl shadow-black/30 backdrop-blur-xl">
            <h2 className="mb-3 text-lg font-semibold text-white">News & Sentiment</h2>
            <div className="flex max-h-96 flex-col gap-3 overflow-auto">
              {news.length === 0 && <p className="text-sm text-slate-400">No news fetched (soft fail safe).</p>}
              {news.map((item) => (
                <a
                  key={item.url + item.title}
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group rounded-xl border border-white/5 bg-black/50 px-3 py-2 shadow-inner shadow-black/50 transition hover:border-emerald-400/60"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-100 group-hover:text-emerald-300">{item.title}</p>
                    <span className="rounded-lg bg-white/5 px-2 py-1 text-xs text-emerald-300">
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
