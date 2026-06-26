"use client";

/**
 * AEQUITAS — Candlestick + volume chart using TradingView's
 * lightweight-charts library (v5 API).
 *
 * Renders OHLC candles in the main pane and a volume histogram
 * in a separate pane below, synced on the same time axis.
 */

import { useEffect, useRef } from "react";
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type HistogramData,
  type UTCTimestamp,
} from "lightweight-charts";

export interface Candle {
  time: string; // ISO date string
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandlestickChartProps {
  candles: Candle[];
  height?: number;
}

function toUnixTime(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

export function CandlestickChart({
  candles,
  height = 420,
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  // Create chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const isDark =
      document.documentElement.getAttribute("data-theme") === "dark";

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: isDark ? "#8C8B82" : "#5C5A52",
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: isDark ? "#242420" : "#E8E6DF" },
        horzLines: { color: isDark ? "#242420" : "#E8E6DF" },
      },
      rightPriceScale: {
        borderColor: isDark ? "#2E2E29" : "#D4D0C8",
      },
      timeScale: {
        borderColor: isDark ? "#2E2E29" : "#D4D0C8",
        timeVisible: false,
      },
      crosshair: {
        vertLine: { color: isDark ? "#3C3C36" : "#B8B4AA", width: 1 },
        horzLine: { color: isDark ? "#3C3C36" : "#B8B4AA", width: 1 },
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#1A6B4A",
      downColor: "#B83232",
      borderUpColor: "#1A6B4A",
      borderDownColor: "#B83232",
      wickUpColor: "#1A6B4A",
      wickDownColor: "#B83232",
      priceScaleId: "right",
    });
    candleSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.05, bottom: 0.25 },
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height]);

  // Update data whenever candles change
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return;
    if (candles.length === 0) return;

    const candleData: CandlestickData[] = candles.map((c) => ({
      time: toUnixTime(c.time),
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    const volumeData: HistogramData[] = candles.map((c) => ({
      time: toUnixTime(c.time),
      value: c.volume,
      color:
        c.close >= c.open ? "rgba(26, 107, 74, 0.4)" : "rgba(184, 50, 50, 0.4)",
    }));

    candleSeriesRef.current.setData(candleData);
    volumeSeriesRef.current.setData(volumeData);
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  return <div ref={containerRef} style={{ width: "100%" }} />;
}
