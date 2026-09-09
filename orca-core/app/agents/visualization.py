"""Visualization — choosing what to draw, not just what to say.

The problem statement names a visualization agent among the eight roles, and
lists "maps, charts, geospatial visualizations" among the things ORCA should
produce. Charts exist now, but only on two fixed screens: a 48-hour wave and
wind timeline on Sea Today and Safety, and a decade of seasonal means below it.
Ask a question in the chat and you get prose, however much the answer wants a
picture.

This agent closes that. It reads the question, decides *which* series answers
it, fetches that series for real, and returns a chart specification the app
renders inline in the conversation. "Will the waves get worse tonight" comes
back as the wave trace with INCOIS's alert level drawn across it; "has it got
warmer here" comes back as ten Septembers side by side.

The point worth being careful about: this agent draws only data another part of
ORCA already fetches from a named source, and every specification it returns
carries that source through to the caption. It has no ability to plot a number
nobody measured, which is the only way a chart-drawing agent stays honest — a
chart is the most persuasive way there is to show something false.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from ..tools.history import HistoryDataError, fetch_season_history
from ..tools.marine import MarineDataError, fetch_marine_conditions
from .base import Agent, AgentResult, Evidence, QueryContext
from .weather import (
    GUST_CAUTION_KMH,
    GUST_DANGER_KMH,
    WAVE_CAUTION_M,
    WAVE_DANGER_M,
    WIND_CAUTION_KMH,
    WIND_DANGER_KMH,
    safe_until,
)

_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079

FORECAST_SOURCE = "Open-Meteo Marine + Forecast API"

#: What each forecast series is graded against, and who says so. The captions
#: name the agency because an unattributed red line is ORCA claiming an
#: authority it does not have.
_FORECAST_SERIES: dict[str, dict[str, Any]] = {
    "waves": {
        "label": "Wave height",
        "unit": "m",
        "attribute": "wave_height_m",
        "caution": WAVE_CAUTION_M,
        "danger": WAVE_DANGER_M,
        "dangerLabel": "INCOIS High Wave Alert",
        "thresholdSource": "INCOIS High Wave Alert (issued 1.9-2.2 m)",
    },
    "wind": {
        "label": "Wind speed",
        "unit": "km/h",
        "attribute": "wind_speed_kmh",
        "caution": WIND_CAUTION_KMH,
        "danger": WIND_DANGER_KMH,
        "dangerLabel": "IMD: do not venture",
        "thresholdSource": "IMD Wind Warning for Fishermen — lowest tier, 35-45 kmph",
    },
    "gusts": {
        "label": "Gusts",
        "unit": "km/h",
        "attribute": "wind_gusts_kmh",
        "caution": GUST_CAUTION_KMH,
        "danger": GUST_DANGER_KMH,
        "dangerLabel": "IMD gust figure",
        "thresholdSource": "IMD Wind Warning for Fishermen — gusting 55 kmph",
    },
    "rain": {
        "label": "Rainfall",
        "unit": "mm/h",
        "attribute": "precipitation_mm",
        "caution": None,
        "danger": None,
        "dangerLabel": None,
        # Rain alone rarely decides a trip, and there is no published Indian
        # small-craft rainfall threshold, so none is drawn rather than invented.
        "thresholdSource": None,
    },
}

#: Which historical metric a trend request maps to.
_TREND_KEYS = {"sst": "sst", "temperature": "sst", "wind_trend": "wind", "rain_trend": "rain",
               "wave_trend": "wave"}


class VisualizationAgent(Agent):
    name = "visualization"
    description = (
        "Draws a chart to answer a question: the wave, wind, gust or rainfall forecast for "
        "the next two days against India's warning levels, or a decade of seasonal means "
        "for temperature, wind, rain or waves. Use whenever the answer is about how "
        "something changes over hours, days or years, or when the user asks to see, show, "
        "plot or graph something."
    )
    handles = (
        "show", "chart", "graph", "plot", "draw", "picture", "visual", "trend over",
        "how will", "later today", "tonight", "next two days", "compare", "curve",
    )
    is_stub = False

    parameters = {
        "type": "object",
        "properties": {
            "series": {
                "type": "string",
                "description": (
                    "What to draw. Forecast series: 'waves', 'wind', 'gusts', 'rain'. "
                    "Multi-year seasonal series: 'sst', 'wind_trend', 'rain_trend', "
                    "'wave_trend'."
                ),
                "enum": [
                    "waves", "wind", "gusts", "rain",
                    "sst", "wind_trend", "rain_trend", "wave_trend",
                ],
            },
            "hours": {
                "type": "integer",
                "description": "How many hours of forecast to draw. Default 48.",
                "minimum": 6,
                "maximum": 72,
            },
            "latitude": {"type": "number", "description": "Only if not the user's position."},
            "longitude": {"type": "number", "description": "Only if not the user's position."},
        },
    }

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON
        series = str(context.params.get("series") or "waves").lower()
        hours = int(context.params.get("hours") or 48)

        if series in _TREND_KEYS:
            return await self._trend_chart(latitude, longitude, _TREND_KEYS[series])
        if series not in _FORECAST_SERIES:
            series = "waves"
        return await self._forecast_chart(latitude, longitude, series, hours)

    async def _forecast_chart(
        self, latitude: float, longitude: float, key: str, hours: int
    ) -> AgentResult:
        spec = _FORECAST_SERIES[key]
        try:
            conditions = await fetch_marine_conditions(latitude, longitude)
        except MarineDataError as exc:
            return AgentResult(
                agent=self.name,
                summary="The forecast could not be read, so there is nothing to draw.",
                error=str(exc),
                confidence=0.0,
            )

        now = conditions.local_now
        window = [p for p in conditions.hourly if now <= p.time <= now + timedelta(hours=hours)]
        points = [
            {"t": point.time.isoformat(), "v": getattr(point, spec["attribute"])}
            for point in window
        ]
        values = [p["v"] for p in points if p["v"] is not None]
        if not values:
            return AgentResult(
                agent=self.name,
                summary=f"The forecast carries no {spec['label'].lower()} for this position.",
                confidence=0.2,
            )

        peak = max(values)
        peak_at = next(p["t"] for p in points if p["v"] == peak)
        turning = safe_until(conditions.hourly, now)

        chart = {
            "kind": "forecast",
            "title": f"{spec['label']}, next {hours} hours",
            "unit": spec["unit"],
            "points": points,
            "caution": spec["caution"],
            "danger": spec["danger"],
            "dangerLabel": spec["dangerLabel"],
            "source": FORECAST_SOURCE,
            "thresholdSource": spec["thresholdSource"],
            "markerAt": turning[0].isoformat() if turning else None,
            "markerLabel": "sea turns" if turning else None,
        }

        crosses = spec["danger"] is not None and peak >= spec["danger"]
        summary = (
            f"{spec['label']} peaks at {peak:.1f} {spec['unit']} around {peak_at[11:16]} "
            f"over the next {hours} hours"
        )
        summary += (
            f", above the {spec['dangerLabel']} level of {spec['danger']} {spec['unit']}."
            if crosses
            else (
                f", staying under the {spec['dangerLabel']} level of "
                f"{spec['danger']} {spec['unit']}."
                if spec["danger"] is not None
                else "."
            )
        )

        return AgentResult(
            agent=self.name,
            summary=summary,
            evidence=[
                Evidence(
                    source=FORECAST_SOURCE,
                    label=f"Peak {spec['label'].lower()}",
                    value=f"{peak:.1f}",
                    unit=spec["unit"],
                    observed_at=peak_at,
                    note=spec["thresholdSource"],
                )
            ],
            confidence=0.75,
            data={"chart": chart},
        )

    async def _trend_chart(self, latitude: float, longitude: float, key: str) -> AgentResult:
        try:
            history = await fetch_season_history(latitude, longitude)
        except HistoryDataError as exc:
            return AgentResult(
                agent=self.name,
                summary="The historical record could not be read, so there is nothing to draw.",
                error=str(exc),
                confidence=0.0,
            )

        metric = next((m for m in history.metrics if m.key == key), None)
        if metric is None or len(metric.by_year) < 2:
            return AgentResult(
                agent=self.name,
                summary=(
                    "There are not enough years of that record at this position to plot a "
                    "comparison."
                ),
                confidence=0.2,
            )

        chart = {
            "kind": "trend",
            "title": f"{metric.label}, {history.window_label} each year",
            "unit": metric.unit,
            "points": [
                {"t": str(year), "v": value} for year, value in sorted(metric.by_year.items())
            ],
            "baseline": metric.baseline,
            "baselineLabel": "earlier years' average",
            "source": metric.source,
            "notes": history.notes,
        }

        slope = metric.slope_per_decade
        direction = (
            "has not moved in any direction worth calling a trend"
            if slope is None
            else f"has {'risen' if slope > 0 else 'fallen'} about {abs(slope):.2f} "
            f"{metric.unit} per decade"
        )

        return AgentResult(
            agent=self.name,
            summary=(
                f"{metric.label} for the {history.window_label} window {direction} "
                f"({metric.first_year}–{metric.last_year})."
            ),
            evidence=[
                Evidence(
                    source=metric.source,
                    label=f"{metric.label} this season",
                    value="—" if metric.latest is None else f"{metric.latest:.2f}",
                    unit=metric.unit,
                    observed_at=f"{metric.first_year}–{metric.last_year}",
                )
            ],
            confidence=0.7,
            data={"chart": chart},
        )
