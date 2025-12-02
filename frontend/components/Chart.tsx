/* eslint-disable react-hooks/exhaustive-deps */
import { useEffect, useRef, useState } from "react";
import {
  AreaSeriesPartialOptions,
  BarData,
  CandlestickData,
  ColorType,
  createChart,
  IChartApi,
  LineData,
} from "lightweight-charts";

type Candle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

type IndicatorSeries = {
  sma50?: LineData[];
  sma200?: LineData[];
  ema20?: LineData[];
};

type Props = {
  candles: Candle[];
  indicators?: IndicatorSeries;
  rsi?: LineData[];
  macd?: { macd: LineData[]; signal: LineData[]; histogram: BarData[] };
};

const chartOptions = {
  layout: {
    background: { type: ColorType.Solid, color: "#0b1224" },
    textColor: "#e3e7f1",
  },
  grid: {
    vertLines: { color: "rgba(255, 255, 255, 0.05)" },
    horzLines: { color: "rgba(255, 255, 255, 0.05)" },
  },
};

export function Chart({ candles, indicators, rsi, macd }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [showSMA, setShowSMA] = useState({ sma50: true, sma200: true, ema20: false });

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, { width: containerRef.current.clientWidth, height: 480, ...chartOptions });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#6EE7B7",
      downColor: "#FCA5A5",
      wickUpColor: "#6EE7B7",
      wickDownColor: "#FCA5A5",
      borderUpColor: "#6EE7B7",
      borderDownColor: "#FCA5A5",
    });
    candleSeries.setData(candles as CandlestickData[]);

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "",
      color: "#4b5563",
      priceLineVisible: false,
    });
    volumeSeries.priceScale().setScaleMargins({ top: 0.8, bottom: 0 });
    volumeSeries.setData(
      candles.map((c) => ({
        time: c.time,
        value: c.volume ?? 0,
        color: c.close >= c.open ? "rgba(110, 231, 183, 0.5)" : "rgba(252, 165, 165, 0.5)",
      }))
    );

    const overlayLines: Record<string, AreaSeriesPartialOptions> = {
      sma50: { lineColor: "#60a5fa" },
      sma200: { lineColor: "#c084fc" },
      ema20: { lineColor: "#facc15" },
    };

    Object.entries(overlayLines).forEach(([key, opts]) => {
      if (showSMA[key as keyof typeof showSMA] && indicators?.[key as keyof IndicatorSeries]) {
        const line = chart.addLineSeries({ color: opts.lineColor, lineWidth: 2 });
        line.setData(indicators[key as keyof IndicatorSeries] as LineData[]);
      }
    });

    // RSI + MACD sub-panels could be rendered in dedicated charts; keep inline for brevity
    if (rsi) {
      const rsiLine = chart.addLineSeries({ color: "#f472b6", lineWidth: 2, priceScaleId: "rsi" });
      rsiLine.priceScale().setScaleMargins({ top: 0.2, bottom: 0.6 });
      rsiLine.setData(rsi);
    }

    if (macd) {
      const macdLine = chart.addLineSeries({ color: "#22d3ee", lineWidth: 2, priceScaleId: "macd" });
      macdLine.priceScale().setScaleMargins({ top: 0.6, bottom: 0 });
      macdLine.setData(macd.macd);

      const signalLine = chart.addLineSeries({ color: "#f97316", lineWidth: 2, priceScaleId: "macd" });
      signalLine.setData(macd.signal);

      const hist = chart.addHistogramSeries({ color: "#a78bfa", priceScaleId: "macd" });
      hist.setData(macd.histogram);
    }

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [candles, indicators, rsi, macd, showSMA]);

  return (
    <div className="w-full rounded-xl bg-slate-900/70 p-4 shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3">
        <div className="text-lg font-semibold text-white">Price Action</div>
        <div className="flex gap-2 text-sm text-slate-200">
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={showSMA.sma50}
              onChange={() => setShowSMA((s) => ({ ...s, sma50: !s.sma50 }))}
            />
            SMA 50
          </label>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={showSMA.sma200}
              onChange={() => setShowSMA((s) => ({ ...s, sma200: !s.sma200 }))}
            />
            SMA 200
          </label>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={showSMA.ema20}
              onChange={() => setShowSMA((s) => ({ ...s, ema20: !s.ema20 }))}
            />
            EMA 20
          </label>
        </div>
      </div>
      <div ref={containerRef} className="h-[500px] w-full" />
    </div>
  );
}

export default Chart;
